"""The live Monitor path: GET <monitor>/api/instances/by-slug/<slug>.

The Monitor serves this route since eRegulations-Monitor PR "serve fleet
facts by deploy slug". Its body is `fixtures/monitor.by-slug.sample.json`:
exactly `instance`, `host`, `posture`, `version` and `platform`. These tests
pin the URL the resolver calls and what each body does to the gates. No test
touches the network.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import fleet_resolve
import gates

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MONITOR_BODY = json.loads((FIXTURES / "monitor.by-slug.sample.json").read_text())


class _Response(object):
    def __init__(self, body):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener_returning(body, seen):
    def opener(request, timeout=None):
        seen["url"] = request.full_url
        return _Response(body)

    return opener


def _host_posture(context):
    return [d for d in gates.evaluate(context) if d["gate"] == "host_posture"][0]


def test_fetch_instance_calls_the_by_slug_route():
    seen = {}
    fleet_resolve.fetch_instance("https://monitor.example/", "t", "alpha", _opener_returning(MONITOR_BODY, seen))
    assert seen["url"] == "https://monitor.example/api/instances/by-slug/alpha"


def test_fetch_instance_quotes_the_slug_so_it_stays_one_path_segment():
    seen = {}
    fleet_resolve.fetch_instance("https://monitor.example", "t", "../users", _opener_returning({}, seen))
    assert seen["url"] == "https://monitor.example/api/instances/by-slug/..%2Fusers"


def test_an_unknown_slug_404_degrades_to_the_overlay():
    def opener(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO(b'{"code":"NOT_FOUND"}'))

    assert fleet_resolve.fetch_instance("https://monitor.example", "t", "nowhere", opener) is None


def test_the_monitor_contract_body_resolves_every_gate_field():
    ctx = fleet_resolve.resolve("alpha", MONITOR_BODY, {})
    assert ctx["source"] == "monitor"
    assert ctx["known_instance"] is True
    assert ctx["unresolved"] == []
    assert (ctx["host"], ctx["posture"], ctx["version"], ctx["version_major"], ctx["platform"]) == (
        "host-safe", "ok", "7.7.9", "7", "linux",
    )
    assert _host_posture(ctx)["status"] == gates.PASS


def test_an_unassessed_monitor_host_blocks_even_when_the_overlay_says_ok():
    body = dict(MONITOR_BODY, posture="unknown")
    overlay = {"instances": {"alpha": {"host": "host-safe"}}, "hosts": {"host-safe": {"posture": "ok"}}}
    ctx = fleet_resolve.resolve("alpha", body, overlay)
    assert ctx["posture"] == "unknown"
    assert _host_posture(ctx)["status"] == gates.BLOCK


def test_an_overlay_compromised_marking_beats_a_monitor_ok():
    overlay = {"instances": {"alpha": {"host": "host-safe"}}, "hosts": {"host-safe": {"posture": "compromised"}}}
    ctx = fleet_resolve.resolve("alpha", MONITOR_BODY, overlay)
    assert ctx["posture"] == "compromised"
    assert {"field": "posture", "monitor": "ok", "overlay": "compromised"} in ctx["drift"]
    assert _host_posture(ctx)["status"] == gates.BLOCK


def test_a_monitor_without_a_server_leaves_posture_to_the_overlay():
    body = dict(MONITOR_BODY, host=None, posture=None)
    overlay = {"instances": {"alpha": {"host": "host-safe"}}, "hosts": {"host-safe": {"posture": "degraded"}}}
    ctx = fleet_resolve.resolve("alpha", body, overlay)
    assert ctx["host"] == "host-safe"
    assert ctx["posture"] == "degraded"


def test_a_monitor_without_a_server_and_no_overlay_blocks():
    body = dict(MONITOR_BODY, host=None, posture=None)
    ctx = fleet_resolve.resolve("alpha", body, {})
    assert "posture" in ctx["unresolved"]
    assert _host_posture(ctx)["status"] == gates.BLOCK


def test_a_null_monitor_version_falls_back_to_the_overlay_version():
    body = dict(MONITOR_BODY, version=None)
    overlay = {"instances": {"alpha": {"version": "7.7.1"}}}
    assert fleet_resolve.resolve("alpha", body, overlay)["version"] == "7.7.1"
