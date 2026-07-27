"""Tests for the command-line entry point of the columns_logic script.

Spec ("What changes"): the columns_logic module is runnable as a script —
`python3 scripts/columns_logic.py` — with no install step.

Edge case: the CLI receives non-JSON or an unexpected form shape — it must
validate its input schema and FAIL LOUD with a clear error rather than
crashing the walker or emitting a corrupt plan consumed downstream unnoticed.

Exercised both via the in-process `main` entry (assertion on exit code /
raised error) and via a real subprocess (assertion on non-zero exit + stderr
message).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MODULE_PATH = SCRIPTS_DIR / "columns_logic.py"

_VALID_FORM = {
    "components": [
        {
            "key": "row1",
            "type": "columns",
            "columns": [
                {"width": 4, "components": []},
                {"width": 4, "components": []},
            ],
        }
    ]
}


def _run_cli(stdin_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def _assert_module_present(proc: subprocess.CompletedProcess[str]) -> None:
    """A missing script must not masquerade as a fail-loud validation error.

    Without this guard the fail-loud tests would pass for the wrong reason
    (a missing file exits non-zero too). We require the script to be present
    and runnable so the assertion under test is validation, not absence.
    """
    assert MODULE_PATH.is_file(), f"columns_logic.py not found at {MODULE_PATH}"
    combined = (proc.stderr + proc.stdout).lower()
    assert (
        "no module named" not in combined
        and "modulenotfounderror" not in combined
        and "no such file or directory" not in combined
    ), f"{MODULE_PATH} is not runnable; CLI cannot be exercised yet:\n{proc.stderr}"


def test_cli_valid_form_emits_json_plan_and_exits_zero() -> None:
    """A well-formed form on stdin yields a JSON plan and a 0 exit code."""
    proc = _run_cli(json.dumps(_VALID_FORM))
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    # Output must be parseable JSON (the plan), not a Python repr.
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, (dict, list))


def test_cli_non_json_input_fails_loud() -> None:
    """Non-JSON stdin must fail loud (non-zero exit + explanatory stderr)."""
    proc = _run_cli("this is not json {{{")
    _assert_module_present(proc)
    assert proc.returncode != 0
    assert proc.stderr.strip(), "CLI must print a clear error to stderr"
    # Must NOT emit a plan on stdout for invalid input.
    assert proc.stdout.strip() == "" or "error" in proc.stdout.lower()


def test_cli_unexpected_shape_fails_loud() -> None:
    """Valid JSON of the wrong shape (no components) must be rejected."""
    proc = _run_cli(json.dumps({"not": "a form"}))
    _assert_module_present(proc)
    assert proc.returncode != 0
    assert proc.stderr.strip(), "CLI must reject an unexpected form shape"


def test_cli_null_width_fails_loud_not_corrupt_plan() -> None:
    """A partial/malformed component tree must be rejected, not normalized."""
    bad = {
        "components": [
            {
                "key": "row1",
                "type": "columns",
                "columns": [{"width": None, "components": []}],
            }
        ]
    }
    proc = _run_cli(json.dumps(bad))
    _assert_module_present(proc)
    assert proc.returncode != 0
    assert proc.stderr.strip()


def test_cli_main_callable_rejects_non_json() -> None:
    """In-process seam: main() must exit non-zero / raise on non-JSON input."""
    from columns_logic import main

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        main(["--stdin"], stdin_text="not json")  # type: ignore[call-arg]
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code not in (0, None)
