"""Tests for the command-line entry points of the two APPLY scripts.

Spec ("What changes"): `columns_apply.py` and `columns_split_apply.py` are
runnable as scripts — `python3 scripts/columns_apply.py` — with no install
step, so the skill drives them by pipe instead of importing them from the MCP
server's virtualenv.

Why this file exists: the skill pipes one script's **stdout** into the next
stage and ultimately into a `form_patch` WRITE. So the load-bearing invariant
is not merely "exits non-zero on bad input" — it is that a failing run emits
**nothing at all on stdout**. A CLI that printed a partial result before
dying would feed a truncated operation list into a last-write-wins write.
Every fail-loud case below therefore asserts an EMPTY stdout, not just a
non-zero exit code.

Edge cases covered: non-JSON stdin, a top-level JSON array instead of an
object, a missing required array, and a present-but-non-list array (which
must never be silently defaulted to `[]` — an empty apply and a malformed
payload must not look identical).

Exercised both via a real subprocess (the way the skill invokes them) and via
the in-process `main` seam, mirroring test_columns_logic_cli.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
APPLY_PATH = SCRIPTS_DIR / "columns_apply.py"
SPLIT_APPLY_PATH = SCRIPTS_DIR / "columns_split_apply.py"
SPLIT_SCAN_PATH = SCRIPTS_DIR / "columns_split.py"

# An over-12 row (8 + 8 = 16) whose columns carry FIELDS. Until marketplace #58 this
# fixture was `[8,8]` with both columns empty — which, once content-less groups
# are dropped, is no longer a splittable row at all but an `all_columns_empty`
# review row. It only ever "worked" here because the scan used to emit two
# containers holding no fields, i.e. the fixture encoded the defect. The pipe
# contract this test exists for needs a row that genuinely splits.
_OVER_12_FORM = {
    "components": [
        {
            "key": "row1",
            "type": "columns",
            "columns": [
                {"width": 8, "components": [{"key": "f0", "type": "textfield"}]},
                {"width": 8, "components": [{"key": "f1", "type": "textfield"}]},
            ],
        }
    ]
}

# The same shape with no content anywhere: every group is content-less, so the
# scan surfaces it as a review row instead of splitting it (marketplace #58).
_ALL_EMPTY_OVER_12_FORM = {
    "components": [
        {
            "key": "row1",
            "type": "columns",
            "columns": [
                {"width": 8, "components": []},
                {"width": 8, "components": []},
            ],
        }
    ]
}


def _run(script: Path, stdin_text: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def _assert_script_present(
    script: Path, proc: subprocess.CompletedProcess[str]
) -> None:
    """A missing script must not masquerade as a fail-loud validation error.

    Without this guard every fail-loud test would pass for the wrong reason:
    a nonexistent file also exits non-zero.
    """
    assert script.is_file(), f"{script.name} not found at {script}"
    combined = (proc.stderr + proc.stdout).lower()
    assert (
        "no module named" not in combined
        and "modulenotfounderror" not in combined
        and "no such file or directory" not in combined
    ), f"{script} is not runnable; CLI cannot be exercised:\n{proc.stderr}"


def _assert_fails_loud_with_empty_stdout(
    script: Path, proc: subprocess.CompletedProcess[str]
) -> None:
    """The pipe-safety invariant: non-zero exit AND nothing on stdout."""
    _assert_script_present(script, proc)
    assert proc.returncode != 0, f"expected non-zero exit, got {proc.returncode}"
    assert proc.stderr.strip(), "CLI must print a clear error to stderr"
    assert proc.stdout == "", (
        "CLI must emit NOTHING on stdout when it fails — the skill pipes "
        f"stdout into a form_patch write. Got: {proc.stdout!r}"
    )


# ---------------------------------------------------------------------------
# happy paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", [APPLY_PATH, SPLIT_APPLY_PATH])
def test_cli_empty_payload_emits_json_and_exits_zero(script: Path) -> None:
    """An empty (but well-formed) payload yields JSON and a 0 exit code."""
    proc = _run(script, json.dumps({"plan_rows": [], "live_components": []}))
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    assert parsed["operations"] == []


def test_split_apply_cli_revert_flag_emits_json_and_exits_zero() -> None:
    """--revert reads applied_rows and yields the restore operations."""
    proc = _run(
        SPLIT_APPLY_PATH,
        json.dumps({"applied_rows": [], "live_components": []}),
        "--revert",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    assert parsed["operations"] == []


def test_scan_output_pipes_into_split_apply_unchanged() -> None:
    """The real pipe the skill runs: columns_split.py | columns_split_apply.py.

    This is the contract that matters most. The scan's stdout must be
    consumable as the apply's plan_rows with no reshaping in between — if the
    two scripts ever disagree on that JSON shape, the skill breaks at write
    time, not at scan time.
    """
    scan = _run(SPLIT_SCAN_PATH, json.dumps(_OVER_12_FORM))
    assert scan.returncode == 0, f"scan failed: {scan.stderr}"
    plan_rows = json.loads(scan.stdout)
    assert plan_rows, "fixture should produce at least one over-12 split row"

    apply_proc = _run(
        SPLIT_APPLY_PATH,
        json.dumps(
            {
                "plan_rows": plan_rows,
                "live_components": _OVER_12_FORM["components"],
            }
        ),
    )
    assert apply_proc.returncode == 0, f"apply failed: {apply_proc.stderr}"
    result = json.loads(apply_proc.stdout)
    assert result["operations"], (
        "a live over-12 row re-verified against its own form must produce "
        f"operations; got {result!r}"
    )


# ---------------------------------------------------------------------------
# fail-loud paths — every one asserts EMPTY stdout
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", [APPLY_PATH, SPLIT_APPLY_PATH])
def test_cli_non_json_input_fails_loud(script: Path) -> None:
    proc = _run(script, "this is not json {{{")
    _assert_fails_loud_with_empty_stdout(script, proc)
    assert "invalid json" in proc.stderr.lower()


@pytest.mark.parametrize("script", [APPLY_PATH, SPLIT_APPLY_PATH])
def test_cli_top_level_array_fails_loud(script: Path) -> None:
    """Valid JSON of the wrong kind (an array, not an object) is rejected."""
    proc = _run(script, json.dumps([]))
    _assert_fails_loud_with_empty_stdout(script, proc)


@pytest.mark.parametrize("script", [APPLY_PATH, SPLIT_APPLY_PATH])
@pytest.mark.parametrize("missing", ["plan_rows", "live_components"])
def test_cli_missing_required_array_fails_loud(script: Path, missing: str) -> None:
    payload = {"plan_rows": [], "live_components": []}
    del payload[missing]
    proc = _run(script, json.dumps(payload))
    _assert_fails_loud_with_empty_stdout(script, proc)
    assert missing in proc.stderr


@pytest.mark.parametrize("script", [APPLY_PATH, SPLIT_APPLY_PATH])
def test_cli_non_list_array_is_not_silently_defaulted(script: Path) -> None:
    """A present-but-non-list key must fail, never coerce to an empty apply.

    An empty apply and a malformed payload must not produce identical output —
    otherwise a caller that garbled its plan sees a clean "0 operations" and
    concludes there was nothing to do.
    """
    proc = _run(script, json.dumps({"plan_rows": {}, "live_components": []}))
    _assert_fails_loud_with_empty_stdout(script, proc)
    assert "plan_rows" in proc.stderr


def test_split_apply_cli_revert_rejects_apply_shaped_payload() -> None:
    """--revert must not silently accept a plan_rows payload."""
    proc = _run(
        SPLIT_APPLY_PATH,
        json.dumps({"plan_rows": [], "live_components": []}),
        "--revert",
    )
    _assert_fails_loud_with_empty_stdout(SPLIT_APPLY_PATH, proc)
    assert "applied_rows" in proc.stderr


# ---------------------------------------------------------------------------
# in-process seam
# ---------------------------------------------------------------------------


def test_apply_main_callable_rejects_non_json() -> None:
    from columns_apply import main

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        main(["--stdin"], stdin_text="not json")
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code not in (0, None)


def test_split_apply_main_callable_rejects_non_json() -> None:
    from columns_split_apply import main

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        main(["--stdin"], stdin_text="not json")
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code not in (0, None)


def test_split_apply_main_callable_revert_rejects_missing_applied_rows() -> None:
    from columns_split_apply import main

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        main(["--revert"], stdin_text=json.dumps({"live_components": []}))
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code not in (0, None)


def test_all_empty_over_12_row_pipes_through_as_review_without_operations() -> None:
    """The companion to the pipe contract above (marketplace #58).

    A row whose every group is content-less must survive the same pipe: the
    scan surfaces it as `review`, and the apply must consume that row shape
    without error and emit NOTHING. Emitting the bare `remove` would delete an
    authored component and put nothing back.
    """
    scan = _run(SPLIT_SCAN_PATH, json.dumps(_ALL_EMPTY_OVER_12_FORM))
    assert scan.returncode == 0, f"scan failed: {scan.stderr}"
    plan_rows = json.loads(scan.stdout)

    assert len(plan_rows) == 1
    assert plan_rows[0]["action"] == "review"
    assert plan_rows[0]["reason"] == "all_columns_empty"

    apply_proc = _run(
        SPLIT_APPLY_PATH,
        json.dumps(
            {
                "plan_rows": plan_rows,
                "live_components": _ALL_EMPTY_OVER_12_FORM["components"],
            }
        ),
    )
    assert apply_proc.returncode == 0, f"apply failed: {apply_proc.stderr}"
    result = json.loads(apply_proc.stdout)
    assert result["operations"] == []
    assert result["applied_rows"] == []
