"""Gate evaluation, with the fail-closed directions asserted explicitly.

The spec's whole point is that an UNRESOLVED input to a safety gate must
block exactly as hard as a confirmed-bad one. A first draft of the design
let unresolved posture through with a warning, which meant the gate
silently never fired whenever Monitor was unreachable. These tests exist
so that regression cannot recur.
"""

from __future__ import annotations

import io
import json

import gates


def _ctx(**overrides):
    """A context that passes every gate, so each test varies one thing."""
    base = {
        "kind": "bugfix",
        "secondary_kinds": [],
        "posture": "ok",
        "touches_admin_public": False,
        "branch_pair_valid": None,
        "targets_admin_deploy": False,
        "media_mount": None,
        "version_major": "7",
        "platform": "ubuntu",
    }
    base.update(overrides)
    return base


def _by_gate(decisions, name):
    for d in decisions:
        if d["gate"] == name:
            return d
    raise AssertionError("no decision for gate %r in %r" % (name, decisions))


def test_clean_context_blocks_nothing():
    assert gates.blocking(gates.evaluate(_ctx())) == []


def test_compromised_host_blocks():
    d = _by_gate(gates.evaluate(_ctx(posture="compromised")), "host_posture")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_unknown_posture_blocks_identically_to_compromised():
    unknown = _by_gate(gates.evaluate(_ctx(posture="unknown")), "host_posture")
    missing = _by_gate(gates.evaluate(_ctx(posture=None)), "host_posture")
    assert unknown["status"] == gates.BLOCK
    assert missing["status"] == gates.BLOCK
    assert missing["overridable"] is False


def test_degraded_host_warns_but_does_not_block():
    d = _by_gate(gates.evaluate(_ctx(posture="degraded")), "host_posture")
    assert d["status"] == gates.WARN


def test_branch_pair_gate_only_applies_to_admin_public_builds():
    d = _by_gate(gates.evaluate(_ctx(touches_admin_public=False)), "branch_pair")
    assert d["status"] == gates.PASS


def test_underivable_branch_pair_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=None)),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK


def test_invalid_branch_pair_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=False)),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK


def test_unrecognised_branch_pair_value_blocks():
    """Fail-closed: any value other than True/False is treated as unresolved."""
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid="maybe")),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK


def test_valid_branch_pair_passes():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=True)),
        "branch_pair",
    )
    assert d["status"] == gates.PASS


def test_admin_deploy_without_media_mount_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount=False)),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK


def test_admin_deploy_with_unknown_media_mount_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount=None)),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK


def test_admin_deploy_with_unrecognised_media_mount_value_blocks():
    """Fail-closed: any value other than True/False is treated as unresolved."""
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount="yes")),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK


def test_admin_deploy_with_confirmed_media_mount_passes():
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount=True)),
        "media_mount",
    )
    assert d["status"] == gates.PASS


def test_unsupported_version_blocks_but_is_overridable():
    for major in ("4", "5", "6"):
        d = _by_gate(gates.evaluate(_ctx(version_major=major)), "unsupported_version")
        assert d["status"] == gates.BLOCK, major
        assert d["overridable"] is True, major


def test_unresolved_version_blocks_and_is_not_overridable():
    d = _by_gate(gates.evaluate(_ctx(version_major=None)), "unsupported_version")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_unrecognised_version_value_blocks():
    """Fail-closed: any value other than '7' or a known unsupported major
    still blocks, not silently let through."""
    d = _by_gate(gates.evaluate(_ctx(version_major="banana")), "unsupported_version")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_unrecognised_version_reason_is_distinct_from_unresolved():
    """A present-but-unrecognised major (a future "8", or an int 7 that
    fails the string comparison) must BLOCK exactly like a missing
    version_major -- but the reason must say so, not claim the version is
    unresolved when something was actually read."""
    missing = _by_gate(gates.evaluate(_ctx(version_major=None)), "unsupported_version")
    assert missing["status"] == gates.BLOCK
    assert "unresolved" in missing["reason"]

    for present_but_unrecognised in ("8", 7, "banana"):
        d = _by_gate(
            gates.evaluate(_ctx(version_major=present_but_unrecognised)),
            "unsupported_version",
        )
        assert d["status"] == gates.BLOCK, present_but_unrecognised
        assert d["overridable"] is False, present_but_unrecognised
        assert "unresolved" not in d["reason"], present_but_unrecognised


def test_windows_target_warns_and_fails_open():
    d = _by_gate(gates.evaluate(_ctx(platform="windows")), "windows_target")
    assert d["status"] == gates.WARN
    unresolved = _by_gate(gates.evaluate(_ctx(platform=None)), "windows_target")
    assert unresolved["status"] != gates.BLOCK


def test_windows_target_warns_regardless_of_casing():
    """The gate is advisory and must never block -- but an exact-match
    comparison silently PASSed "Windows" / "WINDOWS" instead of warning,
    which is the wrong failure direction for a gate that is supposed to
    fire whenever the target is Windows, spelled however."""
    for platform in ("Windows", "WINDOWS", "WinDows"):
        d = _by_gate(gates.evaluate(_ctx(platform=platform)), "windows_target")
        assert d["status"] == gates.WARN, platform


def test_windows_target_still_fails_open_on_garbage_types():
    """Casing fix must not turn this into a gate that crashes or blocks
    on a non-string platform value -- it stays advisory-only."""
    for bogus in (1, [], {}, True):
        d = _by_gate(gates.evaluate(_ctx(platform=bogus)), "windows_target")
        assert d["status"] != gates.BLOCK, bogus


def test_secondary_kinds_are_gated_too():
    """A bugfix carrying 'upgrade' as a secondary kind is itself the
    remediation the version gate would otherwise demand, so it passes on
    an unsupported major. Without that secondary, the identical version
    still blocks -- proving the key is actually read, not just accepted.
    """
    with_upgrade = _ctx(kind="bugfix", secondary_kinds=["upgrade"], version_major="5")
    assert _by_gate(gates.evaluate(with_upgrade), "unsupported_version")["status"] == gates.PASS

    without_upgrade = _ctx(kind="bugfix", secondary_kinds=[], version_major="5")
    assert _by_gate(gates.evaluate(without_upgrade), "unsupported_version")["status"] == gates.BLOCK


def test_every_decision_carries_a_remedy():
    for d in gates.evaluate(_ctx(posture="compromised", version_major="4")):
        if d["status"] == gates.BLOCK:
            assert d["remedy"], d


def test_cli_reports_a_blocking_context_on_stdout_and_still_exits_zero(capsys, monkeypatch):
    """The CLI exists so the router RUNS the gates rather than reading prose
    about them, and the verdict lives in the JSON alone.

    A block is this tool's normal, expected output, so it exits 0 like any
    other verdict. Exiting non-zero on a block would abort a caller running
    under `set -e`, and would invite the calling layer to treat the run as a
    failed command and discard stdout -- throwing away the reasons and
    remedies the operator needs. Non-zero is reserved for "the evaluation
    could not run".
    """
    ctx = _ctx(posture="compromised")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ctx)))

    status = gates.main([])

    assert status == 0
    decisions = json.loads(capsys.readouterr().out)
    assert _by_gate(decisions, "host_posture")["status"] == gates.BLOCK
    assert decisions[0]["status"] == gates.BLOCK  # blocking sorts first


def test_cli_reports_a_passing_context_with_a_zero_exit_status(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ctx())))

    status = gates.main([])

    assert status == 0
    decisions = json.loads(capsys.readouterr().out)
    assert [d for d in decisions if d["status"] == gates.BLOCK] == []
    assert {d["gate"] for d in decisions} == {
        "host_posture",
        "branch_pair",
        "media_mount",
        "unsupported_version",
        "windows_target",
    }


def test_cli_refuses_malformed_stdin_cleanly(capsys, monkeypatch):
    """Unreadable input is the one case that IS an execution failure.

    It must not surface as a traceback: a stack trace buries the one useful
    fact (the context is not JSON) and looks like a crash in the gates
    themselves, which is the last thing an operator should mistrust.
    """
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

    status = gates.main([])

    assert status != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "gates.py:" in captured.err
    assert "Traceback" not in captured.err
    assert captured.err.strip().count("\n") == 0  # one line, not a dump


def _ctx_without(key, **overrides):
    """A passing context with `key` removed entirely, not just falsified.

    An absent key and a `false` key are different statements: "nobody
    looked" versus "somebody looked and said no". The fail-open defect
    these tests pin down lived precisely in that gap.
    """
    ctx = _ctx(**overrides)
    ctx.pop(key, None)
    return ctx


def test_explicit_media_mount_false_blocks_without_the_applicability_flag():
    """Negative evidence outranks an absent applicability flag.

    `media_mount: false` means somebody read the compose and the mount is
    NOT there -- Admin crashes on startup. That finding must not be
    discarded merely because `targets_admin_deploy` was never set.
    """
    d = _by_gate(
        gates.evaluate(_ctx_without("targets_admin_deploy", media_mount=False)),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK
    assert d["remedy"]


def test_explicit_branch_pair_false_blocks_without_the_applicability_flag():
    """Symmetric to media_mount: a pair confirmed incompatible still blocks."""
    d = _by_gate(
        gates.evaluate(_ctx_without("touches_admin_public", branch_pair_valid=False)),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK
    assert d["remedy"]


def test_non_boolean_targets_admin_deploy_blocks():
    """A malformed applicability value must not silently deactivate a gate.

    The evidence is deliberately POSITIVE here (`media_mount: true`), so the
    block can only come from the unreadable applicability value itself and
    not from the underlying fact being unresolved.
    """
    for bogus in ("yes", 1, {"admin": True}, ["admin"]):
        d = _by_gate(
            gates.evaluate(_ctx(targets_admin_deploy=bogus, media_mount=True)),
            "media_mount",
        )
        assert d["status"] == gates.BLOCK, bogus
        assert "targets_admin_deploy" in d["reason"], bogus
        assert d["remedy"], bogus


def test_non_boolean_touches_admin_public_blocks():
    for bogus in ("yes", 1, {"admin": True}, ["admin"]):
        d = _by_gate(
            gates.evaluate(_ctx(touches_admin_public=bogus, branch_pair_valid=True)),
            "branch_pair",
        )
        assert d["status"] == gates.BLOCK, bogus
        assert "touches_admin_public" in d["reason"], bogus
        assert d["remedy"], bogus


def test_dict_secondary_kinds_does_not_grant_the_upgrade_exemption():
    """`in` matches a dict's KEYS, so a dict once bought the exemption.

    A set is checked alongside it: `list()` flattens it into exactly the
    same membership test, and only a list or tuple is an accepted shape.
    """
    for bogus in ({"upgrade": "x"}, {"upgrade"}):
        d = _by_gate(
            gates.evaluate(_ctx(secondary_kinds=bogus, version_major="5")),
            "unsupported_version",
        )
        assert d["status"] == gates.BLOCK, bogus


def test_bare_string_secondary_kinds_does_not_grant_the_upgrade_exemption():
    """`in` on a string matches SUBSTRINGS; only a list/tuple of strings counts."""
    for bogus in ("upgrade", "upgrades and bugfixes", "xupgradex"):
        d = _by_gate(
            gates.evaluate(_ctx(secondary_kinds=bogus, version_major="5")),
            "unsupported_version",
        )
        assert d["status"] == gates.BLOCK, bogus


def test_applicability_false_or_absent_still_passes():
    """The regression guard: ordinary requests must not start blocking."""
    for ctx in (
        _ctx(targets_admin_deploy=False),
        _ctx_without("targets_admin_deploy"),
    ):
        assert _by_gate(gates.evaluate(ctx), "media_mount")["status"] == gates.PASS
    for ctx in (
        _ctx(touches_admin_public=False),
        _ctx_without("touches_admin_public"),
    ):
        assert _by_gate(gates.evaluate(ctx), "branch_pair")["status"] == gates.PASS


def test_legitimate_upgrade_exemption_still_granted():
    listed = _ctx(kind="bugfix", secondary_kinds=["upgrade"], version_major="5")
    assert _by_gate(gates.evaluate(listed), "unsupported_version")["status"] == gates.PASS

    tupled = _ctx(kind="bugfix", secondary_kinds=("upgrade",), version_major="5")
    assert _by_gate(gates.evaluate(tupled), "unsupported_version")["status"] == gates.PASS

    primary = _ctx(kind="upgrade", secondary_kinds=[], version_major="5")
    assert _by_gate(gates.evaluate(primary), "unsupported_version")["status"] == gates.PASS


def test_malformed_media_mount_blocks_even_when_inapplicable():
    """Malformed EVIDENCE must fail closed exactly like a malformed FLAG.

    `"false"` and `0` carry the meaning of False without being the False
    singleton, and a context templated through a shell or YAML produces
    exactly those. Keying only on the singleton let them slip through
    whenever the applicability flag was absent -- the same fail-open shape
    as the original defect, one type away.
    """
    for bogus in ("false", "true", 0, 1, [], {}):
        d = _by_gate(
            gates.evaluate(_ctx_without("targets_admin_deploy", media_mount=bogus)),
            "media_mount",
        )
        assert d["status"] == gates.BLOCK, bogus
        assert "media_mount" in d["reason"], bogus
        assert type(bogus).__name__ in d["reason"], bogus
        assert d["remedy"], bogus


def test_malformed_branch_pair_valid_blocks_even_when_inapplicable():
    for bogus in ("false", "true", 0, 1, [], {}):
        d = _by_gate(
            gates.evaluate(_ctx_without("touches_admin_public", branch_pair_valid=bogus)),
            "branch_pair",
        )
        assert d["status"] == gates.BLOCK, bogus
        assert "branch_pair_valid" in d["reason"], bogus
        assert type(bogus).__name__ in d["reason"], bogus
        assert d["remedy"], bogus


def test_malformed_evidence_does_not_leak_the_value_into_the_reason():
    """The reason names the TYPE, not the payload.

    A context can carry an instance name or a path; a reason is printed,
    logged and pasted into tickets, so it reports the shape of what
    arrived and never echoes it back.
    """
    d = _by_gate(
        gates.evaluate(_ctx(media_mount="s3cr3t-instance-name")),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK
    assert "s3cr3t-instance-name" not in d["reason"]
    assert "s3cr3t-instance-name" not in d["remedy"]
    assert "str" in d["reason"]


def test_boolean_evidence_behaviour_is_unchanged():
    """The three settled cases stay exactly as they are."""
    applies = {"targets_admin_deploy": True}
    assert _by_gate(
        gates.evaluate(_ctx(media_mount=True, **applies)), "media_mount"
    )["status"] == gates.PASS
    assert _by_gate(
        gates.evaluate(_ctx(media_mount=False, **applies)), "media_mount"
    )["status"] == gates.BLOCK
    assert _by_gate(
        gates.evaluate(_ctx_without("targets_admin_deploy", media_mount=None)),
        "media_mount",
    )["status"] == gates.PASS

    pair = {"touches_admin_public": True}
    assert _by_gate(
        gates.evaluate(_ctx(branch_pair_valid=True, **pair)), "branch_pair"
    )["status"] == gates.PASS
    assert _by_gate(
        gates.evaluate(_ctx(branch_pair_valid=False, **pair)), "branch_pair"
    )["status"] == gates.BLOCK
    assert _by_gate(
        gates.evaluate(_ctx_without("touches_admin_public", branch_pair_valid=None)),
        "branch_pair",
    )["status"] == gates.PASS
