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
import sys
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


def known_slugs(overlay):
    """The instance slugs the overlay knows about, sorted.

    The overlay is the only scripted source of a fleet roster: Monitor is
    queried one slug at a time and has no list endpoint here. This is what
    lets a caller offer "the nearest matches" for a slug that did not
    resolve, instead of saying "unresolved" with nothing to search.

    Tolerant of the same hand-edited shapes `resolve` tolerates -- see
    `_as_dict`. A malformed overlay yields an empty roster, never a
    traceback: keys are coerced to strings first, because `sorted()` raises
    on a dict whose keys are of mixed type. JSON keys are always strings, so
    that shape only arrives from a Python caller building the dict by hand --
    but the docstring promises no traceback, and a promise a caller can break
    is not one.
    """
    return sorted(str(slug) for slug in _as_dict(_as_dict(overlay).get("instances")))


def resolve(slug, monitor_record, overlay):
    """Merge Monitor and overlay into one context, reporting drift.

    Two of the keys returned are RESOLUTION METADATA, not gate context:
    `known_instance` and `known_slugs`. They describe what this resolver
    could look the slug up in; they say nothing about the host, the
    version, the platform or the posture. `gates.py` must never read
    either, and a test in test_gates.py holds that line -- a gate reading
    `known_instance` would treat "somebody wrote this slug down" as
    evidence about an instance, which is precisely the inference the
    fail-closed design exists to forbid. A recorded slug with no facts
    behind it still leaves every field UNRESOLVED, and every gate still
    blocks on that.
    """
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
        # An empty string is an absent value wearing a value's clothes, and
        # `host` already collapses `""` to the `server` alias two lines up.
        # Doing the same for `version` and `platform` gives absence one
        # meaning across the merge, the unresolved list, and `known_instance`.
        #
        # `posture` is deliberately EXCLUDED. An unreadable posture is not an
        # absent one: `_worse_posture` ranks anything it cannot parse above
        # `degraded`, precisely so a garbage reading from one source cannot be
        # displaced by a benign `ok` from the other. Collapsing `""` to None
        # here let exactly that happen -- the overlay's `ok` won and the gate
        # passed on a host whose posture Monitor had failed to state. The
        # existing severity test caught it.
        monitor_view = dict(
            (field, None if (value == "" and field != "posture") else value)
            for field, value in monitor_view.items()
        )

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

    # An unrecognised slug and a recognised-but-sparse one are both entirely
    # unresolved, and they call for opposite responses: the first is a typo
    # or the wrong country and the answer is to ask which instance was
    # meant; the second is a real instance missing facts and the answer is
    # to record them. `unresolved` alone cannot tell them apart, so
    # SKILL.md Step 2's "offer the nearest matches" had no trigger to fire
    # on and no roster to draw from.
    #
    # `_as_dict` rejects non-dicts, NOT non-instances -- an error object is a
    # dict and sails straight through it. A gateway that answers a missing
    # slug with `200 {"error": "not found"}` instead of a 404 would otherwise
    # be read as having found it, and SKILL.md Step 2 would then tell the
    # operator this is a real instance merely missing data and to add those
    # facts to the overlay by hand. They would be inventing a record for a
    # slug that names nothing, and the gates would pass on it afterwards.
    #
    # Evaluated over `monitor_view`, NOT the raw record, so one definition of
    # "Monitor supplied this" serves the whole object. Reading the raw record
    # made it disagree with itself: `{"server": "h1"}` resolved a host FROM
    # MONITOR while reporting the slug found nowhere, and `{"host": ""}`
    # reported it found while resolving nothing.
    monitor_named_it = any(monitor_view.get(field) is not None for field in STATE_FIELDS)
    known_instance = monitor_named_it or slug in _as_dict(overlay.get("instances"))

    context = {
        "instance": slug,
        # Same definition again: a body that named nothing did not source
        # anything, however truthy it was. Otherwise an error object reported
        # `source: monitor` beside `known_instance: false`, and the two lines
        # of one object contradicted each other.
        "source": "monitor" if monitor_named_it else "overlay",
        "known_instance": known_instance,
        "known_slugs": known_slugs(overlay),
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

    # load_overlay raises on an unreadable or malformed overlay -- absent is a
    # state, unreadable is an error. Both must reach the operator as one stderr
    # line, not a traceback: gates.py and audit.py already print that shape, and
    # a traceback here is the same failure wearing a worse coat. Exit is
    # non-zero either way, so no context is emitted and no gate can return a
    # verdict on data that was never read.
    try:
        overlay = load_overlay(args.overlay)
    except (OSError, ValueError) as exc:
        sys.stderr.write("fleet_resolve.py: %s\n" % exc)
        return 2

    record = None
    if args.monitor_url:
        record = fetch_instance(args.monitor_url, args.token, args.slug)
    print(json.dumps(resolve(args.slug, record, overlay), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
