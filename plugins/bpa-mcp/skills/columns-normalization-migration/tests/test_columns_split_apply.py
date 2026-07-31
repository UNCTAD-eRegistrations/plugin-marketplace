"""Tests for the over-12 columns "split-APPLY" OPERATIONS module (TOBE-18009).

Spec: transform a ``columns_split.scan_form_for_splits`` split PLAN plus a
freshly-fetched live form's component list into the ``form_patch`` remove+add
operations a skill session would send to replace an over-12 columns
component with N 12-sum containers in its exact slot. Pure, read-only
LOGIC — no writes, no MCP tool.

Invariants exercised here:
  - ``plan_to_split_operations`` re-verifies EVERY row against the LIVE
    component right before emitting operations (last-write-wins safety): the
    emitted containers always come from re-running ``columns_split.plan_split``
    on the live component, never from the stale plan row.
  - A live row that no longer sums over 12 (or is otherwise no longer
    splittable) since the plan was built is skipped ``layout_changed``.
  - A plan row whose path no longer resolves live is skipped ``row_not_found``;
    a path resolving to more than one live component is skipped
    ``duplicate_path`` (both rows); a live key shared by more than one live
    columns component is skipped ``duplicate_key`` (both rows).
  - A BPA-managed behaviour (non-empty ``behaviourId``/``effectsIds``/
    ``determinantIds``) on the live original component NEVER skips the row:
    every row splits structurally regardless. Its ``applied_rows`` entry
    carries a populated ``determinant_replication`` descriptor
    (``source_key``/``target_keys``/``source_behaviour_id``/
    ``target_behaviour_ids``) the skill executes after the write ONLY when
    the live original component has a non-empty ``behaviourId`` (the clone
    source). A row managed only via ``determinantIds``/``effectsIds`` (no
    ``behaviourId``) has no clone source, so it splits with NO descriptor —
    ``determinant_replication: None`` — same as any non-managed row.
  - Inline visibility fields (``conditional``, ``customConditional``,
    ``logic``, ``hidden``) are copied verbatim onto EVERY new container.
  - Only form root / plain container / nested columns parents are supported;
    anything else (tabs, table, grid) is skipped ``unsupported_parent_context``.
  - A proposed container key colliding with any existing live key skips the
    row ``container_key_collision``.
  - ``revert_split_operations`` only restores a row when every one of its
    written containers still deep-equals what was written; otherwise it
    skips ``modified_since_apply``. Never a blind restore.
  - Neither function mutates its inputs.
  - Both functions fail loud with ``ValueError`` when ``live_components`` is
    not a list.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from columns_split import scan_form_for_splits

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MODULE_PATH = SCRIPTS_DIR / "columns_split_apply.py"

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


def _columns_component(key: str, widths: list[int], **extra: Any) -> dict[str, Any]:
    keys = [f"{key}_f{i}" for i in range(len(widths))]
    comp: dict[str, Any] = {
        "key": key,
        "type": "columns",
        # `keys` is built from `len(widths)` just above, so the two are equal
        # by construction; plain zip() keeps this helper runnable on the 3.9
        # floor the bundled scripts support.
        "columns": [_col(w, key=k) for w, k in zip(widths, keys)],
    }
    comp.update(extra)
    return comp


def _form(components: list[dict[str, Any]]) -> dict[str, Any]:
    return {"components": components}


def _plan_rows(live: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return scan_form_for_splits(_form(live))


# ---------------------------------------------------------------------------
# stdlib-only invariant
# ---------------------------------------------------------------------------
def test_columns_split_apply_is_stdlib_only() -> None:
    assert MODULE_PATH.is_file(), f"columns_split_apply.py not found at {MODULE_PATH}"
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
    assert not offenders, f"columns_split_apply must be stdlib-only; found {offenders}"


# ---------------------------------------------------------------------------
# intra-skill import discipline
# ---------------------------------------------------------------------------
def test_columns_split_apply_only_imports_columns_logic_and_columns_split() -> None:
    """columns_split_apply may only import ``columns_logic``/``columns_split``
    from its siblings (no BPAClient / other tools imports, and no import of the
    sibling ``columns_apply``)."""
    assert MODULE_PATH.is_file(), f"columns_split_apply.py not found at {MODULE_PATH}"
    with open(MODULE_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in _LOCAL_MODULES:
                assert node.module.endswith("columns_logic") or node.module.endswith(
                    "columns_split"
                ), (
                    f"columns_split_apply must only import columns_logic/"
                    f"columns_split intra-skill; found {node.module}"
                )


# ---------------------------------------------------------------------------
# happy path: ROOT parent, 9x4 -> 3 clean [4,4,4] containers
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_root_parent_emits_remove_and_three_adds() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    leading = {"key": "leadingField", "type": "textfield", "label": "Leading"}
    target = _columns_component("row1", [4] * 9)
    live = [leading, target]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1
    assert plan_rows[0]["path"] == "row1"

    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    assert len(result["operations"]) == 4  # 1 remove + 3 add
    remove_op, *add_ops = result["operations"]
    assert remove_op == {"op": "remove", "key": "row1"}
    assert len(add_ops) == 3

    for n, op in enumerate(add_ops):
        assert op["op"] == "add"
        assert "parent_key" not in op
        assert "column_index" not in op
        assert op["position"] == 1 + n  # base_index (1) + n
        component = op["component"]
        assert component["type"] == "columns"
        assert component["key"] == f"row1_split{n + 1}"
        widths = [c["width"] for c in component["columns"]]
        assert widths == [4, 4, 4]

    assert len(result["applied_rows"]) == 1
    applied = result["applied_rows"][0]
    assert applied["path"] == "row1"
    assert applied["original_key"] == "row1"
    assert applied["parent_key"] is None
    assert applied["column_index"] is None
    assert applied["position"] == 1
    assert applied["container_keys"] == ["row1_split1", "row1_split2", "row1_split3"]
    assert applied["original_component"] == target
    assert len(applied["written_containers"]) == 3
    # Non-managed row -> no behaviour replication descriptor.
    assert applied["determinant_replication"] is None


# ---------------------------------------------------------------------------
# happy path: PANEL parent
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_panel_parent_carries_parent_key() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    leading = {"key": "leadingField", "type": "textfield", "label": "Leading"}
    target = _columns_component("row1", [4] * 9)
    panel = {
        "key": "myPanel",
        "type": "panel",
        "components": [leading, target],
    }
    live = [panel]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    remove_op, *add_ops = result["operations"]
    assert remove_op == {"op": "remove", "key": "row1"}
    assert len(add_ops) == 3
    for n, op in enumerate(add_ops):
        assert op["parent_key"] == "myPanel"
        assert "column_index" not in op
        assert op["position"] == 1 + n

    applied = result["applied_rows"][0]
    assert applied["parent_key"] == "myPanel"
    assert applied["column_index"] is None
    assert applied["position"] == 1


# ---------------------------------------------------------------------------
# happy path: COLUMNS parent (nested inside another columns component)
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_columns_parent_carries_column_index() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    leading = {"key": "leadingField", "type": "textfield", "label": "Leading"}
    target = _columns_component("row1", [4] * 9)
    outer = {
        "key": "outer",
        "type": "columns",
        "columns": [
            {
                "size": "md",
                "width": 6,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [leading, target],
            },
            {
                "size": "md",
                "width": 6,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [],
            },
        ],
    }
    live = [outer]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1

    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    remove_op, *add_ops = result["operations"]
    assert remove_op == {"op": "remove", "key": "row1"}
    assert len(add_ops) == 3
    for n, op in enumerate(add_ops):
        assert op["parent_key"] == "outer"
        assert op["column_index"] == 0
        assert op["position"] == 1 + n

    applied = result["applied_rows"][0]
    assert applied["parent_key"] == "outer"
    assert applied["column_index"] == 0
    assert applied["position"] == 1


# ---------------------------------------------------------------------------
# Finding 1 (position drift): TWO distinct over-12 rows in the SAME
# sibling list must have the second row's adds offset by the first row's
# net length change (+2 for a 9x4 -> 3-container split), not land at its
# stale pre-batch position. Traced case from the reviewer: root
# [rowA(9x4), rowB(9x4)] must emit rowA adds at 0,1,2 and rowB adds at
# 3,4,5 (NOT 1,2,3). This test MUST fail against the pre-fix code, which
# computed every row's positions from the static pre-batch tree.
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_offsets_second_row_same_sibling_list_root() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    row_a = _columns_component("rowA", [4] * 9)  # -> 3 containers of [4,4,4]
    row_b = _columns_component("rowB", [4] * 9)  # -> 3 containers of [4,4,4]
    live = [row_a, row_b]

    plan_rows = _plan_rows(live)
    assert {row["path"] for row in plan_rows} == {"rowA", "rowB"}

    result = plan_to_split_operations(plan_rows, live)
    assert result["skipped"] == []

    expected_ops = [
        {"op": "remove", "key": "rowA"},
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowA_split1",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 0,
        },
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowA_split2",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 1,
        },
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowA_split3",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 2,
        },
        {"op": "remove", "key": "rowB"},
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowB_split1",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 3,
        },
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowB_split2",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 4,
        },
        {
            "op": "add",
            "component": {
                "type": "columns",
                "key": "rowB_split3",
                "columns": [{"width": w} for w in (4, 4, 4)],
            },
            "position": 5,
        },
    ]

    # Compare op-by-op on key/position/type/widths (the "columns" fixture
    # in this test only asserts widths, so trim the actual component's
    # columns down to widths before comparing to the hand-computed
    # expectation above).
    actual = []
    for op in result["operations"]:
        if op["op"] == "remove":
            actual.append(op)
            continue
        trimmed = {
            "op": "add",
            "component": {
                "type": op["component"]["type"],
                "key": op["component"]["key"],
                "columns": [{"width": c["width"]} for c in op["component"]["columns"]],
            },
            "position": op["position"],
        }
        actual.append(trimmed)

    assert actual == expected_ops

    a_positions = [op["position"] for op in actual[1:4]]
    b_positions = [op["position"] for op in actual[5:8]]
    assert a_positions == [0, 1, 2]
    assert b_positions == [3, 4, 5]  # NOT [1, 2, 3] -- offset by rowA's net +2

    applied_by_key = {row["original_key"]: row for row in result["applied_rows"]}
    assert applied_by_key["rowA"]["position"] == 0
    assert applied_by_key["rowB"]["position"] == 3


# ---------------------------------------------------------------------------
# Finding 1: same offset behaviour under a PANEL parent (not just root)
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_offsets_second_row_same_sibling_list_panel() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    row_a = _columns_component("rowA", [4] * 9)
    row_b = _columns_component("rowB", [4] * 9)
    panel = {
        "key": "myPanel",
        "type": "panel",
        "components": [row_a, row_b],
    }
    live = [panel]

    plan_rows = _plan_rows(live)
    assert {row["path"] for row in plan_rows} == {"myPanel/rowA", "myPanel/rowB"}

    result = plan_to_split_operations(plan_rows, live)
    assert result["skipped"] == []

    add_ops_by_prefix: dict[str, list[dict[str, Any]]] = {"rowA": [], "rowB": []}
    for op in result["operations"]:
        if op["op"] != "add":
            continue
        prefix = "rowA" if op["component"]["key"].startswith("rowA") else "rowB"
        add_ops_by_prefix[prefix].append(op)

    a_positions = [op["position"] for op in add_ops_by_prefix["rowA"]]
    b_positions = [op["position"] for op in add_ops_by_prefix["rowB"]]
    assert a_positions == [0, 1, 2]
    assert b_positions == [3, 4, 5]  # NOT [1, 2, 3]
    for op in result["operations"]:
        if op["op"] == "add":
            assert op["parent_key"] == "myPanel"

    applied_by_key = {row["original_key"]: row for row in result["applied_rows"]}
    assert applied_by_key["rowA"]["position"] == 0
    assert applied_by_key["rowB"]["position"] == 3


# ---------------------------------------------------------------------------
# split-then-pad remainder is reflected in the emitted containers
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_reflects_padded_remainder_group() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [3, 3, 3, 3, 3, 3])  # sum 18
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    _, add1, add2 = result["operations"]
    widths1 = [c["width"] for c in add1["component"]["columns"]]
    widths2 = [c["width"] for c in add2["component"]["columns"]]
    assert widths1 == [3, 3, 3, 3]
    assert widths2 == [3, 3, 6]
    filler = add2["component"]["columns"][-1]
    assert filler["components"] == []


# ---------------------------------------------------------------------------
# inline visibility carry: conditional / customConditional copied verbatim
# onto EVERY new container
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_carries_conditional_onto_every_container() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    conditional = {"show": True, "when": "someField", "eq": "yes"}
    target = _columns_component("row1", [4] * 9, conditional=conditional)
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    assert len(add_ops) == 3
    for op in add_ops:
        assert op["component"]["conditional"] == conditional


def test_plan_to_split_operations_carries_custom_conditional_onto_every_container() -> (
    None
):
    from columns_split_apply import (
        plan_to_split_operations,
    )

    custom_conditional = "show = data.someField === 'yes';"
    target = _columns_component("row1", [4] * 9, customConditional=custom_conditional)
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    assert len(add_ops) == 3
    for op in add_ops:
        assert op["component"]["customConditional"] == custom_conditional


# ---------------------------------------------------------------------------
# Blocker 2: container construction is a DEEP-COPY BLACKLIST of the live
# original component, not a field whitelist. Every authored property not
# explicitly cleared must survive verbatim onto EVERY new container, and the
# identity/behaviour fields the split handles explicitly (`id`,
# `behaviourId`, `effectsIds`) must be cleared on every container.
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_deep_copies_original_props_onto_containers() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component(
        "row1",
        [4] * 9,
        id="platform-id-123",
        behaviourId="behaviour-123",
        effectsIds=["effect-1", "effect-2"],
        registrations={"reg-1": True, "reg-2": False},
        customClass="deactivated",
        customClasses=["width10"],
        activate=False,
        tableView=False,
    )
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    assert len(add_ops) == 3
    for op in add_ops:
        component = op["component"]
        # Every other authored property carried verbatim.
        assert component["registrations"] == {"reg-1": True, "reg-2": False}
        assert component["customClass"] == "deactivated"
        assert component["customClasses"] == ["width10"]
        assert component["activate"] is False
        assert component["tableView"] is False
        # Identity/behaviour fields the split handles explicitly are cleared.
        assert "id" not in component
        assert "behaviourId" not in component
        assert "effectsIds" not in component

    # Purity: each container's deep copy is independent -- mutating one
    # emitted component must not affect another, or the live original.
    add_ops[0]["component"]["registrations"]["reg-1"] = False
    assert add_ops[1]["component"]["registrations"]["reg-1"] is True
    assert target["registrations"] == {"reg-1": True, "reg-2": False}


# ---------------------------------------------------------------------------
# Fix 2 (Erick, comment 102512): other 1:1 binding pointers ride the deepcopy
# unchanged and would be silently SHARED across all N containers if ever set
# on a columns component. `_CONTAINER_IDENTITY_FIELDS_TO_CLEAR` must clear
# `componentActionId`, `componentFormulaId`, `componentValidationId`,
# `actionRowIds`, `formulaRowIds` on every emitted container too -- alongside
# the already-cleared `id`/`behaviourId`/`effectsIds` -- while every
# non-identity authored property still carries through verbatim.
# `determinantIds` is deliberately NOT cleared (out of scope, Fix 1).
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_clears_extra_one_to_one_binding_pointers() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component(
        "row1",
        [4] * 9,
        id="platform-id-123",
        behaviourId="behaviour-123",
        effectsIds=["effect-1", "effect-2"],
        componentActionId="action-1",
        componentFormulaId="formula-1",
        componentValidationId="validation-1",
        actionRowIds=["actionrow-1", "actionrow-2"],
        formulaRowIds=["formularow-1"],
        determinantIds=["det-1"],
        registrations={"reg-1": True, "reg-2": False},
        customClass="deactivated",
    )
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    assert len(add_ops) == 3
    for op in add_ops:
        component = op["component"]
        # All identity / 1:1-binding fields cleared.
        assert "id" not in component
        assert "behaviourId" not in component
        assert "effectsIds" not in component
        assert "componentActionId" not in component
        assert "componentFormulaId" not in component
        assert "componentValidationId" not in component
        assert "actionRowIds" not in component
        assert "formulaRowIds" not in component
        # determinantIds is explicitly out of scope for this clear list.
        assert component["determinantIds"] == ["det-1"]
        # Non-identity authored properties still carry through verbatim.
        assert component["registrations"] == {"reg-1": True, "reg-2": False}
        assert component["customClass"] == "deactivated"


# ---------------------------------------------------------------------------
# Fix 3: a component whose DIRECT parent is a keyless (unaddressable)
# intermediate container must be skipped `unsupported_parent_context`, not
# silently re-rooted (a keyless container is NOT the form root).
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_keyless_intermediate_container_parent() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9)
    keyless_panel = {
        # No "key" at all -- unaddressable, but NOT the form root.
        "type": "panel",
        "components": [target],
    }
    live = [keyless_panel]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {
            "path": plan_rows[0]["path"],
            "original_key": "row1",
            "reason": "unsupported_parent_context",
        }
    ]


def test_plan_to_split_operations_skips_keyless_intermediate_columns_parent() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9)
    keyless_outer = {
        # No "key" -- unaddressable columns parent, not the form root.
        "type": "columns",
        "columns": [
            {
                "size": "md",
                "width": 6,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [target],
            },
            {
                "size": "md",
                "width": 6,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [],
            },
        ],
    }
    live = [keyless_outer]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {
            "path": plan_rows[0]["path"],
            "original_key": "row1",
            "reason": "unsupported_parent_context",
        }
    ]


def test_plan_to_split_operations_component_at_true_form_root_still_works() -> None:
    """Contrast case: the ACTUAL form root (no parent at all) legitimately
    omits `parent_key` and is NOT confused with a keyless intermediate
    parent -- it must still split successfully."""
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9)
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    assert len(result["applied_rows"]) == 1
    applied = result["applied_rows"][0]
    assert applied["parent_key"] is None
    assert applied["column_index"] is None
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    for op in add_ops:
        assert "parent_key" not in op


# ---------------------------------------------------------------------------
# managed-behaviour: every row splits structurally (remove + N adds)
# regardless of any managed chain. The `determinant_replication` descriptor
# (the skill executes it after the write to clone the source behaviour onto
# each new key via `componentbehaviour_generate_newkeys`) is gated on a REAL
# `behaviourId` -- the clone's source. A row managed via `behaviourId` DOES
# get the descriptor; a row managed ONLY via `determinantIds`/`effectsIds`
# (no `behaviourId`) does NOT (Erick's post-merge follow-up, comment 102512:
# "handle source_behaviour_id is None explicitly").
# ---------------------------------------------------------------------------
def test_managed_behaviour_id_row_splits_and_emits_descriptor() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9, behaviourId="behaviour-123")
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    # Structural ops emitted exactly like a non-managed row: 1 remove + 3 adds.
    assert result["skipped"] == []
    assert len(result["operations"]) == 4
    remove_op, *add_ops = result["operations"]
    assert remove_op == {"op": "remove", "key": "row1"}
    assert len(add_ops) == 3

    assert len(result["applied_rows"]) == 1
    applied = result["applied_rows"][0]
    assert applied["container_keys"] == [
        "row1_split1",
        "row1_split2",
        "row1_split3",
    ]
    assert applied["determinant_replication"] == {
        "source_key": "row1",
        "target_keys": ["row1_split1", "row1_split2", "row1_split3"],
        "source_behaviour_id": "behaviour-123",
        "target_behaviour_ids": {},
    }
    # target_keys mirrors container_keys exactly.
    descriptor = applied["determinant_replication"]
    assert descriptor["target_keys"] == applied["container_keys"]


def test_determinant_ids_only_row_splits_with_no_replication_descriptor() -> None:
    """Fix 1 (Erick, comment 102512): a row managed ONLY via `determinantIds`
    (no `behaviourId`) has no clone source, so it must NOT emit a
    `determinant_replication` descriptor -- the clone
    (`componentbehaviour_generate_newkeys`) needs a source `behaviourId`, and
    without one it would fail `SOURCE_NOT_FOUND` and spuriously revert. The
    row still splits structurally like any other row (1 remove + N adds)."""
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9, determinantIds=["det-1"])
    live = [target]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    assert len(result["operations"]) == 4  # 1 remove + 3 adds
    remove_op, *add_ops = result["operations"]
    assert remove_op == {"op": "remove", "key": "row1"}
    assert len(add_ops) == 3
    assert len(result["applied_rows"]) == 1
    applied = result["applied_rows"][0]
    assert applied["container_keys"] == [
        "row1_split1",
        "row1_split2",
        "row1_split3",
    ]
    # No behaviourId -> no clone source -> no replication descriptor, and NOT
    # reported as a managed replication row.
    assert applied["determinant_replication"] is None


def test_plan_to_split_operations_managed_row_reverts_cleanly() -> None:
    """A managed row's applied entry (carrying the extra
    `determinant_replication` field) still round-trips through the structural
    revert — the field is ignored for the structural part."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9, behaviourId="behaviour-123")]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]
    assert applied_rows[0]["determinant_replication"] is not None

    post_split_live = _post_split_live(live, applied)
    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["skipped"] == []
    assert len(revert["operations"]) == 4  # 3 removes + 1 add
    *remove_ops, add_op = revert["operations"]
    assert {op["key"] for op in remove_ops} == {
        "row1_split1",
        "row1_split2",
        "row1_split3",
    }
    assert add_op["op"] == "add"
    assert add_op["component"] == live[0]
    assert add_op["position"] == applied_rows[0]["position"]


# ---------------------------------------------------------------------------
# row_not_found
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_row_not_found() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)

    result = plan_to_split_operations(plan_rows, [])

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {"path": "row1", "original_key": "row1", "reason": "row_not_found"}
    ]


# ---------------------------------------------------------------------------
# duplicate_path: two live components resolve to the same walker path
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_both_rows_on_duplicate_path() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    live = [
        {
            "key": "p",
            "type": "panel",
            "components": [_columns_component("c", [4] * 9)],
        },
        {
            "key": "p",
            "type": "panel",
            "components": [_columns_component("c", [3] * 6)],
        },
    ]
    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 2
    assert {row["path"] for row in plan_rows} == {"p/c"}

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {"path": "p/c", "original_key": "c", "reason": "duplicate_path"},
        {"path": "p/c", "original_key": "c", "reason": "duplicate_path"},
    ]


# ---------------------------------------------------------------------------
# duplicate_key: two DISTINCT paths share a live key
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_rows_with_duplicate_live_key() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    live = [
        {
            "key": "panelA",
            "type": "panel",
            "components": [_columns_component("c", [4] * 9)],
        },
        {
            "key": "panelB",
            "type": "panel",
            "components": [_columns_component("c", [3] * 6)],
        },
    ]
    plan_rows = _plan_rows(live)
    assert {row["path"] for row in plan_rows} == {"panelA/c", "panelB/c"}

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert sorted(s["path"] for s in result["skipped"]) == ["panelA/c", "panelB/c"]
    assert {s["reason"] for s in result["skipped"]} == {"duplicate_key"}


# ---------------------------------------------------------------------------
# Finding 2: duplicate_key guard must be FULL-TREE, not columns-only. A
# columns component sharing a key with a non-columns component (here a
# textfield) must also be skipped duplicate_key -- a key-addressed
# `remove` resolves to the first DFS component of ANY type with that key,
# so a collision outside the columns-only index is just as unsafe.
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_duplicate_key_across_component_types() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("dupKey", [4] * 9)
    colliding_textfield = {
        "key": "dupKey",
        "type": "textfield",
        "label": "Collides by key, different type",
    }
    live = [target, colliding_textfield]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1
    assert plan_rows[0]["path"] == "dupKey"

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {"path": "dupKey", "original_key": "dupKey", "reason": "duplicate_key"}
    ]


# ---------------------------------------------------------------------------
# layout_changed: live widths no longer over-12 (or otherwise unsplittable)
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_layout_changed_when_no_longer_over_12() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    original_live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(original_live)

    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"] = mutated_live[0]["columns"][:2]  # now sums to 8

    result = plan_to_split_operations(plan_rows, mutated_live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {"path": "row1", "original_key": "row1", "reason": "layout_changed"}
    ]


# ---------------------------------------------------------------------------
# unsupported_parent_context: original inside a tabs component
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_unsupported_tabs_parent() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9)
    tabs = {
        "key": "myTabs",
        "type": "tabs",
        "tabs": [
            {"key": "tab1", "label": "Tab 1", "components": [target]},
        ],
    }
    live = [tabs]

    plan_rows = _plan_rows(live)
    assert len(plan_rows) == 1

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {
            "path": plan_rows[0]["path"],
            "original_key": "row1",
            "reason": "unsupported_parent_context",
        }
    ]


# ---------------------------------------------------------------------------
# container_key_collision: a proposed container key already exists live
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_skips_container_key_collision() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    target = _columns_component("row1", [4] * 9)
    colliding_field = {
        "key": "row1_split2",
        "type": "textfield",
        "label": "Collides",
    }
    live = [target, colliding_field]

    plan_rows = _plan_rows(live)
    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert result["skipped"] == [
        {
            "path": "row1",
            "original_key": "row1",
            "reason": "container_key_collision",
        }
    ]


# ---------------------------------------------------------------------------
# live re-derivation beats stale plan
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_uses_live_grouping_not_stale_plan() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    original_live = [_columns_component("row1", [4] * 9)]  # 9x4 -> [4,4,4]x3
    plan_rows = _plan_rows(original_live)
    assert plan_rows[0]["containers"][0]["widths"] == [4, 4, 4]

    # Live form has since changed: 9x4 -> 6x6 (still sums to 36, but a
    # different grouping: three [6,6] containers, not the stale [4,4,4]x3).
    # NB: a non-width-12 grouping is used on purpose — an all-12 row
    # (e.g. 3x12) is CSS-handled (TOBE-18019/#441) and plan_split returns
    # None for it, so it is no longer a "still-splittable" shape.
    mutated_live = deepcopy(original_live)
    mutated_live[0]["columns"] = [_col(6, key=f"row1_g{i}") for i in range(6)]

    result = plan_to_split_operations(plan_rows, mutated_live)

    assert result["skipped"] == []
    add_ops = [op for op in result["operations"] if op["op"] == "add"]
    assert len(add_ops) == 3
    for op in add_ops:
        widths = [c["width"] for c in op["component"]["columns"]]
        assert widths == [6, 6]  # LIVE grouping, not the stale plan's [4,4,4]


# ---------------------------------------------------------------------------
# input-not-mutated
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_does_not_mutate_inputs() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    live_copy = deepcopy(live)
    plan_copy = deepcopy(plan_rows)

    result = plan_to_split_operations(plan_rows, live)
    assert live == live_copy
    assert plan_rows == plan_copy

    # Mutating the returned op's component must not affect the live tree.
    add_op = next(op for op in result["operations"] if op["op"] == "add")
    add_op["component"]["columns"][0]["width"] = 999
    assert live[0]["columns"][0]["width"] == 4


# ---------------------------------------------------------------------------
# fail loud on bad shape
# ---------------------------------------------------------------------------
def test_plan_to_split_operations_raises_on_non_list_live_components() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)

    with pytest.raises(ValueError):
        plan_to_split_operations(plan_rows, _form(live))  # type: ignore[arg-type]


def test_revert_split_operations_raises_on_non_list_live_components() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied_rows = plan_to_split_operations(plan_rows, live)["applied_rows"]

    with pytest.raises(ValueError):
        revert_split_operations(applied_rows, _form(live))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# revert round-trip: N removes + 1 add restoring the original
# ---------------------------------------------------------------------------
def _post_split_live(
    live: list[dict[str, Any]], applied: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build a hand-crafted "post-split" live tree: the original component at
    ``applied["position"]`` in the root list is replaced by its N written
    containers, in order."""
    applied_row = applied["applied_rows"][0]
    containers = deepcopy(applied_row["written_containers"])
    position = applied_row["position"]
    new_live = deepcopy(live)
    new_live[position : position + 1] = containers
    return new_live


def test_revert_split_operations_restores_pristine_split() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)

    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["skipped"] == []
    assert len(revert["operations"]) == 4  # 3 removes + 1 add
    *remove_ops, add_op = revert["operations"]
    assert {op["key"] for op in remove_ops} == {
        "row1_split1",
        "row1_split2",
        "row1_split3",
    }
    assert add_op["op"] == "add"
    assert add_op["component"] == live[0]
    assert add_op["position"] == applied_rows[0]["position"]
    assert "parent_key" not in add_op
    assert "column_index" not in add_op


# ---------------------------------------------------------------------------
# Finding 3: revert must tolerate platform-injected default keys.
# `form_patch add` into a columns parent routes through `insert_component`,
# which injects defaults (`determinantIds`, `version`, `tableView`, ...) --
# the live container is then a strict SUPERSET of the minimal emitted
# payload and would never full-dict-equal it. This test MUST fail against
# the pre-fix full-dict-`==` comparison.
# ---------------------------------------------------------------------------
def test_revert_split_operations_tolerates_platform_injected_default_keys() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)
    for container in post_split_live:
        # Simulate the platform-injected defaults `insert_component` adds
        # on write -- extra keys beyond what this module emitted.
        container["determinantIds"] = []
        container["version"] = "abc123"
        container["tableView"] = False

    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["skipped"] == []
    assert len(revert["operations"]) == 4  # 3 removes + 1 add
    *remove_ops, add_op = revert["operations"]
    assert {op["key"] for op in remove_ops} == {
        "row1_split1",
        "row1_split2",
        "row1_split3",
    }
    assert add_op["op"] == "add"
    assert add_op["component"] == live[0]
    assert add_op["position"] == applied_rows[0]["position"]


# ---------------------------------------------------------------------------
# Finding 3 (contrast case): a GENUINE edit to a container's `columns`
# array (not just extra injected metadata keys) must still trip
# modified_since_apply.
# ---------------------------------------------------------------------------
def test_revert_split_operations_detects_genuine_columns_edit_since_apply() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)
    # A designer genuinely changed a column's width in the first container.
    post_split_live[0]["columns"][0]["width"] = 6

    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["operations"] == []
    assert revert["skipped"] == [
        {
            "path": "row1",
            "original_key": "row1",
            "reason": "modified_since_apply",
        }
    ]


def test_revert_split_operations_skips_when_container_modified_since_apply() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)
    # A designer added a field into the first container since apply.
    post_split_live[1]["columns"][0]["components"].append(
        {"key": "new_field", "type": "textfield", "label": "New"}
    )

    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["operations"] == []
    assert revert["skipped"] == [
        {
            "path": "row1",
            "original_key": "row1",
            "reason": "modified_since_apply",
        }
    ]


def test_revert_split_operations_skips_when_container_missing() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)
    # One of the containers was deleted since apply.
    del post_split_live[1]

    revert = revert_split_operations(applied_rows, post_split_live)

    assert revert["operations"] == []
    assert revert["skipped"] == [
        {
            "path": "row1",
            "original_key": "row1",
            "reason": "modified_since_apply",
        }
    ]


def test_revert_split_operations_does_not_mutate_inputs() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]

    post_split_live = _post_split_live(live, applied)
    applied_rows_copy = deepcopy(applied_rows)
    post_split_live_copy = deepcopy(post_split_live)

    result = revert_split_operations(applied_rows, post_split_live)
    assert applied_rows == applied_rows_copy
    assert post_split_live == post_split_live_copy

    result["operations"][-1]["component"]["columns"][0]["width"] = 999
    assert post_split_live_copy[0] == post_split_live[0]


# ---------------------------------------------------------------------------
# Revert-path corruption guard (regression, TOBE-18009 els-dev canary).
#
# `container_keys` and `written_containers` are produced together and must
# stay the same length. Verifying only a prefix would leave `pristine` True
# while later containers went unchecked -- i.e. a blind restore over state
# nobody verified. This was previously enforced by `zip(..., strict=True)`,
# which is Python 3.10+ ONLY and therefore crashed the whole revert path on
# stock macOS `python3` (3.9) with "zip() takes no keyword arguments" -- the
# forward apply worked, but the RECOVERY path did not. The invariant is now
# an explicit length check; these tests lock the behaviour in, and the CI
# Python matrix (see .github/workflows/test-plugin-scripts.yml) locks in the
# version floor that made the original break invisible.
# ---------------------------------------------------------------------------
def test_revert_split_operations_raises_on_length_mismatch() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]
    post_split_live = _post_split_live(live, applied)

    corrupt = deepcopy(applied_rows)
    # Drop one written_containers entry: a prefix-only zip would silently
    # accept this row and emit a restore having checked only 2 of 3.
    corrupt[0]["written_containers"] = corrupt[0]["written_containers"][:-1]
    assert len(corrupt[0]["container_keys"]) != len(corrupt[0]["written_containers"])

    with pytest.raises(ValueError, match="corrupt"):
        revert_split_operations(corrupt, post_split_live)


def test_revert_split_operations_raises_on_excess_written_containers() -> None:
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]
    post_split_live = _post_split_live(live, applied)

    corrupt = deepcopy(applied_rows)
    corrupt[0]["container_keys"] = corrupt[0]["container_keys"][:-1]

    with pytest.raises(ValueError, match="corrupt"):
        revert_split_operations(corrupt, post_split_live)


def test_revert_split_operations_reports_every_corrupt_row_at_once() -> None:
    """Finding 3 (PR #56 review): the length check is a PRE-PASS, so an
    operator recovering from a bad apply sees ALL corrupt rows in one error
    rather than fixing row 1, re-running, and only then discovering row 2.
    This is the recovery path -- its ergonomics matter most exactly when
    something has already gone wrong."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [
        _columns_component("row1", [4] * 9),
        _columns_component("row2", [4] * 9),
    ]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    applied_rows = applied["applied_rows"]
    assert len(applied_rows) == 2

    corrupt = deepcopy(applied_rows)
    corrupt[0]["written_containers"] = corrupt[0]["written_containers"][:-1]
    corrupt[1]["container_keys"] = corrupt[1]["container_keys"][:-1]

    with pytest.raises(ValueError, match="corrupt") as excinfo:
        revert_split_operations(corrupt, live)

    message = str(excinfo.value)
    assert "2 applied row(s) corrupt" in message
    # BOTH rows named -- not just the first one encountered.
    assert "row1" in message
    assert "row2" in message


def test_revert_split_operations_raises_before_emitting_any_operations() -> None:
    """The pre-pass must abort before a single operation is built: a partial
    operations list from a run that then raised would be a trap for a caller
    that catches ValueError and inspects what it got."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [
        _columns_component("row1", [4] * 9),
        _columns_component("row2", [4] * 9),
    ]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)
    post_split_live = deepcopy(live)

    corrupt = deepcopy(applied["applied_rows"])
    # Corrupt only the SECOND row; the first would otherwise emit operations.
    corrupt[1]["written_containers"] = corrupt[1]["written_containers"][:-1]

    with pytest.raises(ValueError, match="corrupt"):
        revert_split_operations(corrupt, post_split_live)


def test_revert_split_operations_still_raises_when_first_container_not_pristine() -> (
    None
):
    """Finding 1 (PR #56 review): the old `zip(strict=True)` was an INCOMPLETE
    guard. The verification loop `break`s on the first non-pristine container,
    and `strict=` only fires when zip advances past an exhausted iterator -- so
    a corrupt row whose FIRST container was already non-pristine broke out
    before `strict` ever ran and was silently downgraded to a
    `modified_since_apply` skip. The pre-pass catches it as the error it is."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_component("row1", [4] * 9)]
    plan_rows = _plan_rows(live)
    applied = plan_to_split_operations(plan_rows, live)

    corrupt = deepcopy(applied["applied_rows"])
    corrupt[0]["written_containers"] = corrupt[0]["written_containers"][:-1]

    # Live tree where the FIRST container is absent -> first iteration would
    # have set pristine=False and broken out under the old code.
    post_split_live: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="corrupt"):
        revert_split_operations(corrupt, post_split_live)


# ---------------------------------------------------------------------------
# single-container plans + review rows (marketplace #58)
# ---------------------------------------------------------------------------
def _col_maybe_empty(width: int, key: str | None) -> dict[str, Any]:
    """A source column; ``key=None`` builds an empty spacer column."""
    return _col(width, key=key)


def _columns_with_content_flags(
    key: str, widths: list[int], flags: str
) -> dict[str, Any]:
    """Columns component where ``flags`` marks each column ``1`` (has a field)
    or ``0`` (empty spacer)."""
    assert len(widths) == len(flags)
    return {
        "key": key,
        "type": "columns",
        "columns": [
            _col_maybe_empty(w, None if flags[i] == "0" else f"{key}_f{i}")
            for i, w in enumerate(widths)
        ],
    }


def test_apply_tolerates_a_single_container_plan() -> None:
    """Erick's case 2 on #58: dropping a content-less group can legitimately
    leave ONE surviving container, i.e. a 1->1 rewrite. The apply side must
    emit `remove` + a single `add` rather than assuming N > 1 anywhere."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_with_content_flags("row1", [6, 6, 6], "110")]
    plan_rows = _plan_rows(live)

    assert len(plan_rows) == 1
    assert len(plan_rows[0]["containers"]) == 1

    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    ops = result["operations"]
    assert [op["op"] for op in ops] == ["remove", "add"]
    assert ops[0]["key"] == "row1"
    assert ops[1]["component"]["key"] == "row1_split1"
    assert [c["width"] for c in ops[1]["component"]["columns"]] == [6, 6]
    assert len(result["applied_rows"]) == 1
    assert result["applied_rows"][0]["container_keys"] == ["row1_split1"]


def test_apply_round_trips_a_single_container_plan() -> None:
    """The revert path must survive the 1->1 shape too — it is the recovery
    story for exactly the rows this fix newly makes applicable."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_with_content_flags("row1", [6, 6, 6], "110")]
    result = plan_to_split_operations(_plan_rows(live), live)

    written = [op["component"] for op in result["operations"] if op["op"] == "add"]
    reverted = revert_split_operations(result["applied_rows"], written)

    assert reverted["skipped"] == []
    assert [op["op"] for op in reverted["operations"]] == ["remove", "add"]


def test_apply_skips_an_all_columns_empty_review_row() -> None:
    """A row whose every group is content-less is surfaced as `review`, never
    split. The apply side must skip it — emitting nothing for it, and above all
    never emitting the bare `remove` that would delete the component."""
    from columns_split_apply import (
        plan_to_split_operations,
        revert_split_operations,
    )

    live = [_columns_with_content_flags("row1", [8, 8], "00")]
    plan_rows = _plan_rows(live)

    assert len(plan_rows) == 1
    assert plan_rows[0]["action"] == "review"
    assert plan_rows[0]["reason"] == "all_columns_empty"

    result = plan_to_split_operations(plan_rows, live)

    assert result["operations"] == []
    assert result["applied_rows"] == []


# ---------------------------------------------------------------------------
# grid-nested apply (TOBE-18041)
# ---------------------------------------------------------------------------
def _editgrid(key: str, children: "list[dict[str, Any]]") -> "dict[str, Any]":
    return {"key": key, "type": "editgrid", "components": children}


def _panel(key: str, children: "list[dict[str, Any]]") -> "dict[str, Any]":
    return {"key": key, "type": "panel", "components": children}


def test_split_applies_inside_a_grid_nested_panel() -> None:
    """TOBE-18041 acceptance 1: add + remove resolve inside a grid subtree.
    The panel parent sits inside an editgrid; the ops must address the PANEL
    (parent_key=p), never the grid, and never re-root."""
    from columns_split_apply import plan_to_split_operations

    target = _columns_component("row1", [4] * 9)
    live = [_editgrid("grid", [_panel("p", [target])])]
    plan_rows = _plan_rows(live)

    assert [r["action"] for r in plan_rows] == ["split"]
    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    ops = result["operations"]
    assert [op["op"] for op in ops] == ["remove", "add", "add", "add"]
    for n, op in enumerate(ops[1:]):
        assert op["parent_key"] == "p", "must address the panel inside the grid"
        assert "column_index" not in op
        assert op["position"] == n
    assert result["applied_rows"][0]["container_keys"] == [
        "row1_split1",
        "row1_split2",
        "row1_split3",
    ]


def test_two_split_rows_sharing_a_panel_inside_a_grid_keep_position_arithmetic() -> None:
    """TOBE-18041 acceptance 1, the position-drift case: two rows in the SAME
    panel inside a grid — the second row's adds must be offset by the net
    growth from the first (each split is -1 original +N containers)."""
    from columns_split_apply import plan_to_split_operations

    row_a = _columns_component("rowA", [4] * 9)   # -> 3 containers (net +2)
    row_b = _columns_component("rowB", [6] * 3)   # -> 2 containers
    live = [_editgrid("grid", [_panel("p", [row_a, row_b])])]
    plan_rows = _plan_rows(live)
    assert [r["original_key"] for r in plan_rows] == ["rowA", "rowB"]

    result = plan_to_split_operations(plan_rows, live)

    assert result["skipped"] == []
    adds = [op for op in result["operations"] if op["op"] == "add"]
    by_key = {op["component"]["key"]: op["position"] for op in adds}
    assert by_key == {
        "rowA_split1": 0,
        "rowA_split2": 1,
        "rowA_split3": 2,
        # rowB sat at base position 1; rowA grew the panel by +2 -> 3
        "rowB_split1": 3,
        "rowB_split2": 4,
    }


def test_direct_child_of_grid_is_still_refused_by_the_apply() -> None:
    """TOBE-18041 acceptance 6, defense-in-depth: the scan never emits a
    direct child, but a FORGED plan row targeting one must still be skipped —
    the DS grid rule owns that row and a split would degrade it."""
    from columns_split import plan_split
    from columns_split_apply import plan_to_split_operations

    target = _columns_component("row1", [4] * 9)
    live = [_editgrid("grid", [target])]
    forged = dict(plan_split(target) or {})
    forged["path"] = "grid/row1"

    result = plan_to_split_operations([forged], live)

    assert result["operations"] == []
    assert result["applied_rows"] == []
    assert [sk["reason"] for sk in result["skipped"]] == ["unsupported_parent_context"]


def test_tabs_inside_a_grid_are_still_unsupported() -> None:
    """Narrowing the grid guard must not weaken the tabs/table rule: a row
    inside a tabs pane inside a grid stays unsupported."""
    from columns_split import plan_split
    from columns_split_apply import plan_to_split_operations

    target = _columns_component("row1", [4] * 9)
    tabs = {
        "key": "tabs1",
        "type": "tabs",
        "tabs": [{"key": "pane1", "components": [target]}],
    }
    live = [_editgrid("grid", [tabs])]
    forged = dict(plan_split(target) or {})
    forged["path"] = "grid/tabs1/row1"

    result = plan_to_split_operations([forged], live)

    assert result["operations"] == []
    assert [sk["reason"] for sk in result["skipped"]] == ["unsupported_parent_context"]


def test_grid_nested_split_reverts_cleanly() -> None:
    """TOBE-18041 acceptance 3: the revert path works for a grid-nested row —
    remove the containers, re-add the original into the panel inside the
    grid, pristine check passing."""
    from columns_split_apply import plan_to_split_operations, revert_split_operations

    target = _columns_component("row1", [4] * 9)
    live = [_editgrid("grid", [_panel("p", [target])])]
    result = plan_to_split_operations(_plan_rows(live), live)
    assert result["skipped"] == []

    written = [op["component"] for op in result["operations"] if op["op"] == "add"]
    reverted = revert_split_operations(result["applied_rows"], written)

    assert reverted["skipped"] == []
    ops = reverted["operations"]
    assert [op["op"] for op in ops] == ["remove", "remove", "remove", "add"]
    assert ops[-1]["component"]["key"] == "row1"
    assert ops[-1].get("parent_key") == "p"
