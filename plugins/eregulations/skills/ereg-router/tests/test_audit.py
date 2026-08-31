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


def test_append_refuses_a_record_with_no_stated_reason(tmp_path):
    """`append` validated nothing of its own.

    `record_override` is the only entry point this module exposes, and it
    validates first -- so this was never a live hole. But the invariant
    ("the one overridable gate is never bypassed without a stated reason")
    is the entire reason this module exists, and it was enforced in one
    place only: a caller importing `append` directly wrote a reasonless
    record and the log said an override happened with nothing behind it.
    An invariant worth having is worth enforcing where the write happens.

    Same ValueError, and nothing reaches disk -- not even the parent
    directory, which `append` would otherwise create on its way to a write
    it must refuse.
    """
    log = tmp_path / "nested" / "audit.jsonl"
    for record in (
        {"gate": "unsupported_version"},                       # no reason at all
        {"gate": "unsupported_version", "reason": ""},         # blank
        {"gate": "unsupported_version", "reason": "   "},      # whitespace only
        {"gate": "unsupported_version", "reason": None},       # explicitly none
    ):
        try:
            audit.append(str(log), record)
        except ValueError as exc:
            assert "reason" in str(exc).lower()
        else:
            raise AssertionError("reasonless record %r must be refused" % (record,))
    assert not log.exists()
    assert not log.parent.exists()


def test_append_still_writes_a_record_that_states_one(tmp_path):
    """The guard refuses only what it is there to refuse."""
    log = tmp_path / "audit.jsonl"
    audit.append(str(log), {"gate": "unsupported_version", "reason": "a stated reason"})
    assert len(log.read_text().strip().splitlines()) == 1


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


def test_cli_refuses_a_blank_reason_cleanly(capsys, tmp_path):
    """A blank --reason is the one case that IS an execution failure.

    It must not surface as a traceback: gates.py's CLI was already fixed to
    print one clean line and exit 2 for "could not run" cases, and audit.py
    must match rather than leaking a stack trace.
    """
    log = tmp_path / "audit.jsonl"

    status = audit.main(["--gate", "unsupported_version", "--reason", "   ", "--log", str(log)])

    assert status == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "audit.py:" in captured.err
    assert "Traceback" not in captured.err
    assert captured.err.strip().count("\n") == 0  # one line, not a dump
    assert not log.exists()


def test_append_survives_losing_the_directory_creation_race(tmp_path, monkeypatch):
    """`os.makedirs` without exist_ok=True races with a concurrent session.

    Two overrides recorded before ~/.ereg exists both see `isdir` False,
    both call makedirs, and the loser gets an uncaught FileExistsError
    traceback where the rest of the toolchain prints one stderr line.
    Concurrent sessions against one home directory are normal here.

    Reproduced deterministically rather than with threads: the loser's
    state IS "my isdir check said no, and by the time I called makedirs the
    directory was there". Only the first isdir call is stale -- every later
    one, including the one makedirs itself makes to honour exist_ok, sees
    the real filesystem.
    """
    log = tmp_path / "nested" / "audit.jsonl"
    (tmp_path / "nested").mkdir()  # the winning session got there first

    import os as _os

    real_isdir = _os.path.isdir
    calls = {"n": 0}

    def stale_first_isdir(path):
        calls["n"] += 1
        return False if calls["n"] == 1 else real_isdir(path)

    monkeypatch.setattr(_os.path, "isdir", stale_first_isdir)

    audit.append(
        str(log), {"gate": "unsupported_version", "reason": "a stated reason"}
    )

    assert len(log.read_text().strip().splitlines()) == 1
