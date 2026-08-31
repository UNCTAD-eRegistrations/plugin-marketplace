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


def build_record(gate, reason, context, clock=_now):
    if reason is None or not str(reason).strip():
        raise ValueError("an override requires a stated reason")
    return {
        "timestamp": clock(),
        "gate": gate,
        "reason": reason,
        "context": context or {},
    }


def append(path, record):
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
