"""Record gate overrides to ~/.ereg/audit.jsonl.

JSONL rather than JSON so an interrupted write costs one record instead of
the whole log, and so appending never requires reading what is already
there.

The clock is injectable purely so tests can assert an exact timestamp.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

DEFAULT_LOG = os.path.join(os.path.expanduser("~"), ".ereg", "audit.jsonl")


def _now():
    return datetime.now().astimezone().isoformat()


def _require_reason(reason):
    """The one rule this module exists to enforce, in one place.

    A whitespace-only reason is a blank one. Only a string can be a reason:
    `str()` on a container produces something non-empty -- `str({})` is
    `"{}"`, `str(0)` is `"0"` -- so judging a non-string by what it would be
    written as lets an empty object through as a justification. The type
    check is what makes the emptiness test mean anything.
    """
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("an override requires a stated reason")
    return reason


def build_record(gate, reason, context, clock=_now):
    _require_reason(reason)
    return {
        "timestamp": clock(),
        "gate": gate,
        "reason": reason,
        "context": context or {},
    }


def append(path, record):
    """Append one record, refusing any that states no reason.

    `record_override` already validates before calling this, so the guard
    is defence in depth rather than a live hole -- but the invariant it
    protects ("the one overridable gate is never bypassed without a stated
    reason") is the whole reason this module exists, and it was enforced in
    exactly one place. A caller importing `append` directly wrote a
    reasonless record and the log then claimed an override with nothing
    behind it, which is worse than no log at all.

    `append` is not a general-purpose JSONL writer that happens to be used
    here: this module has one record shape, one caller, and one purpose, so
    the reason belongs to the write, not only to the layer above it.

    Refused BEFORE anything is written, and before the parent directory is
    created -- a refused override leaves no trace of having been attempted
    through a path that could not carry it. Same ValueError as
    `build_record`, so `record_override` is unchanged in behaviour: it
    still raises from `build_record` first, with the same message, having
    written nothing.
    """
    _require_reason(record.get("reason") if isinstance(record, dict) else None)
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        # exist_ok, because the isdir check above is not a lock. Two
        # concurrent sessions recording an override before ~/.ereg exists
        # both see False and both call makedirs; without this the loser got
        # an uncaught FileExistsError traceback, where the rest of the
        # toolchain prints one stderr line. Concurrent sessions against one
        # home directory are normal here.
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def record_override(path, gate, reason, context, clock=_now):
    """Validate, then append. Raises ValueError before writing anything."""
    record = build_record(gate, reason, context, clock)
    append(path, record)
    return record


def main(argv=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Record a gate override.")
    parser.add_argument("--gate", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--context", default="{}")
    parser.add_argument("--log", default=DEFAULT_LOG)
    args = parser.parse_args(argv)
    try:
        record = record_override(args.log, args.gate, args.reason, json.loads(args.context))
    except ValueError as exc:
        sys.stderr.write("audit.py: %s\n" % exc)
        return 2
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
