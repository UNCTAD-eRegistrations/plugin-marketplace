"""Override auditing.

Only one gate is overridable, and it bypasses the platform's headline
policy. An override with no stated reason is refused outright; an accepted
one leaves a line behind. This is a local memory aid and an
incident-reconstruction trail, not an access control.
"""

from __future__ import annotations

import json

import audit


def _clock():
    return "2026-08-26T10:00:00+00:00"


def test_refuses_an_override_with_no_reason(tmp_path):
    log = tmp_path / "audit.jsonl"
    for empty in ("", "   ", None):
        try:
            audit.record_override(str(log), "unsupported_version", empty, {}, _clock)
        except ValueError as exc:
            assert "reason" in str(exc).lower()
        else:
            raise AssertionError("empty reason %r must be refused" % (empty,))
    assert not log.exists()


def test_accepted_override_writes_one_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    audit.record_override(
        str(log), "unsupported_version", "hotfix for a live outage",
        {"instance": "alpha", "version_major": "5"}, _clock,
    )
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["gate"] == "unsupported_version"
    assert entry["reason"] == "hotfix for a live outage"
    assert entry["timestamp"] == _clock()
    assert entry["context"]["instance"] == "alpha"


def test_appends_rather_than_truncates(tmp_path):
    log = tmp_path / "audit.jsonl"
    for i in range(3):
        audit.record_override(str(log), "unsupported_version", "reason %d" % i, {}, _clock)
    assert len(log.read_text().strip().splitlines()) == 3


def test_creates_the_parent_directory(tmp_path):
    log = tmp_path / "nested" / "deeper" / "audit.jsonl"
    audit.record_override(str(log), "unsupported_version", "because", {}, _clock)
    assert log.exists()


def test_each_line_is_independently_parseable(tmp_path):
    """JSONL, so a truncated write costs one record, not the whole log."""
    log = tmp_path / "audit.jsonl"
    audit.record_override(str(log), "unsupported_version", "one\nwith a newline", {}, _clock)
    audit.record_override(str(log), "unsupported_version", "two", {}, _clock)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["reason"] == "one\nwith a newline"
