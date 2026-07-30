"""Tests for the ported `columns_logic` module (stdlib-only walker +
normalize-to-12 rules).

Spec ("What changes"): move `tools/columns_logic.py` into the package as a
NON-tool module (not registered with the MCP server), stdlib-only, with a
`python -m` CLI (CLI covered in test_columns_logic_cli.py).

Invariants exercised here:
  - columns_logic.py must remain stdlib-only (no third-party deps). This is
    what lets the script run under a bare `python3` with no install step.
  - columns_logic.py must NOT be an MCP tool. That guarantee is now
    structural: the module lives with this skill, not in the MCP package, so
    there is no server to register it with.
  - The walker normalizes ONLY column-layout width fields and must never
    rewrite a textarea's `rows` (or any non-width int prop) — the textarea
    rows:3 input must round-trip byte-identical.
  - normalize-to-12 must always yield widths summing to exactly 12 for every
    input (all-equal, single-column, boundary 1-12, over-12), with an
    explicit remainder-assignment step.
  - The walker/normalizer must fail loud on a malformed/partial component
    tree (missing keys, null widths) rather than emit a corrupt plan.
  - Keyless / duplicated component paths must be resolvable unambiguously or
    skipped/reported — never applied to a first/arbitrary match.

These tests are RED until the salvaged module is ported into this package.
Module-under-test symbols are imported inside each test so the server-side
CI guard (which does not touch columns_logic) can still run.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MODULE_PATH = SCRIPTS_DIR / "columns_logic.py"

# Sibling flat modules that ship with this skill. Importing one of these from
# another is intra-skill, not a third-party dependency.
_LOCAL_MODULES = {
    "columns_logic",
    "columns_split",
    "columns_apply",
    "columns_split_apply",
}


# ---------------------------------------------------------------------------
# stdlib-only invariant
# ---------------------------------------------------------------------------
def test_columns_logic_is_stdlib_only() -> None:
    """The module must not import any third-party package."""
    assert MODULE_PATH.is_file(), f"columns_logic.py not found at {MODULE_PATH}"
    with open(MODULE_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    stdlib_ok = {
        "copy",
        "json",
        "sys",
        "argparse",
        "dataclasses",
        "typing",
        "collections",
        "collections.abc",
        "__future__",
        "math",
        "itertools",
        "enum",
    }
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _LOCAL_MODULES:
                    continue
                if top not in {m.split(".")[0] for m in stdlib_ok}:
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative intra-package import is fine
                continue
            top = (node.module or "").split(".")[0]
            if node.module and top not in {m.split(".")[0] for m in stdlib_ok}:
                if top in _LOCAL_MODULES:
                    continue
                offenders.append(node.module)
    assert not offenders, f"columns_logic must be stdlib-only; found {offenders}"


# ---------------------------------------------------------------------------
# normalize-to-12 redistribution invariant
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "widths",
    [
        [1, 1],  # all-equal, small
        [3, 3, 3, 3],  # already summing to 12
        [5],  # single column
        [1],  # boundary low, single
        [12],  # boundary high, single
        [6, 6],  # even split
        [8, 8],  # over-12 -> must be brought down to 12
        [11, 11, 11],  # heavy over-12
        [1, 2, 3, 4, 5, 6, 7],  # many columns
        [2, 2, 2],  # under-12, not divisible evenly into 12
    ],
)
def test_normalize_to_12_sums_to_exactly_twelve(widths: list[int]) -> None:
    from columns_logic import normalize_to_12

    out = normalize_to_12(widths)
    assert sum(out) == 12, f"{widths} -> {out} must sum to 12"
    assert len(out) == len(widths), "column count must be preserved"
    assert all(isinstance(w, int) and not isinstance(w, bool) for w in out)
    assert all(w >= 1 for w in out), "every column keeps a positive width"


def test_normalize_to_12_is_deterministic_remainder_assignment() -> None:
    """Remainder must be assigned by an explicit, stable rule (repeatable)."""
    from columns_logic import normalize_to_12

    first = normalize_to_12([1, 1, 1])
    second = normalize_to_12([1, 1, 1])
    assert first == second
    assert sum(first) == 12


def test_normalize_to_12_fails_loud_on_null_width() -> None:
    """A malformed/partial tree (null width) must raise, not misredistribute."""
    from columns_logic import normalize_to_12

    with pytest.raises((ValueError, TypeError)):
        normalize_to_12([None, 3])  # type: ignore[list-item]


def test_normalize_to_12_fails_loud_on_non_int_width() -> None:
    from columns_logic import normalize_to_12

    with pytest.raises((ValueError, TypeError)):
        normalize_to_12(["6", 6])  # type: ignore[list-item]


def test_normalize_to_12_fails_loud_on_empty() -> None:
    from columns_logic import normalize_to_12

    with pytest.raises((ValueError, ZeroDivisionError)):
        normalize_to_12([])


# ---------------------------------------------------------------------------
# walker: finds columns, flags editgrid-inner, preserves paths
# ---------------------------------------------------------------------------
def _columns(key: str, widths: list[int]) -> dict:
    return {
        "key": key,
        "type": "columns",
        "columns": [{"width": w, "components": []} for w in widths],
    }


def test_walker_finds_top_level_columns() -> None:
    from columns_logic import iter_columns_components

    form = [_columns("row1", [4, 4]), {"key": "txt", "type": "textfield"}]
    hits = list(iter_columns_components(form))
    assert len(hits) == 1
    assert hits[0].component["key"] == "row1"
    assert hits[0].inside_grid is False


def test_walker_flags_editgrid_inner_columns() -> None:
    from columns_logic import iter_columns_components

    form = [
        {
            "key": "grid",
            "type": "editgrid",
            "components": [_columns("innerRow", [4, 4])],
        }
    ]
    hits = list(iter_columns_components(form))
    assert len(hits) == 1
    assert hits[0].component["key"] == "innerRow"
    assert hits[0].inside_grid is True


def test_walker_surfaces_duplicate_paths_for_ambiguity_detection() -> None:
    """Duplicated component paths must both be visible so downstream can
    resolve unambiguously or skip — never silently pick the first match."""
    from columns_logic import iter_columns_components

    form = [
        {
            "key": "panel",
            "type": "panel",
            "components": [_columns("dup", [4, 4]), _columns("dup", [3, 3])],
        }
    ]
    hits = list(iter_columns_components(form))
    assert len(hits) == 2
    assert hits[0].path == hits[1].path, "both duplicates share a path"


# ---------------------------------------------------------------------------
# walker must never rewrite a textarea's rows (or any non-width int prop)
# ---------------------------------------------------------------------------
def test_walker_does_not_touch_textarea_rows_roundtrip_identical() -> None:
    from columns_logic import iter_columns_components

    textarea = {"key": "notes", "type": "textarea", "rows": 3, "label": "Notes"}
    form = [deepcopy(textarea), _columns("row1", [4, 4])]
    original = deepcopy(form)

    hits = list(iter_columns_components(form))

    # No textarea is ever yielded as a columns hit.
    assert all(h.component.get("type") == "columns" for h in hits)
    # rows must remain int 3 (not float, not rewritten) and byte-identical.
    assert form[0] == original[0]
    assert form[0]["rows"] == 3
    assert type(form[0]["rows"]) is int


def test_analyze_never_introduces_rows_key_into_columns() -> None:
    from columns_logic import analyze_columns_component

    comp = _columns("row1", [4, 4])  # sum 8 -> under 12, should pad
    verdict = analyze_columns_component(comp, inside_grid=False)
    if verdict.new_columns is not None:
        for col in verdict.new_columns:
            assert "rows" not in col, "normalizer must not write a rows prop"
        total = sum(c["width"] for c in verdict.new_columns)
        assert total == 12


# ---------------------------------------------------------------------------
# analyze skip rules (adjust-columns, keyless, already-normalized)
# ---------------------------------------------------------------------------
def test_analyze_skips_adjust_columns_custom_class() -> None:
    from columns_logic import analyze_columns_component

    comp = _columns("row1", [4, 4])
    comp["customClass"] = "adjust-columns"
    verdict = analyze_columns_component(comp)
    assert verdict.action == "skip"


def test_analyze_skips_keyless_component() -> None:
    from columns_logic import analyze_columns_component

    comp = _columns("", [4, 4])
    comp["key"] = ""
    verdict = analyze_columns_component(comp)
    assert verdict.action == "skip"


def test_analyze_skips_already_normalized_row() -> None:
    from columns_logic import analyze_columns_component

    comp = _columns("row1", [6, 6])  # already sums to 12
    verdict = analyze_columns_component(comp)
    assert verdict.action == "skip"


def test_target_sum_constant_is_twelve() -> None:
    from columns_logic import TARGET_SUM

    assert TARGET_SUM == 12


# ---------------------------------------------------------------------------
# two-class in-grid rule (TOBE-18037)
# ---------------------------------------------------------------------------
# The DS editgrid grid rule (`:where(.editing-entry, .new-entry) >
# .formio-component-columns.row { display: grid; ... }`) uses a DIRECT-CHILD
# combinator, and the per-width `grid-column: span N` loop makes a
# direct-child row wrap into implicit rows by construction — those rows are
# already correct and must never be padded or split. A row nested one or more
# panels DEEPER never matches and falls through to the ordinary #171 fluid
# flex model like any top-level row. Confirmed at effect level on live
# test.kenya (Chrome display badges; TOBE-18037 task zero, comment 103432).
# The old sticky `inside_grid` boolean conflated the two classes.


def _panel(key: str, children: list[dict]) -> dict:
    return {"key": key, "type": "panel", "components": children}


def _editgrid(key: str, children: list[dict]) -> dict:
    return {"key": key, "type": "editgrid", "components": children}


def test_walker_classifies_direct_child_of_editgrid() -> None:
    from columns_logic import iter_columns_components

    form = [_editgrid("grid", [_columns("directRow", [4, 4])])]
    hits = list(iter_columns_components(form))
    assert len(hits) == 1
    assert hits[0].grid_context == "direct_child"
    assert hits[0].inside_grid is True  # compat: bool stays derivable


def test_walker_classifies_panel_nested_inside_editgrid() -> None:
    """The DOSH shape: editgrid > panel > panel > columns."""
    from columns_logic import iter_columns_components

    form = [
        _editgrid(
            "grid",
            [_panel("outer", [_panel("inner", [_columns("nestedRow", [4] * 9)])])],
        )
    ]
    hits = list(iter_columns_components(form))
    assert len(hits) == 1
    assert hits[0].grid_context == "nested"
    assert hits[0].inside_grid is True


def test_walker_classifies_top_level_as_none() -> None:
    from columns_logic import iter_columns_components

    hits = list(iter_columns_components([_columns("row1", [6, 6])]))
    assert hits[0].grid_context == "none"
    assert hits[0].inside_grid is False


def test_walker_classifies_datagrid_like_editgrid() -> None:
    from columns_logic import iter_columns_components

    form = [
        {
            "key": "dg",
            "type": "datagrid",
            "components": [
                _columns("directRow", [6, 6]),
                _panel("p", [_columns("nestedRow", [6, 6])]),
            ],
        }
    ]
    by_key = {
        h.component["key"]: h.grid_context
        for h in iter_columns_components(form)
    }
    assert by_key == {"directRow": "direct_child", "nestedRow": "nested"}


def test_walker_columns_inside_a_direct_child_columns_row_are_nested() -> None:
    """A columns row inside a COLUMN of a direct-child columns row renders
    inside a col-md div — the grid rule's `>` cannot reach it, so it is
    `nested`, not `direct_child`."""
    from columns_logic import iter_columns_components

    inner = _columns("innerRow", [6, 6])
    outer = {
        "key": "outerRow",
        "type": "columns",
        "columns": [{"width": 12, "components": [inner]}],
    }
    form = [_editgrid("grid", [outer])]
    by_key = {
        h.component["key"]: h.grid_context
        for h in iter_columns_components(form)
    }
    assert by_key == {"outerRow": "direct_child", "innerRow": "nested"}


def test_build_plan_reports_both_grid_classes_with_sums() -> None:
    """Inventory-readiness: both in-grid skip classes must carry a base_sum
    (the old single `inside_grid` skip reported base_sum None, which forced
    the DOSH inventory to re-derive sums from the raw schema by hand)."""
    from columns_logic import build_plan

    form = {
        "components": [
            _editgrid(
                "grid",
                [
                    _columns("directRow", [4, 4]),
                    _panel("p", [_columns("nestedRow", [4] * 9)]),
                ],
            )
        ]
    }
    rows = {r["key"]: r for r in build_plan(form)["plan"]}

    direct = rows["directRow"]
    assert direct["action"] == "skip"
    assert direct["reason"] == "grid_direct_child"
    assert direct["grid_context"] == "direct_child"
    assert direct["base_sum"] == 8

    nested = rows["nestedRow"]
    assert nested["action"] == "skip"
    assert nested["reason"] == "inside_grid_nested"
    assert nested["grid_context"] == "nested"
    assert nested["base_sum"] == 36


def test_build_plan_never_pads_any_in_grid_row_yet() -> None:
    """SCAN-half freeze (TOBE-18037 acceptance 4): even a plainly under-12
    nested row stays `skip` — pad-applying an in-grid row waits for the
    apply half (TOBE-18041) and its canary."""
    from columns_logic import build_plan

    form = {
        "components": [
            _editgrid("grid", [_panel("p", [_columns("under12", [4, 4])])])
        ]
    }
    (row,) = build_plan(form)["plan"]
    assert row["action"] == "skip"
    assert row["reason"] == "inside_grid_nested"
    assert row["new_columns"] is None


def test_analyze_legacy_inside_grid_kwarg_unchanged() -> None:
    """The pad APPLY re-verifies live rows via `analyze(inside_grid=...)`.
    That legacy path must keep returning the historic reason so the apply
    module needs no change in this ticket."""
    from columns_logic import analyze_columns_component

    verdict = analyze_columns_component(_columns("row1", [4, 4]), inside_grid=True)
    assert verdict.action == "skip"
    assert verdict.reason == "inside_grid"
