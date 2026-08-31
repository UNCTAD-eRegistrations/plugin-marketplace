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


def test_monitor_posture_beats_overlay_posture():
    record = {"slug": "bravo", "host": "host-bad", "version": "5.1", "posture": "ok"}
    assert fleet_resolve.resolve("bravo", record, _overlay())["posture"] == "ok"


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
