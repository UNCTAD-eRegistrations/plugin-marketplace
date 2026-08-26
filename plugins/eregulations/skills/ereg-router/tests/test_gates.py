"""Gate evaluation, with the fail-closed directions asserted explicitly.

The spec's whole point is that an UNRESOLVED input to a safety gate must
block exactly as hard as a confirmed-bad one. A first draft of the design
let unresolved posture through with a warning, which meant the gate
silently never fired whenever Monitor was unreachable. These tests exist
so that regression cannot recur.
"""

from __future__ import annotations

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


def test_unsupported_version_blocks_but_is_overridable():
    for major in ("4", "5", "6"):
        d = _by_gate(gates.evaluate(_ctx(version_major=major)), "unsupported_version")
        assert d["status"] == gates.BLOCK, major
        assert d["overridable"] is True, major


def test_unresolved_version_blocks_and_is_not_overridable():
    d = _by_gate(gates.evaluate(_ctx(version_major=None)), "unsupported_version")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_windows_target_warns_and_fails_open():
    d = _by_gate(gates.evaluate(_ctx(platform="windows")), "windows_target")
    assert d["status"] == gates.WARN
    unresolved = _by_gate(gates.evaluate(_ctx(platform=None)), "windows_target")
    assert unresolved["status"] != gates.BLOCK


def test_secondary_kinds_are_gated_too():
    """A bugfix that is also an upgrade must still hit the version gate."""
    ctx = _ctx(kind="bugfix", secondary_kinds=["upgrade"], version_major="5")
    assert _by_gate(gates.evaluate(ctx), "unsupported_version")["status"] == gates.BLOCK


def test_every_decision_carries_a_remedy():
    for d in gates.evaluate(_ctx(posture="compromised", version_major="4")):
        if d["status"] == gates.BLOCK:
            assert d["remedy"], d
