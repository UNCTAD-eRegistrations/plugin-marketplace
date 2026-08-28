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


def test_unrecognised_slug_is_distinguishable_from_a_known_sparse_one():
    """An unknown slug and a known-but-sparse one used to come back
    identically all-unresolved, with no way to tell "typo, never heard of
    it" apart from "real instance, just missing data". known_instance
    makes that distinction explicit."""
    unknown = fleet_resolve.resolve("nosuch", None, _overlay())
    assert unknown["known_instance"] is False

    sparse = fleet_resolve.resolve("delta", None, _overlay())  # missing version
    assert sparse["known_instance"] is True
    assert sparse["version_major"] is None  # still genuinely unresolved


def test_monitor_record_alone_marks_the_instance_known():
    record = {"slug": "zulu", "host": "host-x", "version": "7.0"}
    ctx = fleet_resolve.resolve("zulu", record, _overlay())  # not in the overlay at all
    assert ctx["known_instance"] is True


def test_known_slugs_lists_the_overlay_instance_roster():
    """The overlay is the only scripted source of a fleet roster, so a
    caller offering "the nearest matches" for an unrecognised slug needs
    a real list to search -- not just the word "unresolved"."""
    ctx = fleet_resolve.resolve("nosuch", None, _overlay())
    assert ctx["known_slugs"] == ["alpha", "bravo", "charlie", "delta"]
    assert fleet_resolve.known_slugs(_overlay()) == ["alpha", "bravo", "charlie", "delta"]
    assert fleet_resolve.known_slugs({}) == []


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
