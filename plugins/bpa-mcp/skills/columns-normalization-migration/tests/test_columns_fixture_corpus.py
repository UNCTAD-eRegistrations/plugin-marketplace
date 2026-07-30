"""Tests for the shared columns fixture corpus (language-neutral JSON).

Spec ("What changes"): add the shared fixture corpus as JSON files covering
the live-found edge cases: textarea rows:3 int, already-normalized rows,
keyless/duplicate paths, widths 1-12 bounds, editgrid-inner, adjust-columns,
and over-12.

Invariants exercised here:
  - The corpus must be language-neutral pure JSON with {input, expected}
    pairs, explicit numeric types (rows stays int 3, not 3.0), no
    NaN/Infinity, no Python reprs, order-independent comparison keys, so the
    SQL (TOBE-18007) and TS (TOBE-18006) ports can assert against the same
    reference.
  - normalize-to-12: every "expected" set of widths must sum to exactly 12.
  - Malformed/null-width inputs must be represented (asserting the walker
    raises) so ports test the fail-loud path too.
  - Dependency-inversion note: the corpus is a cross-language contract housed
    with one implementation; the corpus dir must carry a placement/relocation
    note.

If no corpus directory exists, the locator assertion fires (not a bare
FileNotFoundError at import time).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent

_CANDIDATE_DIRS = [
    SKILL_DIR / "fixtures" / "columns_corpus",
]

# Live-found edge cases that MUST be represented by at least one fixture file
# (matched case-insensitively against file names).
_REQUIRED_SCENARIOS = [
    "textarea",  # textarea rows:3 int
    "already",  # already-normalized rows
    "keyless",  # keyless path
    "duplicate",  # duplicate paths
    "bound",  # widths 1-12 bounds
    "editgrid",  # editgrid-inner
    "adjust",  # adjust-columns customClass
    "over",  # over-12
    "malformed",  # missing-key / null-width fail-loud
    "spacer",  # split track: over-12 row ending in empty spacer columns
]


def _corpus_dir() -> Path:
    for d in _CANDIDATE_DIRS:
        if d.is_dir():
            return d
    pytest.fail(
        "No columns fixture corpus directory found. Expected one of: "
        + ", ".join(str(d.relative_to(SKILL_DIR)) for d in _CANDIDATE_DIRS)
    )
    raise AssertionError  # pragma: no cover


def _reject_constant(_value: str) -> float:
    raise AssertionError(f"NaN/Infinity is not language-neutral JSON: {_value!r}")


def _strict_load(path: Path) -> object:
    """Parse JSON rejecting NaN/Infinity (not portable to SQL/TS ports)."""
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)


def _corpus_files() -> list[Path]:
    return sorted(_corpus_dir().glob("*.json"))


def test_corpus_directory_exists_and_has_files() -> None:
    files = _corpus_files()
    assert files, "columns corpus must contain at least one .json fixture"


def test_corpus_covers_all_required_scenarios() -> None:
    names = " ".join(p.name.lower() for p in _corpus_files())
    missing = [s for s in _REQUIRED_SCENARIOS if s not in names]
    assert not missing, f"corpus missing fixtures for scenarios: {missing}"


def test_every_fixture_is_strict_json_with_input_expected() -> None:
    for path in _corpus_files():
        data = _strict_load(path)
        assert isinstance(data, dict), f"{path.name}: top-level must be an object"
        assert "input" in data, f"{path.name}: must have an 'input' key"
        assert "expected" in data, f"{path.name}: must have an 'expected' key"


def test_textarea_rows_stays_integer_three_not_float() -> None:
    """The textarea fixture must keep rows as int 3 (not 3.0) end-to-end."""
    matches = [p for p in _corpus_files() if "textarea" in p.name.lower()]
    assert matches, "no textarea fixture present"

    def _walk_for_rows(node: object) -> list[object]:
        found: list[object] = []
        if isinstance(node, dict):
            if node.get("type") == "textarea" and "rows" in node:
                found.append(node["rows"])
            for v in node.values():
                found.extend(_walk_for_rows(v))
        elif isinstance(node, list):
            for v in node:
                found.extend(_walk_for_rows(v))
        return found

    for path in matches:
        raw = path.read_text(encoding="utf-8")
        # A float literal like "rows": 3.0 must never appear.
        assert '"rows": 3.0' not in raw and '"rows":3.0' not in raw, (
            f"{path.name}: rows must be an integer literal, not a float"
        )
        data = _strict_load(path)
        for rows_val in _walk_for_rows(data):
            assert isinstance(rows_val, int) and not isinstance(rows_val, bool), (
                f"{path.name}: textarea rows must be a JSON integer"
            )


def test_expected_widths_sum_to_twelve_where_present() -> None:
    """For any fixture whose 'expected' encodes normalized columns, the
    per-columns widths must sum to exactly 12."""
    seen_a_width_case = False

    def _collect_columns(node: object, out: list[list[int]]) -> None:
        if isinstance(node, dict):
            if node.get("type") == "columns" and isinstance(node.get("columns"), list):
                widths = [
                    c.get("width") for c in node["columns"] if isinstance(c, dict)
                ]
                if widths and all(isinstance(w, int) for w in widths):
                    out.append(widths)  # type: ignore[arg-type]
            for v in node.values():
                _collect_columns(v, out)
        elif isinstance(node, list):
            for v in node:
                _collect_columns(v, out)

    for path in _corpus_files():
        if "malformed" in path.name.lower() or "over" in path.name.lower():
            # 'over' fixtures may or may not encode a normalized expected set;
            # they are validated by the normalizer tests, not here.
            pass
        data = _strict_load(path)
        expected = data.get("expected") if isinstance(data, dict) else None
        if expected is None:
            continue
        cols: list[list[int]] = []
        _collect_columns(expected, cols)
        for widths in cols:
            seen_a_width_case = True
            assert sum(widths) == 12, (
                f"{path.name}: expected widths {widths} must sum to 12"
            )

    assert seen_a_width_case, (
        "at least one fixture must encode a normalized 12-column expected set"
    )


def test_malformed_fixture_marks_expected_error() -> None:
    """The malformed/null-width fixture must declare a fail-loud expectation
    so ports assert the walker raises rather than emit a corrupt plan."""
    matches = [p for p in _corpus_files() if "malformed" in p.name.lower()]
    assert matches, "no malformed/null-width fixture present"
    for path in matches:
        data = _strict_load(path)
        expected = data["expected"] if isinstance(data, dict) else {}
        blob = json.dumps(expected).lower()
        assert (
            "error" in blob or "raise" in blob or "skip" in blob or "invalid" in blob
        ), f"{path.name}: malformed fixture must declare a fail-loud expectation"


def test_corpus_records_placement_relocation_note() -> None:
    """Placement risk: the corpus is a cross-repo, cross-language reference
    housed alongside one implementation; a note must record the placement /
    relocation decision (NOVA / shared package)."""
    corpus = _corpus_dir()
    notes = list(corpus.glob("*.md")) + list(corpus.glob("*.txt"))
    assert notes, "corpus dir must carry a placement/relocation note file"
    blob = "\n".join(n.read_text(encoding="utf-8").lower() for n in notes)
    assert any(
        kw in blob
        for kw in ("interim", "relocat", "shared", "nova", "tobe-18006", "tobe-18007")
    ), "placement note must address the cross-repo dependency-inversion risk"
