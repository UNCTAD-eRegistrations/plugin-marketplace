"""Pure logic for column-layout normalization: walker + normalize-to-12 rules.

No I/O except the optional ``python -m`` CLI seam at the bottom — everything
else operates on parsed Form.io trees. Spec: TOBE-18003 / DS-Frontend#172.

IMPORTANT — placement / invariants:
  - This is a stdlib-only script bundled in the columns-normalization-migration
    skill, invoked by CLI. It ships as a plain script module so the
    SQL (TOBE-18007) and TypeScript (TOBE-18006) ports can mirror its rules.
  - It must remain STDLIB-ONLY (no third-party dependencies).
  - The walker normalizes ONLY column-layout width fields. It must never
    rewrite a textarea's ``rows`` (or any non-width int-valued prop) or descend
    into non-layout component props — a textarea rows:3 input round-trips
    byte-identical.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

GRID_TYPES = frozenset({"editgrid", "datagrid"})
TARGET_SUM = 12
EXCLUDED_KEYS = frozenset({"my-applications-pagination", "myApplicationsNavButtons"})
EXCLUDED_CUSTOM_CLASS = "adjust-columns"


# ---------------------------------------------------------------------------
# Walker
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ColumnsHit:
    """One columns component found in a form tree.

    ``grid_context`` is the two-class in-grid rule (TOBE-18037):

    - ``"direct_child"`` — the schema parent IS an editgrid/datagrid. The DS
      grid rule (`:where(.editing-entry, .new-entry) > .formio-component-
      columns.row` + per-width `grid-column: span N`) lays these out on 12
      tracks and wraps them correctly by construction — they must never be
      padded or split. Confirmed at effect level on live test.kenya
      (task zero, TOBE-18037 comment 103432).
    - ``"nested"`` — an editgrid/datagrid is a FARTHER ancestor (the row sits
      inside a panel/columns/etc. within the grid). The `>` combinator cannot
      reach it, so it falls through to the ordinary #171 fluid flex model
      like any top-level row.
    - ``"none"`` — no grid ancestor at all.

    ``inside_grid`` is kept as the derived boolean (``grid_context != "none"``)
    for existing consumers; the sticky boolean alone conflated the two
    in-grid classes, which is what TOBE-18037 corrects.
    """

    component: dict[str, Any]
    path: str
    inside_grid: bool
    grid_context: str = "none"


def _iter_node(
    node: dict[str, Any], prefix: str, parent_is_grid: bool, ancestor_grid: bool
) -> Iterator[ColumnsHit]:
    key = node.get("key") or ""
    path = f"{prefix}/{key}" if prefix and key else (key or prefix)
    if node.get("type") == "columns":
        if parent_is_grid:
            grid_context = "direct_child"
        elif ancestor_grid:
            grid_context = "nested"
        else:
            grid_context = "none"
        yield ColumnsHit(
            component=node,
            path=path,
            inside_grid=grid_context != "none",
            grid_context=grid_context,
        )
    # Only a grid's OWN `components` children are its direct children. The
    # columns/rows/tabs branches below never apply to a grid node (editgrid/
    # datagrid hold children via `components[]` only), so passing
    # `node_is_grid` uniformly is exact, not an approximation.
    node_is_grid = node.get("type") in GRID_TYPES
    child_grid = ancestor_grid or node_is_grid

    children = node.get("components")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                yield from _iter_node(child, path, node_is_grid, child_grid)
    columns = node.get("columns")
    if isinstance(columns, list):
        for column in columns:
            if isinstance(column, dict):
                for child in column.get("components") or []:
                    if isinstance(child, dict):
                        yield from _iter_node(child, path, False, child_grid)
    rows = node.get("rows")
    # NOTE: only a list-valued `rows` is a table layout to descend into. A
    # scalar `rows` (e.g. a textarea's rows:3) is NOT a layout field and must
    # be left untouched — this guard is what keeps textarea rows byte-identical.
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict):
                        for child in cell.get("components") or []:
                            if isinstance(child, dict):
                                yield from _iter_node(child, path, False, child_grid)
    tabs = node.get("tabs")
    if isinstance(tabs, list):
        for pane in tabs:
            if isinstance(pane, dict):
                for child in pane.get("components") or []:
                    if isinstance(child, dict):
                        yield from _iter_node(child, path, False, child_grid)


def iter_columns_components(
    components: list[dict[str, Any]],
) -> Iterator[ColumnsHit]:
    """Depth-first over a Form.io tree, yielding every columns component.

    Recurses through ``components``, ``columns[].components``, table ``rows``
    (list-valued only), and tabs. ``grid_context`` distinguishes a DIRECT child of an
    editgrid/datagrid (CSS-owned, never normalized) from a row nested
    deeper inside one (ordinary flex row); ``inside_grid`` is the derived
    boolean. Duplicated component paths are BOTH yielded (they share
    a path) so downstream can resolve unambiguously or skip — never silently
    pick a first/arbitrary match.
    """
    for node in components:
        if isinstance(node, dict):
            yield from _iter_node(node, "", False, False)


# ---------------------------------------------------------------------------
# normalize-to-12
# ---------------------------------------------------------------------------
def normalize_to_12(widths: Sequence[int]) -> list[int]:
    """Redistribute ``widths`` to a positive-int set summing to exactly 12.

    Column count is preserved. Every output width is >= 1. The remainder is
    assigned by an explicit, stable largest-remainder rule (Hamilton), so the
    result is deterministic and the SQL/TS ports can reproduce it.

    Fails loud (ValueError/TypeError) on an empty set, a null width, or a
    non-int width rather than emit a corrupt plan.
    """
    if not widths:
        raise ValueError("cannot normalize an empty column set")
    for w in widths:
        if isinstance(w, bool) or not isinstance(w, int):
            raise TypeError(f"column width must be an int, got {w!r}")
    n = len(widths)
    if n > TARGET_SUM:
        raise ValueError(
            f"cannot fit {n} columns into {TARGET_SUM} with each width >= 1"
        )

    total = sum(widths)
    if total <= 0:
        raise ValueError(f"column widths must be positive; got sum {total}")

    # Every column keeps a floor of 1; distribute the remaining units in
    # proportion to the input widths using largest-remainder rounding.
    base = [1] * n
    remaining = TARGET_SUM - n
    if remaining == 0:
        return base

    quotas = [w / total * remaining for w in widths]
    floors = [int(math.floor(q)) for q in quotas]
    leftover = remaining - sum(floors)
    # Assign leftover units to the largest fractional remainders; ties break
    # toward the earliest column index (stable, repeatable).
    order = sorted(range(n), key=lambda i: (-(quotas[i] - floors[i]), i))
    for i in order[:leftover]:
        floors[i] += 1
    return [base[i] + floors[i] for i in range(n)]


# ---------------------------------------------------------------------------
# analyze one columns component
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    """Outcome of analyzing one columns component."""

    action: str  # "skip" | "append" | "resize"
    reason: str
    base_sum: int | None = None
    widths: list[int | None] | None = None
    filler_width: int | None = None
    filler_size: str | None = None
    new_columns: list[dict[str, Any]] | None = None


def _is_empty_column(col: dict[str, Any]) -> bool:
    return not (col.get("components") or [])


def _dominant_size(columns: list[dict[str, Any]]) -> str:
    sizes = [c.get("size") or "md" for c in columns]
    if not sizes:
        return "md"
    # dict preserves insertion order: ties break toward the earliest column
    return max(dict.fromkeys(sizes), key=sizes.count)


def analyze_columns_component(
    component: dict[str, Any],
    *,
    inside_grid: bool = False,
    grid_context: str | None = None,
) -> Verdict:
    """Apply the TOBE-18003 padding rule to one columns component.

    Never mutates the input; ``new_columns`` is a deep copy. Only width fields
    are ever written — no ``rows`` (or other non-width) prop is introduced.

    ``grid_context`` (TOBE-18037) takes precedence over the legacy
    ``inside_grid`` boolean when provided: ``"direct_child"`` rows skip as
    ``grid_direct_child`` (the DS grid rule owns their layout), ``"nested"``
    rows skip as ``inside_grid_nested`` (deferred to the TOBE-18041 apply
    half and its canary — the scan half must not open a write path). Both
    carry a RAW width sum (spacers included, matching the split module's
    boundary semantics) so the inventory can size them; the old single
    ``inside_grid`` skip reported ``base_sum`` None. The legacy boolean path
    is byte-identical to before — the pad APPLY re-verifies live rows through
    it and needs no change.
    """
    columns = component.get("columns") or []
    widths = [c.get("width") for c in columns]

    if grid_context in ("direct_child", "nested"):
        raw_sum = sum(
            w for w in widths if isinstance(w, int) and not isinstance(w, bool)
        )
        reason = (
            "grid_direct_child"
            if grid_context == "direct_child"
            else "inside_grid_nested"
        )
        return Verdict(action="skip", reason=reason, base_sum=raw_sum, widths=widths)
    if inside_grid:
        return Verdict(action="skip", reason="inside_grid", widths=widths)
    if not component.get("key"):
        return Verdict(action="skip", reason="no_key", widths=widths)
    custom_class = component.get("customClass") or ""
    if EXCLUDED_CUSTOM_CLASS in custom_class.split():
        return Verdict(action="skip", reason="adjust_columns", widths=widths)
    if component.get("key") in EXCLUDED_KEYS:
        return Verdict(action="skip", reason="excluded_key", widths=widths)
    if not columns:
        return Verdict(action="skip", reason="no_columns", widths=widths)
    if any(not isinstance(w, int) or isinstance(w, bool) for w in widths):
        return Verdict(action="skip", reason="null_width", widths=widths)
    if any(isinstance(w, int) and not (1 <= w <= 12) for w in widths):
        return Verdict(action="skip", reason="invalid_width", widths=widths)

    # Trailing empty columns are a designer's spacer or a previous filler.
    n_trailing = 0
    for col in reversed(columns):
        if _is_empty_column(col):
            n_trailing += 1
        else:
            break
    body = columns[: len(columns) - n_trailing]
    if not body:
        return Verdict(action="skip", reason="all_empty", widths=widths)
    base_sum = sum(c["width"] for c in body)
    if base_sum >= TARGET_SUM:
        reason = "complete" if base_sum == TARGET_SUM else "over_12"
        # A complete/over row keeps any trailing empties untouched.
        return Verdict(action="skip", reason=reason, base_sum=base_sum, widths=widths)

    filler_width = TARGET_SUM - base_sum
    new_columns = copy.deepcopy(body)
    if n_trailing:
        # Resize (and merge) existing trailing empties into one filler,
        # preserving the first trailing column's identity minus its width.
        filler = copy.deepcopy(columns[len(body)])
        filler["width"] = filler_width
        filler["components"] = []
        filler.pop("hideIfEmpty", None)
        new_columns.append(filler)
        filler_size = filler.get("size") or "md"
        action = "resize"
    else:
        filler_size = _dominant_size(body)
        new_columns.append(
            {
                "size": filler_size,
                "width": filler_width,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [],
            }
        )
        action = "append"

    # Idempotency: if new_columns is identical to the original,
    # report as already normalized instead of proposing a no-op change.
    if new_columns == columns:
        return Verdict(
            action="skip",
            reason="already_normalized",
            base_sum=base_sum,
            widths=widths,
        )

    return Verdict(
        action=action,
        reason="under_12",
        base_sum=base_sum,
        widths=widths,
        filler_width=filler_width,
        filler_size=filler_size,
        new_columns=new_columns,
    )


# ---------------------------------------------------------------------------
# Plan builder + CLI (`python3 scripts/columns_logic.py`)
# ---------------------------------------------------------------------------
def build_plan(form: Any) -> dict[str, Any]:
    """Build a read-only normalization plan from a parsed Form.io form.

    Fails loud (ValueError) on an unexpected form shape or a malformed columns
    component (null/invalid width) rather than emit a corrupt plan.
    """
    if not isinstance(form, dict):
        raise ValueError("form must be a JSON object with a 'components' array")
    components = form.get("components")
    if not isinstance(components, list):
        raise ValueError("form must have a 'components' array")

    rows: list[dict[str, Any]] = []
    for hit in iter_columns_components(components):
        verdict = analyze_columns_component(
            hit.component, grid_context=hit.grid_context
        )
        if verdict.reason in ("null_width", "invalid_width"):
            raise ValueError(
                f"malformed columns component at {hit.path!r}: {verdict.reason}"
            )
        rows.append(
            {
                "path": hit.path,
                "key": hit.component.get("key") or "",
                "inside_grid": hit.inside_grid,
                "grid_context": hit.grid_context,
                "action": verdict.action,
                "reason": verdict.reason,
                "base_sum": verdict.base_sum,
                "new_columns": verdict.new_columns,
            }
        )
    return {"plan": rows, "count": len(rows)}


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    """CLI seam: read a form as JSON on stdin, emit a JSON plan on stdout.

    Fails loud (non-zero exit + explanatory stderr) on non-JSON input, an
    unexpected form shape, or a malformed component tree. Never emits a plan
    on stdout for invalid input.
    """
    parser = argparse.ArgumentParser(
        prog="python3 scripts/columns_logic.py",
        description="Emit a read-only columns normalization plan for a Form.io "
        "form read as JSON on stdin.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the form JSON from stdin (default behaviour).",
    )
    parser.parse_args(argv)

    if stdin_text is None:
        stdin_text = sys.stdin.read()

    try:
        form = json.loads(stdin_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"error: invalid JSON on stdin: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    try:
        plan = build_plan(form)
    except (ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    json.dump(plan, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
