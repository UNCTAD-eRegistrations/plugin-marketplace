"""Fleet resolution: Monitor is authoritative for state, the operator
overlay fills gaps, and anything neither supplies is UNRESOLVED.

`resolve` is pure — the caller passes in the Monitor record — so these
tests never touch the network. `fetch_instance` takes an injectable
opener for the same reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import fleet_resolve

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _overlay():
    return json.loads((FIXTURES / "fleet.sample.json").read_text())


def test_overlay_only_resolves_host_and_posture():
    ctx = fleet_resolve.resolve("alpha", None, _overlay())
    assert ctx["host"] == "host-safe"
    assert ctx["posture"] == "ok"
    assert ctx["version_major"] == "7"
    assert ctx["source"] == "overlay"


def test_host_absent_from_overlay_leaves_posture_unresolved():
    ctx = fleet_resolve.resolve("charlie", None, _overlay())
    assert ctx["posture"] is None
    assert "posture" in ctx["unresolved"]


def test_missing_version_is_unresolved_not_guessed():
    ctx = fleet_resolve.resolve("delta", None, _overlay())
    assert ctx["version_major"] is None
    assert "version" in ctx["unresolved"]


def test_unknown_instance_resolves_nothing():
    ctx = fleet_resolve.resolve("nosuch", None, _overlay())
    assert ctx["host"] is None
    assert ctx["posture"] is None
    assert "host" in ctx["unresolved"]


def test_an_unrecognised_slug_is_distinguishable_from_a_known_sparse_one():
    """Both come back with everything unresolved, and they are not the same.

    A slug nobody has heard of is a typo or the wrong country, and the
    answer is to ask which instance was meant. A slug that IS in the
    overlay but carries no data is a real instance missing facts, and the
    answer is to add them. Told only "unresolved", a caller cannot tell
    which it is holding -- so SKILL.md Step 2's "offer the nearest matches"
    had no trigger to fire on.
    """
    unknown = fleet_resolve.resolve("nosuch", None, _overlay())
    assert unknown["known_instance"] is False

    sparse = fleet_resolve.resolve("delta", None, _overlay())  # no version recorded
    assert sparse["known_instance"] is True
    assert "version" in sparse["unresolved"]  # still genuinely unresolved


def test_a_monitor_record_alone_marks_the_instance_known():
    """Monitor is the other place a slug can be found. An instance it
    serves is recognised whether or not the operator has written it down."""
    record = {"slug": "zulu", "host": "host-x", "version": "7.0"}
    ctx = fleet_resolve.resolve("zulu", record, _overlay())  # absent from the overlay
    assert ctx["known_instance"] is True


def test_a_slug_present_in_the_overlay_but_empty_is_still_known():
    """Presence is the question, not how much the entry carries. An entry
    holding nothing is still an operator saying "this instance exists"."""
    ctx = fleet_resolve.resolve("echo", None, {"instances": {"echo": {}}})
    assert ctx["known_instance"] is True
    assert ctx["unresolved"] == list(fleet_resolve.STATE_FIELDS)


def test_known_slugs_is_the_overlay_roster_a_caller_can_search():
    """The overlay is the only scripted source of a roster -- Monitor is
    queried one slug at a time and never listed. Without this there is
    nothing for "the nearest matches" to be drawn from."""
    ctx = fleet_resolve.resolve("nosuch", None, _overlay())
    assert ctx["known_slugs"] == ["alpha", "bravo", "charlie", "delta"]
    assert fleet_resolve.known_slugs(_overlay()) == ["alpha", "bravo", "charlie", "delta"]


def test_known_slugs_survives_the_overlay_shapes_resolve_already_tolerates():
    """Same tolerance as the rest of `resolve`: a hand-edited overlay
    yields an empty roster, never a traceback."""
    for overlay in ({}, [], "alpha", {"instances": ["alpha"]}, {"instances": None}):
        assert fleet_resolve.known_slugs(overlay) == [], overlay
        assert fleet_resolve.resolve("alpha", None, overlay)["known_slugs"] == [], overlay


def test_known_slugs_is_sorted_regardless_of_file_order():
    overlay = {"instances": {"zulu": {}, "alpha": {}, "mike": {}}}
    assert fleet_resolve.known_slugs(overlay) == ["alpha", "mike", "zulu"]


def test_monitor_wins_over_overlay_for_state():
    record = {"slug": "bravo", "host": "host-safe", "version": "7.3", "platform": "ubuntu"}
    ctx = fleet_resolve.resolve("bravo", record, _overlay())
    assert ctx["host"] == "host-safe"
    assert ctx["version"] == "7.3"
    assert ctx["source"] == "monitor"


def test_disagreement_is_reported_as_drift():
    record = {"slug": "bravo", "host": "host-safe", "version": "7.3", "platform": "ubuntu"}
    ctx = fleet_resolve.resolve("bravo", record, _overlay())
    drifted = dict((d["field"], d) for d in ctx["drift"])
    assert drifted["version"]["monitor"] == "7.3"
    assert drifted["version"]["overlay"] == "5.1"
    assert drifted["host"]["overlay"] == "host-bad"


def test_agreement_produces_no_drift():
    record = {"slug": "alpha", "host": "host-safe", "version": "7.2", "platform": "ubuntu"}
    assert fleet_resolve.resolve("alpha", record, _overlay())["drift"] == []


def test_the_more_severe_posture_wins_in_both_directions():
    """Posture is the one field Monitor does not simply win.

    An operator who marks a host compromised must not be overruled by a
    Monitor that is stale or optimistic -- that is the whole point of
    being able to write it down. Equally, a Monitor reporting compromised
    must not be overruled by a stale local `ok`. So for posture the more
    severe value wins, whichever source it came from.

    This replaces `test_monitor_posture_beats_overlay_posture`, which
    pinned the first direction as correct: against this same fixture, a
    Monitor reporting `ok` for `bravo` resolved to `ok` and the
    host_posture gate PASSED on a host the operator had recorded as
    compromised.
    """
    overlay = _overlay()

    # overlay compromised (bravo -> host-bad) + Monitor ok -> compromised
    optimistic = {"slug": "bravo", "host": "host-bad", "version": "5.1", "posture": "ok"}
    assert fleet_resolve.resolve("bravo", optimistic, overlay)["posture"] == "compromised"

    # Monitor compromised + overlay ok (alpha -> host-safe) -> compromised
    alarming = {"slug": "alpha", "host": "host-safe", "version": "7.2", "posture": "compromised"}
    assert fleet_resolve.resolve("alpha", alarming, overlay)["posture"] == "compromised"


def test_posture_disagreement_is_still_reported_as_drift():
    """Resolving to the severe value does not hide the disagreement."""
    record = {"slug": "bravo", "host": "host-bad", "version": "5.1", "posture": "ok"}
    drifted = dict(
        (d["field"], d) for d in fleet_resolve.resolve("bravo", record, _overlay())["drift"]
    )
    assert drifted["posture"]["monitor"] == "ok"
    assert drifted["posture"]["overlay"] == "compromised"


def test_degraded_outranks_ok_and_an_unreadable_posture_outranks_both():
    """The order is ok < degraded < unknown < compromised.

    Unknown sits above degraded because the host_posture gate blocks on a
    posture it cannot read and only warns on `degraded`; it sits below
    compromised so that a garbage reading from one source cannot displace
    a real `compromised` from the other and swap the gate's actionable
    remedy ("migrate off this host") for the wrong one ("record the host").
    """
    overlay = _overlay()

    # alpha's overlay posture is ok
    degraded = {"slug": "alpha", "host": "host-safe", "posture": "degraded"}
    assert fleet_resolve.resolve("alpha", degraded, overlay)["posture"] == "degraded"

    # an unreadable value must not be discarded in favour of a benign one
    for unreadable in ("wat", "", 7, {"posture": "ok"}):
        record = {"slug": "alpha", "host": "host-safe", "posture": unreadable}
        assert fleet_resolve.resolve("alpha", record, overlay)["posture"] == unreadable, unreadable

    # ...but it must not displace a real compromised either
    record = {"slug": "bravo", "host": "host-bad", "posture": "wat"}
    assert fleet_resolve.resolve("bravo", record, overlay)["posture"] == "compromised"


def test_posture_from_one_source_only_is_used_as_is():
    """Severity only arbitrates a disagreement. A single source still
    supplies the answer, and neither side absent means unresolved."""
    overlay = _overlay()

    # Monitor silent on posture -> the overlay's value stands
    assert fleet_resolve.resolve("bravo", {"slug": "bravo"}, overlay)["posture"] == "compromised"

    # overlay silent (charlie's host is unlisted) -> Monitor's value stands
    record = {"slug": "charlie", "host": "host-unlisted", "posture": "degraded"}
    assert fleet_resolve.resolve("charlie", record, overlay)["posture"] == "degraded"

    # neither -> unresolved, which the fail-closed gate blocks on
    ctx = fleet_resolve.resolve("charlie", {"slug": "charlie"}, overlay)
    assert ctx["posture"] is None
    assert "posture" in ctx["unresolved"]


def test_monitor_still_wins_the_other_three_fields():
    """Only posture changes. host, version and platform keep Monitor
    precedence: they are state, and only a live source can be right
    about state."""
    record = {
        "slug": "bravo",
        "host": "host-safe",
        "version": "7.3",
        "platform": "ubuntu",
        "posture": "ok",
    }
    ctx = fleet_resolve.resolve("bravo", record, _overlay())
    assert ctx["host"] == "host-safe"        # overlay said host-bad
    assert ctx["version"] == "7.3"           # overlay said 5.1
    assert ctx["platform"] == "ubuntu"       # overlay said windows


def test_version_major_is_the_leading_component():
    record = {"slug": "alpha", "version": "7.10.2"}
    assert fleet_resolve.resolve("alpha", record, _overlay())["version_major"] == "7"


def test_missing_overlay_file_is_empty_not_an_error():
    assert fleet_resolve.load_overlay("/nonexistent/fleet.local.json") == {}


def test_malformed_overlay_raises_rather_than_resolving_silently(tmp_path):
    bad = tmp_path / "fleet.local.json"
    bad.write_text("{not json")
    try:
        fleet_resolve.load_overlay(str(bad))
    except ValueError as exc:
        assert "fleet.local.json" in str(exc)
    else:
        raise AssertionError("a malformed overlay must raise, not resolve to {}")


def test_fetch_instance_returns_none_on_http_error():
    class Boom(Exception):
        pass

    def opener(request, timeout=None):
        raise Boom("unreachable")

    assert fleet_resolve.fetch_instance("https://example.invalid", "t", "alpha", opener) is None


def test_fetch_instance_sends_bearer_token():
    seen = {}

    class FakeResponse(object):
        def read(self):
            return b'{"slug": "alpha", "version": "7.2"}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout=None):
        seen["auth"] = request.get_header("Authorization")
        return FakeResponse()

    record = fleet_resolve.fetch_instance("https://example.invalid", "tok", "alpha", opener)
    assert seen["auth"] == "Bearer tok"
    assert record["version"] == "7.2"


def test_non_dict_overlay_shapes_resolve_to_nothing_instead_of_crashing():
    """A hand-edited overlay can put a list or a bare string where an
    object belongs, and every one of these shapes used to come out of
    `resolve` as a bare AttributeError naming a line number.

    A crash is fail-safe in direction -- no verdict is issued, so nothing
    proceeds -- but it is not a verdict, and the operator gets a
    traceback instead of "posture unresolved, record the host". Each of
    these must resolve to nothing, which the fail-closed gates then block
    on, exactly as an absent section does.
    """
    shapes = (
        [],                                                # top level is a list
        "alpha",                                           # top level is a string
        {"instances": ["alpha"]},                          # instances is a list
        {"instances": {"alpha": "host-safe"}},             # one instance is a string
        {"instances": {"alpha": {"host": "h"}}, "hosts": ["h"]},        # hosts is a list
        {"instances": {"alpha": {"host": "h"}}, "hosts": {"h": "ok"}},  # host record is a string
        {"instances": {"alpha": {"host": ["h"]}}},         # host name is unhashable
    )
    for overlay in shapes:
        ctx = fleet_resolve.resolve("alpha", None, overlay)
        assert ctx["posture"] is None, overlay
        assert "posture" in ctx["unresolved"], overlay
        assert ctx["instance"] == "alpha"


def test_non_dict_monitor_record_is_not_read_as_state():
    """Monitor's API is still moving, and a shape change can hand back a
    list where an object was expected. That must degrade to the overlay,
    not crash -- and must not be reported as `source: monitor`, because
    nothing usable came from Monitor."""
    ctx = fleet_resolve.resolve("alpha", ["not", "an", "object"], _overlay())
    assert ctx["source"] == "overlay"
    assert ctx["host"] == "host-safe"


def test_overlay_that_is_valid_json_but_not_an_object_is_rejected_loudly(tmp_path):
    """`load_overlay` is the loud front door -- malformed is not fine --
    while `resolve` is the tolerant library. A top-level list is a file
    the operator must fix, not one to silently read as empty."""
    path = tmp_path / "fleet.local.json"
    path.write_text('["host-a"]', encoding="utf-8")
    try:
        fleet_resolve.load_overlay(str(path))
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("a non-object overlay must raise")


def test_an_unreadable_overlay_is_not_treated_as_an_absent_one(tmp_path):
    """`load_overlay` swallowed every OSError, not just "not there".

    The docstring promises "Absent is fine; malformed is not", and
    resolution.md promises a loud failure naming the file. But a
    PermissionError or an IsADirectoryError came back as `{}` -- exactly
    what an absent overlay returns -- so an operator whose overlay the
    resolver cannot actually read is told every fact is unresolved, and
    the remedy they are handed is to write facts into the very file that
    is already there and already unreadable.

    Only FileNotFoundError means "absent".
    """
    a_directory = tmp_path / "fleet.local.json"
    a_directory.mkdir()
    try:
        fleet_resolve.load_overlay(str(a_directory))
    except OSError as exc:
        assert "fleet.local.json" in str(exc)
    else:
        raise AssertionError("an overlay that is a directory must raise, not resolve to {}")

    unreadable = tmp_path / "locked.json"
    unreadable.write_text('{"instances": {}}', encoding="utf-8")
    unreadable.chmod(0o000)
    try:
        fleet_resolve.load_overlay(str(unreadable))
    except OSError as exc:
        assert "locked.json" in str(exc)
    except AssertionError:
        raise
    else:
        raise AssertionError("an unreadable overlay must raise, not resolve to {}")
    finally:
        unreadable.chmod(0o600)


def test_an_absent_overlay_is_still_fine(tmp_path):
    """The one OSError that must keep degrading to {}."""
    assert fleet_resolve.load_overlay(str(tmp_path / "nope.json")) == {}


def test_cli_reports_an_unreadable_overlay_on_one_line_without_a_traceback(tmp_path, capsys):
    """An unreadable overlay must reach the operator the way audit.py and
    gates.py report their errors: one stderr line, non-zero exit, nothing on
    stdout. A traceback here is the same failure wearing a worse coat, and
    because no context is emitted no gate can return a verdict on data that
    was never read."""
    bad = tmp_path / "fleet.local.json"
    bad.write_text("{not json")

    rc = fleet_resolve.main(["alpha", "--overlay", str(bad)])
    captured = capsys.readouterr()

    assert rc != 0
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert len(captured.err.strip().splitlines()) == 1
    assert "fleet.local.json" in captured.err


def test_cli_still_degrades_quietly_when_the_overlay_is_merely_absent(tmp_path, capsys):
    """The control: absent is a state, not an error."""
    rc = fleet_resolve.main(["alpha", "--overlay", str(tmp_path / "nope.json")])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.err == ""
    assert "unresolved" in captured.out


def test_a_monitor_error_body_does_not_count_as_finding_the_slug():
    """A gateway that answers a missing slug with 200 + an error object.

    `_as_dict` rejects non-dicts, not non-instances -- an error object is a
    dict and passes straight through it. If that counted as having found the
    slug, SKILL.md Step 2 would tell the operator this is a real instance
    merely missing data and to add those facts to the overlay by hand. They
    would be inventing a record for a slug that names nothing, and the gates
    would pass on it from then on: a correct block turned into a bypass by
    following the remedy the tool printed.
    """
    error_body = {"error": "instance not found", "status": 404}
    ctx = fleet_resolve.resolve("typo-slug", error_body, {"instances": {"alpha": {}}})

    assert ctx["known_instance"] is False
    assert ctx["unresolved"] == list(fleet_resolve.STATE_FIELDS)


def test_a_monitor_record_with_any_real_field_does_count():
    """The control: one populated state field is enough to have found it."""
    for field in fleet_resolve.STATE_FIELDS:
        ctx = fleet_resolve.resolve("s", {field: "x"}, {})
        assert ctx["known_instance"] is True, field


def test_an_empty_monitor_body_does_not_count_either():
    ctx = fleet_resolve.resolve("s", {}, {})
    assert ctx["known_instance"] is False


def test_known_slugs_does_not_raise_on_mixed_type_keys():
    """JSON keys are always strings, so only a Python caller reaches this --
    but the docstring promises no traceback, and a promise a caller can break
    is not one."""
    assert fleet_resolve.known_slugs({"instances": {"b": {}, 1: {}, "a": {}}}) == ["1", "a", "b"]
