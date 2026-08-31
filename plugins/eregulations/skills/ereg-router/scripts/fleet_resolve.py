"""Resolve fleet facts for the /ereg router.

Order: Monitor (authoritative for state) -> operator overlay -> UNRESOLVED.
There is no third source and no guessing. "Unresolved" is a real outcome
that the fail-closed gates in gates.py act on.

Posture is the one exception to Monitor precedence: it is a judgement
about whether a host is safe to touch rather than state, so the more
severe value wins whichever source supplied it. See `_worse_posture`.

Monitor's read endpoints sit behind `authenticate`, so the live path needs
a token. Without one this module still works from the overlay alone, which
is the baseline mode the plugin ships in.

stdlib-only: urllib + json. No requests, no PyYAML — hence a JSON overlay.
"""

from __future__ import annotations

import json
import os
import urllib.request

STATE_FIELDS = ("host", "version", "platform", "posture")

DEFAULT_OVERLAY = os.path.join(os.path.expanduser("~"), ".ereg", "fleet.local.json")


def load_overlay(path):
    """Read the operator overlay. Absent is fine; unreadable is not.

    Only FileNotFoundError means "absent". Catching OSError wholesale made
    a PermissionError or an IsADirectoryError indistinguishable from a file
    that was never created: both came back as `{}`, so an operator whose
    overlay cannot be read was told every fact was unresolved, and handed
    the remedy "add the fact to the overlay" for a file that already exists
    and already cannot be read. Everything except absence raises, naming
    the file, as this module's docstring and resolution.md both promise.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except FileNotFoundError:
        return {}
    try:
        overlay = json.loads(text)
    except ValueError as exc:
        raise ValueError("could not parse fleet.local.json at %s: %s" % (path, exc))
    if not isinstance(overlay, dict):
        # Same guard gates.py puts on its own JSON input. This is the loud
        # front door -- a file that parses but is not an object is one the
        # operator has to fix, not one to read as empty and then block on
        # everything with no explanation.
        raise ValueError(
            "fleet.local.json at %s must be a JSON object, got %s"
            % (path, type(overlay).__name__)
        )
    return overlay


def _as_dict(value):
    """Return `value` if it is a dict, otherwise an empty one.

    `resolve` is the tolerant half of the pair: unreadable input resolves
    to nothing rather than raising. Every field a malformed overlay
    section would have supplied ends up UNRESOLVED, which the fail-closed
    gates block on -- the same outcome as a section that was simply
    absent, and the safe one.

    Without this, a hand-edited overlay carrying `"hosts": ["host-a"]`
    where an object belongs takes the resolver down with a bare
    AttributeError. That direction is safe (no verdict is issued, so
    nothing proceeds) but it is not a verdict: the operator gets a
    traceback and a line number instead of "posture unresolved, record
    the host".
    """
    return value if isinstance(value, dict) else {}


def fetch_instance(base_url, token, slug, opener=urllib.request.urlopen):
    """GET one instance from Monitor. Returns None if unreachable.

    Unreachable is not an error here — it degrades to the overlay, and the
    gates block on whatever stays unresolved.
    """
    url = "%s/api/instances/%s" % (base_url.rstrip("/"), slug)
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", "Bearer %s" % token)
    try:
        response = opener(request, timeout=10)
    except Exception:
        return None
    try:
        with response as handle:
            return json.loads(handle.read().decode("utf-8"))
    except Exception:
        return None


# Posture, ordered by how dangerous it is to touch the host. Anything not
# named here is "unknown", which the host_posture gate blocks on.
#
# Unknown sits ABOVE degraded because the gate blocks on a posture it cannot
# read and only warns on `degraded`; it sits BELOW compromised so a garbage
# reading from one source cannot displace a real `compromised` from the other
# and swap the gate's actionable remedy ("migrate off this host") for the
# wrong one ("record the host").
_POSTURE_SEVERITY = {"ok": 0, "degraded": 1, "compromised": 3}
_UNKNOWN_POSTURE_SEVERITY = 2


def _posture_severity(value):
    if isinstance(value, str):
        return _POSTURE_SEVERITY.get(value.strip().lower(), _UNKNOWN_POSTURE_SEVERITY)
    return _UNKNOWN_POSTURE_SEVERITY


def _worse_posture(from_monitor, from_overlay):
    """For posture, the more severe of the two sources wins.

    Every other field is state, and Monitor is authoritative for state
    because state changes without anyone editing a file. Posture is not
    state in that sense -- it is a judgement about whether a host is safe
    to touch, and both sources can hold one.

    So neither source overrules the other downwards. An operator who marks
    a host compromised must not be overruled by a Monitor that is stale or
    optimistic; that is the entire reason the overlay lets them write it
    down. Equally, a Monitor reporting compromised must not be overruled by
    a stale local `ok`.

    A source with nothing to say (None) is not a vote for safety -- the
    other source's value stands, and if neither has one the field is
    UNRESOLVED, which the fail-closed gate blocks on. On equal severity
    Monitor wins, preserving its precedence where the two agree in
    substance and differ only in spelling.
    """
    if from_monitor is None:
        return from_overlay
    if from_overlay is None:
        return from_monitor
    if _posture_severity(from_overlay) > _posture_severity(from_monitor):
        return from_overlay
    return from_monitor


def _major(version):
    if not version:
        return None
    return str(version).split(".")[0]


def resolve(slug, monitor_record, overlay):
    """Merge Monitor and overlay into one context, reporting drift."""
    overlay = _as_dict(overlay)
    monitor_record = _as_dict(monitor_record)

    overlay_instance = _as_dict(_as_dict(overlay.get("instances")).get(slug))
    overlay_host = overlay_instance.get("host")
    overlay_hosts = _as_dict(overlay.get("hosts"))
    # Only a string can name a host. A dict or a list is not merely the
    # wrong value, it is an unhashable key -- `dict.get` raises TypeError
    # on it, which no amount of dict-guarding downstream would catch.
    host_record = _as_dict(overlay_hosts.get(overlay_host)) if isinstance(overlay_host, str) else {}
    overlay_view = {
        "host": overlay_host,
        "version": overlay_instance.get("version"),
        "platform": overlay_instance.get("platform"),
        "posture": host_record.get("posture"),
    }

    monitor_view = {}
    if monitor_record:
        monitor_host = monitor_record.get("host") or monitor_record.get("server")
        monitor_view = {
            "host": monitor_host,
            "version": monitor_record.get("version"),
            "platform": monitor_record.get("platform"),
            "posture": monitor_record.get("posture"),
        }

    resolved = {}
    drift = []
    for field in STATE_FIELDS:
        from_monitor = monitor_view.get(field)
        from_overlay = overlay_view.get(field)
        if field == "posture":
            resolved[field] = _worse_posture(from_monitor, from_overlay)
        else:
            resolved[field] = from_monitor if from_monitor is not None else from_overlay
        # Drift is computed from the raw sources, not from what won, so a
        # disagreement is still reported whichever way it resolved.
        if from_monitor is not None and from_overlay is not None and from_monitor != from_overlay:
            drift.append({"field": field, "monitor": from_monitor, "overlay": from_overlay})

    unresolved = [f for f in STATE_FIELDS if resolved.get(f) is None]

    context = {
        "instance": slug,
        "source": "monitor" if monitor_record else "overlay",
        "drift": drift,
        "unresolved": unresolved,
        "version_major": _major(resolved.get("version")),
    }
    context.update(resolved)
    return context


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Resolve fleet context for one instance.")
    parser.add_argument("slug")
    parser.add_argument("--overlay", default=os.environ.get("EREG_OVERLAY", DEFAULT_OVERLAY))
    parser.add_argument("--monitor-url", default=os.environ.get("EREG_MONITOR_URL"))
    parser.add_argument("--token", default=os.environ.get("EREG_MONITOR_TOKEN"))
    args = parser.parse_args(argv)

    overlay = load_overlay(args.overlay)
    record = None
    if args.monitor_url:
        record = fetch_instance(args.monitor_url, args.token, args.slug)
    print(json.dumps(resolve(args.slug, record, overlay), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
