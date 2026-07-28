"""Tests for the under-12 columns "apply" OPERATIONS module (TOBE-18005).

Spec: transform a ``build_plan`` output (from ``columns_logic``) plus a
freshly-fetched live form's component list into the ``form_patch`` SET
operations a skill session would send. Pure, read-only LOGIC — no writes, no
MCP tool.

Invariants exercised here:
  - ``plan_to_operations`` re-verifies EVERY actionable row against the LIVE
    component right before emitting an operation (last-write-wins safety):
    the emitted ``columns`` always come from the live re-derivation, never
    from the stale plan.
  - A live row that a designer already normalized / completed / pushed
    over 12 since the plan was built is SKIPPED, never blindly applied.
  - A live row whose verdict action no longer matches the plan row's action
    (append became resize, etc.) is skipped as ``layout_changed``.
  - A plan row whose path no longer resolves live is skipped as
    ``row_not_found``.
  - A plan/applied row whose path resolves to MORE THAN ONE live component
    (duplicate paths, e.g. two sibling panels each keyed the same containing
    a columns component keyed the same) is skipped as ``duplicate_path`` in
    both directions — never resolved to an arbitrary first match, which
    would emit a colliding op and silently leave the real target untouched.
  - A content edit that keeps widths intact (a field added into an existing
    column) survives into the emitted op — because the op is built from the
    LIVE component's columns, not the plan's.
  - ``revert_operations`` only restores a row when the live ``columns``
    still deep-equal exactly what ``plan_to_operations`` wrote (pristine);
    otherwise it skips as ``modified_since_apply``. Never a blind restore.
  - Neither function mutates its inputs.
  - Both functions fail loud with ``ValueError`` when ``live_components`` is
    not a list (e.g. a caller passes the whole form dict instead of
    ``form["components"]``).
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

from columns_logic import build_plan

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MODULE_PATH = SCRIPTS_DIR / "columns_apply.py"

# Sibling flat modules that ship with this skill. Importing one of these from
# another is intra-skill, not a third-party dependency.
_LOCAL_MODULES = {
    "columns_logic",
    "columns_split",
    "columns_apply",
    "columns_split_apply",
}


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------
def _col(width: int, *, key: str | None = None, size: str = "md") -> dict[str, Any]:
    return {
        "size": size,
        "width": width,
        "offset": 0,
        "push": 0,
        "pull": 0,
        "components": (
            [{"key": key, "type": "textfield", "label": key}] if key else []
        ),
    }


def _columns_component(
    key: str, widths: list[int], keys: list[str] | None = None
) -> dict[str, Any]:
    keys = keys or [f"{key}_f{i}" for i in range(len(widths))]
    return {
        "key": key,
        "type": "columns",
        # `keys` is built from `len(widths)` just above, so the two are equal
        # by construction; plain zip() keeps this helper runnable on the 3.9
        # floor the bundled scripts support.
        "columns": [_col(w, key=k) for w, k in zip(widths, keys)],
    }


def _form(components: list[dict[str, Any]]) -> dict[str, Any]:
    return {"components": components}


# ---------------------------------------------------------------------------
# stdlib-only invariant
# ---------------------------------------------------------------------------
def test_columns_apply_is_stdlib_only() -> None:
    assert MODULE_PATH.is_file(), f"columns_apply.py not found at {MODULE_PATH}"
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
            if node.level:
                continue
            top = (node.module or "").split(".")[0]
            if node.module and top not in {m.split(".")[0] for m in stdlib_ok}:
                if top in _LOCAL_MODULES:
                    continue
                offenders.append(node.module)
    assert not offenders, f"columns_apply must be stdlib-only; found {offenders}"


# ---------------------------------------------------------------------------
# intra-skill import discipline
# ---------------------------------------------------------------------------
def test_columns_apply_module_only_imports_columns_logic_intra_package() -> None:
    """columns_apply may only import ``columns_logic`` from its siblings (no
    BPAClient / other tools imports) — keeps it a pure, dependency-free
    transform, matching columns_split's constraint."""
    assert MODULE_PATH.is_file(), f"columns_apply.py not found at {MODULE_PATH}"
    with open(MODULE_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in _LOCAL_MODULES:
                assert node.module.endswith("columns_logic"), (
                    f"columns_apply must only import columns_logic intra-skill; "
                    f"found {node.module}"
                )


# ---------------------------------------------------------------------------
# plan_to_operations: happy path — under-12 3+3 row
# ---------------------------------------------------------------------------
def test_plan_to_operations_emits_set_op_for_under_12_row() -> None:
    from columns_apply import plan_to_operations

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]

    result = plan_to_operations(plan, live)

    assert result["skipped"] == []
    assert len(result["operations"]) == 1
    op = result["operations"][0]
    assert op["op"] == "set"
    assert op["key"] == "row1"
    columns = op["properties"]["columns"]
    widths = [c["width"] for c in columns]
    assert widths == [3, 3, 6]
    assert columns[2]["components"] == []

    assert len(result["applied_rows"]) == 1
    applied = result["applied_rows"][0]
    assert applied["path"] == "row1"
    assert applied["key"] == "row1"
    assert applied["before_columns"] == [
        {
            "size": "md",
            "width": 3,
            "offset": 0,
            "push": 0,
            "pull": 0,
            "components": [{"key": "row1_f0", "type": "textfield", "label": "row1_f0"}],
        },
        {
            "size": "md",
            "width": 3,
            "offset": 0,
            "push": 0,
            "pull": 0,
            "components": [{"key": "row1_f1", "type": "textfield", "label": "row1_f1"}],
        },
    ]
    assert applied["new_columns"] == columns


# ---------------------------------------------------------------------------
# live re-verification: widths changed since plan -> op reflects LIVE, not
# the stale plan
# ---------------------------------------------------------------------------
def test_plan_to_operations_uses_live_widths_not_stale_plan() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]

    # Live form has since changed: 3+3 -> 2+3 (a designer resized a column).
    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"][0]["width"] = 2

    result = plan_to_operations(plan, mutated_live)

    assert result["skipped"] == []
    assert len(result["operations"]) == 1
    op = result["operations"][0]
    widths = [c["width"] for c in op["properties"]["columns"]]
    # Must reflect the LIVE 2+3 -> [2,3,7], NOT the stale plan's [3,3,6].
    assert widths == [2, 3, 7]


# ---------------------------------------------------------------------------
# content edit keeping widths: extra field in a column survives into the op
# ---------------------------------------------------------------------------
def test_plan_to_operations_survives_content_edit_that_keeps_widths() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]

    mutated_live = deepcopy(original_live)
    # A designer added a second field into the first column; widths unchanged.
    mutated_live[0]["columns"][0]["components"].append(
        {"key": "extra_field", "type": "textfield", "label": "Extra"}
    )

    result = plan_to_operations(plan, mutated_live)

    assert result["skipped"] == []
    assert len(result["operations"]) == 1
    op = result["operations"][0]
    columns = op["properties"]["columns"]
    widths = [c["width"] for c in columns]
    assert widths == [3, 3, 6]
    first_col_keys = [c["key"] for c in columns[0]["components"]]
    assert "extra_field" in first_col_keys
    assert "row1_f0" in first_col_keys


# ---------------------------------------------------------------------------
# already_normalized: live row was already padded since the plan
# ---------------------------------------------------------------------------
def test_plan_to_operations_skips_already_normalized_live_row() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]

    # Live form already normalized (e.g. a previous run applied it, or a
    # designer hand-padded it) to exactly the append target.
    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"].append(
        {"size": "md", "width": 6, "offset": 0, "push": 0, "pull": 0, "components": []}
    )

    result = plan_to_operations(plan, mutated_live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["path"] == "row1"
    assert result["skipped"][0]["reason"] == "already_normalized"


# ---------------------------------------------------------------------------
# layout_changed / over_12: live row became over-12 since the plan
# ---------------------------------------------------------------------------
def test_plan_to_operations_skips_when_live_row_went_over_12() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]

    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"][0]["width"] = 10  # 10+3 = 13 > 12

    result = plan_to_operations(plan, mutated_live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert len(result["skipped"]) == 1
    skip = result["skipped"][0]
    assert skip["path"] == "row1"
    assert skip["reason"] in ("layout_changed", "over_12")


# ---------------------------------------------------------------------------
# row_not_found: plan path absent from the live tree
# ---------------------------------------------------------------------------
def test_plan_to_operations_skips_row_not_found_when_path_absent_live() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]

    # Live form no longer has the row at all (deleted).
    result = plan_to_operations(plan, [])

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0] == {"path": "row1", "reason": "row_not_found"}


# ---------------------------------------------------------------------------
# skip rows in the plan (action == "skip") are ignored, not re-processed
# ---------------------------------------------------------------------------
def test_plan_to_operations_ignores_skip_rows_in_plan() -> None:
    from columns_apply import plan_to_operations

    # already sums to 12 -> plan action is "skip"
    live = [_columns_component("row1", [6, 6])]
    plan = build_plan(_form(live))["plan"]
    assert plan[0]["action"] == "skip"

    result = plan_to_operations(plan, live)
    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == []


# ---------------------------------------------------------------------------
# input-not-mutated: plan_to_operations
# ---------------------------------------------------------------------------
def test_plan_to_operations_does_not_mutate_inputs() -> None:
    from columns_apply import plan_to_operations

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    live_copy = deepcopy(live)
    plan_copy = deepcopy(plan)

    result = plan_to_operations(plan, live)
    assert live == live_copy
    assert plan == plan_copy

    # Mutating the returned op's columns must not affect the live tree.
    result["operations"][0]["properties"]["columns"][0]["width"] = 999
    assert live[0]["columns"][0]["width"] == 3


# ---------------------------------------------------------------------------
# revert_operations: pristine restore
# ---------------------------------------------------------------------------
def test_revert_operations_restores_pristine_row() -> None:
    from columns_apply import (
        plan_to_operations,
        revert_operations,
    )

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    applied = plan_to_operations(plan, live)
    applied_rows = applied["applied_rows"]

    # Live form now carries exactly what apply wrote.
    post_apply_live = deepcopy(live)
    post_apply_live[0]["columns"] = deepcopy(applied_rows[0]["new_columns"])

    revert = revert_operations(applied_rows, post_apply_live)

    assert revert["skipped"] == []
    assert len(revert["operations"]) == 1
    op = revert["operations"][0]
    assert op["op"] == "set"
    assert op["key"] == "row1"
    assert op["properties"]["columns"] == applied_rows[0]["before_columns"]


# ---------------------------------------------------------------------------
# revert_operations: touched since apply -> skip, never a blind restore
# ---------------------------------------------------------------------------
def test_revert_operations_skips_row_touched_since_apply() -> None:
    from columns_apply import (
        plan_to_operations,
        revert_operations,
    )

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    applied = plan_to_operations(plan, live)
    applied_rows = applied["applied_rows"]

    post_apply_live = deepcopy(live)
    post_apply_live[0]["columns"] = deepcopy(applied_rows[0]["new_columns"])
    # A designer added a field into the filler column since apply.
    post_apply_live[0]["columns"][2]["components"].append(
        {"key": "new_field", "type": "textfield", "label": "New"}
    )

    revert = revert_operations(applied_rows, post_apply_live)

    assert revert["operations"] == []
    assert len(revert["skipped"]) == 1
    assert revert["skipped"][0]["path"] == "row1"
    assert revert["skipped"][0]["reason"] == "modified_since_apply"


def test_revert_operations_skips_row_not_found() -> None:
    from columns_apply import (
        plan_to_operations,
        revert_operations,
    )

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    applied = plan_to_operations(plan, live)
    applied_rows = applied["applied_rows"]

    revert = revert_operations(applied_rows, [])

    assert revert["operations"] == []
    assert len(revert["skipped"]) == 1
    assert revert["skipped"][0] == {"path": "row1", "reason": "row_not_found"}


# ---------------------------------------------------------------------------
# duplicate_path: two live components resolve to the same walker path ->
# BOTH plan rows are skipped, never resolved to an arbitrary first match.
# ---------------------------------------------------------------------------
def _duplicate_path_live() -> list[dict[str, Any]]:
    # Two sibling panels, both keyed "p", each containing a columns
    # component keyed "c" -> both walker paths are "p/c".
    return [
        {
            "key": "p",
            "type": "panel",
            "components": [_columns_component("c", [3, 3])],
        },
        {
            "key": "p",
            "type": "panel",
            "components": [_columns_component("c", [4, 4])],
        },
    ]


def test_plan_to_operations_skips_both_rows_on_duplicate_path() -> None:
    from columns_apply import plan_to_operations

    live = _duplicate_path_live()
    plan = build_plan(_form(live))["plan"]
    assert len(plan) == 2
    assert {row["path"] for row in plan} == {"p/c"}

    result = plan_to_operations(plan, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert len(result["skipped"]) == 2
    assert result["skipped"] == [
        {"path": "p/c", "reason": "duplicate_path"},
        {"path": "p/c", "reason": "duplicate_path"},
    ]


def test_revert_operations_skips_both_rows_on_duplicate_path() -> None:
    from columns_apply import revert_operations

    live = _duplicate_path_live()
    # Simulate two previously-applied rows that (pre-fix) both resolved to
    # the same live path -- revert must independently detect the ambiguity
    # and refuse to guess which live component each row addresses.
    applied_rows = [
        {
            "path": "p/c",
            "key": "c",
            "before_columns": [],
            "new_columns": live[0]["components"][0]["columns"],
        },
        {
            "path": "p/c",
            "key": "c",
            "before_columns": [],
            "new_columns": live[1]["components"][0]["columns"],
        },
    ]

    result = revert_operations(applied_rows, live)

    assert result["operations"] == []
    assert len(result["skipped"]) == 2
    assert result["skipped"] == [
        {"path": "p/c", "reason": "duplicate_path"},
        {"path": "p/c", "reason": "duplicate_path"},
    ]


# ---------------------------------------------------------------------------
# fail loud on bad shape: live_components must be a list, not e.g. a whole
# form dict.
# ---------------------------------------------------------------------------
def test_plan_to_operations_raises_on_non_list_live_components() -> None:
    from columns_apply import plan_to_operations

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]

    try:
        plan_to_operations(plan, _form(live))  # whole form dict, not the list
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for non-list live_components")


def test_revert_operations_raises_on_non_list_live_components() -> None:
    from columns_apply import (
        plan_to_operations,
        revert_operations,
    )

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    applied_rows = plan_to_operations(plan, live)["applied_rows"]

    try:
        revert_operations(applied_rows, _form(live))  # whole form dict
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for non-list live_components")


# ---------------------------------------------------------------------------
# input-not-mutated: revert_operations
# ---------------------------------------------------------------------------
def test_revert_operations_does_not_mutate_inputs() -> None:
    from columns_apply import (
        plan_to_operations,
        revert_operations,
    )

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]
    applied = plan_to_operations(plan, live)
    applied_rows = applied["applied_rows"]

    post_apply_live = deepcopy(live)
    post_apply_live[0]["columns"] = deepcopy(applied_rows[0]["new_columns"])

    applied_rows_copy = deepcopy(applied_rows)
    live_copy = deepcopy(post_apply_live)

    result = revert_operations(applied_rows, post_apply_live)
    assert applied_rows == applied_rows_copy
    assert post_apply_live == live_copy

    result["operations"][0]["properties"]["columns"][0]["width"] = 999
    assert post_apply_live[0]["columns"][0]["width"] == 3


# ---------------------------------------------------------------------------
# duplicate_key: two columns components at DISTINCT paths share a key.
# form_patch addresses by key, so both rows must skip duplicate_key (never
# emit colliding same-key ops) — the key-addressed analogue of duplicate_path.
# ---------------------------------------------------------------------------
def _duplicate_key_live() -> list[dict[str, Any]]:
    # Two DIFFERENTLY-keyed panels, each containing a columns component keyed
    # "c" -> distinct paths "panelA/c" and "panelB/c" but the SAME key "c".
    return [
        {
            "key": "panelA",
            "type": "panel",
            "components": [_columns_component("c", [3, 3])],
        },
        {
            "key": "panelB",
            "type": "panel",
            "components": [_columns_component("c", [4, 4])],
        },
    ]


def test_plan_to_operations_skips_rows_with_duplicate_live_key() -> None:
    from columns_apply import plan_to_operations

    live = _duplicate_key_live()
    plan = build_plan(_form(live))["plan"]
    # Distinct paths -> the duplicate_path guard does NOT fire.
    assert {row["path"] for row in plan} == {"panelA/c", "panelB/c"}

    result = plan_to_operations(plan, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert sorted(s["path"] for s in result["skipped"]) == ["panelA/c", "panelB/c"]
    assert {s["reason"] for s in result["skipped"]} == {"duplicate_key"}


def test_revert_operations_skips_rows_with_duplicate_live_key() -> None:
    from columns_apply import revert_operations

    live = _duplicate_key_live()
    # Two previously-applied rows at distinct paths that share the live key
    # "c" -> revert must independently refuse to guess which "c" each targets.
    applied_rows = [
        {
            "path": "panelA/c",
            "key": "c",
            "before_columns": [],
            "new_columns": live[0]["components"][0]["columns"],
        },
        {
            "path": "panelB/c",
            "key": "c",
            "before_columns": [],
            "new_columns": live[1]["components"][0]["columns"],
        },
    ]

    result = revert_operations(applied_rows, live)

    assert result["operations"] == []
    assert sorted(s["path"] for s in result["skipped"]) == ["panelA/c", "panelB/c"]
    assert {s["reason"] for s in result["skipped"]} == {"duplicate_key"}


# ---------------------------------------------------------------------------
# layout_changed: live verdict action is actionable but differs from the plan
# row's action (plan "append"; live gained a trailing empty -> "resize").
# ---------------------------------------------------------------------------
def test_plan_to_operations_skips_layout_changed_when_live_action_differs() -> None:
    from columns_apply import plan_to_operations

    original_live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(original_live))["plan"]
    assert plan[0]["action"] == "append"

    # A designer appended a trailing EMPTY column since the plan was built, so
    # the live analyzer now resizes that empty into the filler -> action
    # "resize", which no longer matches the plan's "append".
    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"].append(
        {"size": "md", "width": 2, "offset": 0, "push": 0, "pull": 0, "components": []}
    )

    result = plan_to_operations(plan, mutated_live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [{"path": "row1", "reason": "layout_changed"}]


# ---------------------------------------------------------------------------
# malformed live width folds into skipped (unlike build_plan, which RAISES) —
# one anomalous live row must not abort an otherwise-valid batch apply.
# ---------------------------------------------------------------------------
def test_plan_to_operations_folds_null_width_into_skipped_not_raise() -> None:
    from columns_apply import plan_to_operations

    live = [_columns_component("row1", [3, 3]), _columns_component("row2", [4, 4])]
    plan = build_plan(_form(live))["plan"]

    # Corrupt row1's live width to None AFTER building the plan from valid live.
    mutated_live = deepcopy(live)
    mutated_live[0]["columns"][0]["width"] = None

    result = plan_to_operations(plan, mutated_live)

    # row1 folds into skipped (does NOT raise); the valid row2 still applies.
    assert {"path": "row1", "reason": "null_width"} in result["skipped"]
    assert len(result["operations"]) == 1
    assert result["operations"][0]["key"] == "row2"


def test_plan_to_operations_folds_invalid_width_into_skipped_not_raise() -> None:
    from columns_apply import plan_to_operations

    live = [_columns_component("row1", [3, 3])]
    plan = build_plan(_form(live))["plan"]

    mutated_live = deepcopy(live)
    mutated_live[0]["columns"][0]["width"] = 13  # out of 1..12

    result = plan_to_operations(plan, mutated_live)

    assert result["operations"] == []
    assert result["skipped"] == [{"path": "row1", "reason": "invalid_width"}]
