"""Resolve fleet facts for the /ereg router.

Order: Monitor (authoritative for state) -> operator overlay -> UNRESOLVED.
There is no third source and no guessing. "Unresolved" is a real outcome
that the fail-closed gates in gates.py act on.

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
    """Read the operator overlay. Absent is fine; malformed is not."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except (IOError, OSError, ValueError):
        return {}
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ValueError("could not parse fleet.local.json at %s: %s" % (path, exc))


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


def _major(version):
    if not version:
        return None
    return str(version).split(".")[0]


def resolve(slug, monitor_record, overlay):
    """Merge Monitor and overlay into one context, reporting drift."""
    overlay_instance = (overlay.get("instances") or {}).get(slug) or {}
    overlay_host = overlay_instance.get("host")
    overlay_hosts = overlay.get("hosts") or {}
    overlay_view = {
        "host": overlay_host,
        "version": overlay_instance.get("version"),
        "platform": overlay_instance.get("platform"),
        "posture": (overlay_hosts.get(overlay_host) or {}).get("posture"),
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
        resolved[field] = from_monitor if from_monitor is not None else from_overlay
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
