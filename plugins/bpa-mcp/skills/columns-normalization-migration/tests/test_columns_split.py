"""Tests for the over-12 columns "split" DETECTION module (TOBE-18009).

Spec: identify columns rows whose widths sum > 12 and compute the proposed
split plan (greedy 12-boundary grouping, split-then-pad remainder,
determinant-carry intent, single-[12] flagged for editor-tolerance review).

Scan-only: no apply, no form_patch, no MCP tool registration (structural now —
the module ships with this skill, not with the MCP package). This module is
SEPARATE and ADDITIVE — it must never change
``columns_logic.analyze_columns_component`` behaviour (still skip/over_12 for
these rows), covered by test_columns_split_does_not_alter_columns_logic()
below.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MODULE_PATH = SCRIPTS_DIR / "columns_split.py"

# Sibling flat modules that ship with this skill. Importing one of these from
# another is intra-skill, not a third-party dependency.
_LOCAL_MODULES = {
    "columns_logic",
    "columns_split",
    "columns_apply",
    "columns_split_apply",
}


def _col(width: int, *, key: str | None = None, size: str = "md") -> dict[str, Any]:
    col: dict[str, Any] = {
        "size": size,
        "width": width,
        "offset": 0,
        "push": 0,
        "pull": 0,
        "components": (
            [{"key": key or f"f{width}", "type": "textfield", "label": "x"}]
        ),
    }
    return col


def _columns_component(
    key: str, widths: list[int], *, custom_class: str = ""
) -> dict[str, Any]:
    comp: dict[str, Any] = {
        "key": key,
        "type": "columns",
        "columns": [_col(w) for w in widths],
    }
    if custom_class:
        comp["customClass"] = custom_class
    return comp


def _assert_all_containers_sum_to_twelve(plan: dict[str, Any]) -> None:
    """Invariant the padding logic must uphold: EVERY container in a split
    plan sums to exactly 12, not just the trailing one."""
    for container in plan["containers"]:
        assert sum(container["widths"]) == 12
        assert sum(c["width"] for c in container["columns"]) == 12


# ---------------------------------------------------------------------------
# stdlib-only invariant (guards the module docstring's STDLIB-ONLY claim)
# ---------------------------------------------------------------------------
def test_columns_split_is_stdlib_only() -> None:
    """The module must not import any third-party package."""
    assert MODULE_PATH.is_file(), f"columns_split.py not found at {MODULE_PATH}"
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
    assert not offenders, f"columns_split must be stdlib-only; found {offenders}"


# ---------------------------------------------------------------------------
# intra-skill import discipline (guards "no other tools / BPAClient imports")
# ---------------------------------------------------------------------------
def test_columns_split_only_imports_columns_logic_intra_package() -> None:
    """columns_split may only import ``columns_logic`` from its siblings (no
    BPAClient / other tools imports) — keeps it a pure, dependency-free
    transform, matching columns_apply's constraint."""
    assert MODULE_PATH.is_file(), f"columns_split.py not found at {MODULE_PATH}"
    with open(MODULE_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in _LOCAL_MODULES:
                assert node.module.endswith("columns_logic"), (
                    f"columns_split must only import columns_logic intra-skill; "
                    f"found {node.module}"
                )


# ---------------------------------------------------------------------------
# Erick's 9x4 case: three clean [4,4,4] containers
# ---------------------------------------------------------------------------
def test_plan_split_nine_width_four_yields_three_clean_containers() -> None:
    from columns_split import plan_split

    comp = _columns_component("c", [4] * 9)
    plan = plan_split(comp)
    assert plan is not None
    assert plan["action"] == "split"
    assert plan["original_key"] == "c"
    assert plan["base_widths"] == [4] * 9
    assert plan["determinant_carry"] == "all"
    assert "needs_review" not in plan

    containers = plan["containers"]
    assert len(containers) == 3
    for i, container in enumerate(containers, start=1):
        assert container["key"] == f"c_split{i}"
        assert container["widths"] == [4, 4, 4]
        assert container["padded"] is False
        assert sum(c["width"] for c in container["columns"]) == 12
    _assert_all_containers_sum_to_twelve(plan)


# ---------------------------------------------------------------------------
# 5x4 (sum 20): [4,4,4] + [4,4,pad4]
# ---------------------------------------------------------------------------
def test_plan_split_five_width_four_pads_trailing_group() -> None:
    from columns_split import plan_split

    comp = _columns_component("c", [4, 4, 4, 4, 4])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 2

    first, second = containers
    assert first["widths"] == [4, 4, 4]
    assert first["padded"] is False

    assert second["widths"] == [4, 4, 4]
    assert second["padded"] is True
    filler = second["columns"][-1]
    assert filler["width"] == 4
    assert filler["components"] == []
    assert filler["offset"] == 0
    assert filler["push"] == 0
    assert filler["pull"] == 0
    assert "hideIfEmpty" not in filler
    _assert_all_containers_sum_to_twelve(plan)


# ---------------------------------------------------------------------------
# 6+6+3 (sum 15): [6,6] + [3,pad9]
# ---------------------------------------------------------------------------
def test_plan_split_six_six_three_closes_at_twelve_then_pads_remainder() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [6, 6, 3])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 2

    first, second = containers
    assert first["widths"] == [6, 6]
    assert first["padded"] is False

    assert second["widths"] == [3, 9]
    assert second["padded"] is True
    filler = second["columns"][-1]
    assert filler["width"] == 9
    assert filler["components"] == []
    _assert_all_containers_sum_to_twelve(plan)


# ---------------------------------------------------------------------------
# Width-12 rows: plan_split narrows the skip to only rows the TOBE-18019
# CSS rule actually handles (a width-12 column whose non-12 remainder
# itself sums <= 12). A width-12 row whose non-12 remainder ITSELF
# overflows 12 is NOT handled by that CSS rule and must be surfaced as a
# "review" entry rather than silently dropped or auto-split.
# ---------------------------------------------------------------------------
def test_plan_split_all_twelves_returns_none() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [12, 12])
    assert plan_split(comp) is None


def test_plan_split_all_twelves_triple_returns_none() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [12, 12, 12])
    assert plan_split(comp) is None


def test_plan_split_mixed_row_with_a_twelve_and_small_remainder_returns_none() -> None:
    """[12,3,3] (sum 18, over 12) contains a width-12 column, and its non-12
    remainder (3+3=6) is <= 12, so it is fully handled by the TOBE-18019 CSS
    rule and plan_split defers to it (returns None) rather than splitting."""
    from columns_split import plan_split

    comp = _columns_component("row", [12, 3, 3])
    assert plan_split(comp) is None


def test_plan_split_lone_twelve_returns_none_via_sum_check() -> None:
    """A lone [12] column (base_sum 12, not > 12) already returns None via
    the existing sum check, unrelated to the width-12 skip."""
    from columns_split import plan_split

    comp = _columns_component("row", [12])
    assert plan_split(comp) is None


# ---------------------------------------------------------------------------
# autopilot BLOCKING finding (PR #441): a width-12 row whose non-12
# remainder ITSELF overflows 12 is NOT fixed by the TOBE-18019 CSS rule (the
# 12 breaks to its own line, but the ragged over-12 remainder still
# overflows). plan_split must surface this as a "review" entry, NOT return
# None (silently dropping real overflow) and NOT emit a "split" plan
# (auto-splitting a row with a width-12 column risks the defaultsDeep
# back-fill trap / has an open determinant-carry question).
# ---------------------------------------------------------------------------
def test_plan_split_mixed_row_with_overflowing_remainder_returns_review() -> None:
    """[12,8,8] (sum 28, non-12 remainder 8+8=16 > 12): the CSS rule breaks
    the 12 to its own line but the [8,8] pair still overflows. This is the
    autopilot's BLOCKING case: must be a review flag, not None, not a split."""
    from columns_split import plan_split

    comp = _columns_component("row", [12, 8, 8])
    plan = plan_split(comp)
    assert plan is not None
    assert plan["action"] == "review"
    assert plan["reason"] == "mixed_width12_remainder_over12"
    assert plan["original_key"] == "row"
    assert plan["base_widths"] == [12, 8, 8]
    assert plan["determinant_carry"] == "all"
    assert "containers" not in plan


def test_plan_split_two_twelves_with_overflowing_remainder_returns_review() -> None:
    """[12,12,8,8] (sum 40, non-12 remainder 8+8=16 > 12): two width-12
    columns still leave an overflowing [8,8] remainder — same review flag."""
    from columns_split import plan_split

    comp = _columns_component("row", [12, 12, 8, 8])
    plan = plan_split(comp)
    assert plan is not None
    assert plan["action"] == "review"
    assert plan["reason"] == "mixed_width12_remainder_over12"
    assert plan["base_widths"] == [12, 12, 8, 8]
    assert "containers" not in plan


# ---------------------------------------------------------------------------
# FIX 1 (blocking): pad EVERY group summing below 12, not just the trailing
# one. Greedy grouping can close a MIDDLE group below 12 when a wide column
# forces the next column into a new group.
# ---------------------------------------------------------------------------
def test_plan_split_pads_every_group_not_just_trailing_eight_eight_eight() -> None:
    """[8,8,8] (sum 24) greedily groups as [8],[8],[8] (each column alone
    forces a new group because 8+8>12) — ALL THREE must be padded to
    [8,pad4], not just the last one."""
    from columns_split import plan_split

    comp = _columns_component("c", [8, 8, 8])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 3
    for i, container in enumerate(containers, start=1):
        assert container["key"] == f"c_split{i}"
        assert container["widths"] == [8, 4]
        assert container["padded"] is True
        filler = container["columns"][-1]
        assert filler["width"] == 4
        assert filler["components"] == []
        assert filler["offset"] == 0
        assert filler["push"] == 0
        assert filler["pull"] == 0
        assert "hideIfEmpty" not in filler
    _assert_all_containers_sum_to_twelve(plan)


def test_plan_split_pads_middle_group_eight_eight_three() -> None:
    """[8,8,3] (sum 19) groups as [8],[8,3] — the first (middle-in-effect)
    group [8] sums to 8 and must be padded, in addition to the trailing
    [8,3] group."""
    from columns_split import plan_split

    comp = _columns_component("c", [8, 8, 3])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 2

    first, second = containers
    assert first["widths"] == [8, 4]
    assert first["padded"] is True

    assert second["widths"] == [8, 3, 1]
    assert second["padded"] is True
    _assert_all_containers_sum_to_twelve(plan)


def test_plan_split_six_threes_splits_and_pads_trailing_group() -> None:
    """[3,3,3,3,3,3] (sum 18) groups as [3,3,3,3] (sum 12) + [3,3] (sum 6,
    padded to [3,3,pad6])."""
    from columns_split import plan_split

    comp = _columns_component("c", [3, 3, 3, 3, 3, 3])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 2

    first, second = containers
    assert first["widths"] == [3, 3, 3, 3]
    assert first["padded"] is False

    assert second["widths"] == [3, 3, 6]
    assert second["padded"] is True
    filler = second["columns"][-1]
    assert filler["width"] == 6
    assert filler["components"] == []
    _assert_all_containers_sum_to_twelve(plan)


def test_plan_split_pads_both_groups_ten_ten() -> None:
    """[10,10] (sum 20) groups as [10],[10] — both groups sum to 10 and
    must each be padded with an empty width-2 filler."""
    from columns_split import plan_split

    comp = _columns_component("c", [10, 10])
    plan = plan_split(comp)
    assert plan is not None
    containers = plan["containers"]
    assert len(containers) == 2
    for container in containers:
        assert container["widths"] == [10, 2]
        assert container["padded"] is True
        filler = container["columns"][-1]
        assert filler["width"] == 2
        assert filler["components"] == []
    _assert_all_containers_sum_to_twelve(plan)


# ---------------------------------------------------------------------------
# never-emit-under-2-columns invariant (defaultsDeep back-fill trap guard)
# ---------------------------------------------------------------------------
def test_plan_split_never_emits_a_container_with_fewer_than_two_columns() -> None:
    """Direct invariant check across a representative set of splittable
    rows (no width-12 column, genuinely over 12): every emitted container
    must have >= 2 columns."""
    from columns_split import plan_split

    rows: list[list[int]] = [
        [4] * 9,
        [4, 4, 4, 4, 4],
        [6, 6, 3],
        [8, 8, 8],
        [8, 8, 3],
        [10, 10],
        [3, 3, 3, 3, 3, 3],
    ]
    for widths in rows:
        comp = _columns_component("c", widths)
        plan = plan_split(comp)
        assert plan is not None, f"expected a plan for widths={widths}"
        for container in plan["containers"]:
            assert len(container["columns"]) >= 2, (
                f"widths={widths}: container {container['key']} has fewer "
                f"than 2 columns: {container['columns']}"
            )


# ---------------------------------------------------------------------------
# FIX 2 (should-fix): non-string customClass must not crash.
# ---------------------------------------------------------------------------
def test_plan_split_non_string_custom_class_does_not_crash() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [8, 8])
    comp["customClass"] = ["x"]
    plan = plan_split(comp)
    assert plan is not None
    _assert_all_containers_sum_to_twelve(plan)


# ---------------------------------------------------------------------------
# FIX 3 (should-fix): empty top-level components falls back to formSchema.
# ---------------------------------------------------------------------------
def test_scan_form_for_splits_falls_back_to_formschema_when_components_empty() -> None:
    from columns_split import scan_form_for_splits

    form = {
        "components": [],
        "formSchema": {"components": [_columns_component("row", [8, 8])]},
    }
    results = scan_form_for_splits(form)
    assert len(results) == 1
    assert results[0]["original_key"] == "row"


# ---------------------------------------------------------------------------
# under-12 / exactly-12: plan_split returns None
# ---------------------------------------------------------------------------
def test_plan_split_returns_none_for_under_twelve() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [3, 3])
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_exactly_twelve() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [6, 6])
    assert plan_split(comp) is None


# ---------------------------------------------------------------------------
# skip conditions: keyless, adjust-columns, excluded key, null/invalid width
# ---------------------------------------------------------------------------
def test_plan_split_returns_none_for_keyless_component() -> None:
    from columns_split import plan_split

    comp = _columns_component("", [8, 8])
    comp["key"] = ""
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_adjust_columns_custom_class() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [8, 8], custom_class="adjust-columns")
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_excluded_key() -> None:
    from columns_split import plan_split

    comp = _columns_component("my-applications-pagination", [8, 8])
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_null_width() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [8, 8])
    comp["columns"][0]["width"] = None
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_width_thirteen() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [13, 8])
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_no_columns() -> None:
    from columns_split import plan_split

    comp = {"key": "row", "type": "columns", "columns": []}
    assert plan_split(comp) is None


def test_plan_split_returns_none_for_bool_width() -> None:
    from columns_split import plan_split

    comp = _columns_component("row", [8, 8])
    comp["columns"][0]["width"] = True
    assert plan_split(comp) is None


# ---------------------------------------------------------------------------
# input not mutated
# ---------------------------------------------------------------------------
def test_plan_split_does_not_mutate_input() -> None:
    from columns_split import plan_split

    comp = _columns_component("c", [4] * 9)
    original = deepcopy(comp)
    plan_split(comp)
    assert comp == original


# ---------------------------------------------------------------------------
# does not alter columns_logic behaviour
# ---------------------------------------------------------------------------
def test_columns_split_does_not_alter_columns_logic_behaviour() -> None:
    """This module is additive; the existing bot module must keep skipping
    over-12 rows with reason 'over_12' exactly as before."""
    from columns_logic import analyze_columns_component

    comp = _columns_component("c", [4] * 9)
    verdict = analyze_columns_component(comp)
    assert verdict.action == "skip"
    assert verdict.reason == "over_12"


# ---------------------------------------------------------------------------
# scan_form_for_splits: found (top-level/panel), skipped (inside editgrid)
# ---------------------------------------------------------------------------
def test_scan_form_for_splits_finds_nested_over_twelve_in_panel() -> None:
    from columns_split import scan_form_for_splits

    form = {
        "components": [
            {
                "key": "panel1",
                "type": "panel",
                "components": [_columns_component("nested", [8, 8])],
            }
        ]
    }
    results = scan_form_for_splits(form)
    assert len(results) == 1
    assert results[0]["original_key"] == "nested"
    assert "panel1" in results[0]["path"]


def test_scan_form_for_splits_surfaces_mixed_overflow_review_entry() -> None:
    """A [12,8,8] columns row must be SURFACED in scan output as a review
    entry (with its path and reason), not silently dropped — this proves
    scan_form_for_splits's `if plan is not None` filter includes review
    results, not just split plans."""
    from columns_split import scan_form_for_splits

    form = {
        "components": [
            {
                "key": "panel1",
                "type": "panel",
                "components": [_columns_component("overflow", [12, 8, 8])],
            }
        ]
    }
    results = scan_form_for_splits(form)
    assert len(results) == 1
    entry = results[0]
    assert entry["action"] == "review"
    assert entry["reason"] == "mixed_width12_remainder_over12"
    assert entry["original_key"] == "overflow"
    assert "panel1" in entry["path"]


def test_scan_form_for_splits_skips_over_twelve_inside_editgrid() -> None:
    from columns_split import scan_form_for_splits

    form = {
        "components": [
            {
                "key": "grid",
                "type": "editgrid",
                "components": [_columns_component("inGrid", [8, 8])],
            }
        ]
    }
    results = scan_form_for_splits(form)
    assert results == []


def test_scan_form_for_splits_handles_formschema_dict() -> None:
    from columns_split import scan_form_for_splits

    form = {"formSchema": {"components": [_columns_component("row", [8, 8])]}}
    results = scan_form_for_splits(form)
    assert len(results) == 1
    assert results[0]["original_key"] == "row"


def test_scan_form_for_splits_handles_formschema_string() -> None:
    from columns_split import scan_form_for_splits

    schema = {"components": [_columns_component("row", [8, 8])]}
    form = {"formSchema": json.dumps(schema)}
    results = scan_form_for_splits(form)
    assert len(results) == 1
    assert results[0]["original_key"] == "row"


def test_scan_form_for_splits_rejects_unexpected_shape() -> None:
    from columns_split import scan_form_for_splits

    with pytest.raises(ValueError):
        scan_form_for_splits({"not": "a form"})


# ---------------------------------------------------------------------------
# CLI roundtrip
# ---------------------------------------------------------------------------
_VALID_FORM = {"components": [_columns_component("c", [4] * 9)]}


def _run_cli(stdin_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def test_cli_valid_form_emits_split_list_and_exits_zero() -> None:
    proc = _run_cli(json.dumps(_VALID_FORM))
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert len(parsed[0]["containers"]) == 3


def test_cli_non_json_input_fails_loud() -> None:
    proc = _run_cli("this is not json {{{")
    assert proc.returncode != 0
    assert proc.stderr.strip()
    assert proc.stdout.strip() == "" or "error" in proc.stdout.lower()


def test_cli_unexpected_shape_fails_loud() -> None:
    proc = _run_cli(json.dumps({"not": "a form"}))
    assert proc.returncode != 0
    assert proc.stderr.strip()


def test_cli_main_callable_rejects_non_json() -> None:
    from columns_split import main

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        main(["--stdin"], stdin_text="not json")
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code not in (0, None)
