"""Pure logic for under-12 columns "apply" OPERATIONS: transform a
``columns_logic.build_plan`` plan plus a freshly-fetched live form's
component list into the ``form_patch`` SET operations a skill session would
send. Spec: TOBE-18005, unblocked by the DS-Frontend padding gate
(TOBE-18004).

IMPORTANT — placement / invariants:
  - This is a SEPARATE, ADDITIVE module. It must NEVER change the behaviour
    of ``columns_logic.analyze_columns_component`` or ``build_plan`` — this
    module only adds a new, independent capability alongside them.
  - This is a stdlib-only script bundled in the columns-normalization-migration
    skill, invoked by CLI, exactly like ``columns_logic.py`` /
    ``columns_split.py``.
  - It must remain STDLIB-ONLY (no third-party dependencies), plus intra-
    package reuse of ``columns_logic`` for the tree walker and analyzer —
    no other ``tools`` or ``BPAClient`` imports.
  - READ-ONLY / NO WRITES: this module never calls ``form_patch`` and never
    mutates a form or a component. It only computes the operations a caller
    (the skill session) would send. It never registers an MCP tool.

LAST-WRITE-WINS SAFETY (why re-verification, not blind apply):
  A plan is built from a form snapshot that may be stale by the time a skill
  session is ready to write — another designer may have edited the form in
  between. Since BPA's form_patch is last-write-wins (it overwrites whatever
  is live, not a merge), applying a stale plan verbatim could silently
  revert someone else's concurrent edit. So ``plan_to_operations`` re-walks
  the LIVE component tree and re-runs ``analyze_columns_component`` on the
  live component right before building each operation, and only proceeds
  when the live verdict still agrees with the plan (same path, same
  resulting action). The emitted ``columns`` are always the LIVE-derived
  ``new_columns`` — so a content edit that kept widths intact (e.g. a field
  added into an existing column) survives the apply instead of being
  reverted to the plan's stale component snapshot.

  ``revert_operations`` mirrors this caution: it restores a row's original
  columns only when the live columns still deep-equal exactly what
  ``plan_to_operations`` last wrote (i.e. nothing has touched the row since
  apply) — never a blind restore.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any

from columns_logic import (
    analyze_columns_component,
    iter_columns_components,
)


def _require_live_components_list(live_components: Any) -> None:
    """Fail loud when ``live_components`` isn't a list — e.g. a caller
    passed the whole form dict instead of ``form["components"]``. Mirrors
    ``columns_logic.build_plan``'s fail-loud shape check instead of silently
    walking nothing and reporting every row ``row_not_found``.
    """
    if not isinstance(live_components, list):
        raise ValueError("live_components must be a list of Form.io components")


def _build_live_index(
    live_components: list[dict[str, Any]],
) -> dict[str, list[tuple[dict[str, Any], str]]]:
    """Index every live columns hit by walker path, built ONCE per call.

    Walker paths are not guaranteed unique (e.g. two sibling panels sharing
    a key, each containing a same-keyed columns component, both resolve to
    the same path) — so each path maps to a LIST of ``(component,
    grid_context)`` hits. Callers must treat more than one hit for a path as
    ambiguous and skip it (``duplicate_path``) rather than guessing.
    """
    index: dict[str, list[tuple[dict[str, Any], str]]] = {}
    for hit in iter_columns_components(live_components):
        index.setdefault(hit.path, []).append((hit.component, hit.grid_context))
    return index


def _live_key_counts(
    live_index: dict[str, list[tuple[dict[str, Any], str]]],
) -> dict[str, int]:
    """Count how many live columns components carry each non-empty ``key``.

    A ``form_patch`` SET op addresses a component by ``key``, but walker
    paths are per-tree-position: two columns components at DIFFERENT paths
    (distinct parents, same child key) can still share a key. Emitting ops
    for both would collide on one key downstream, so a key seen more than
    once is ambiguous for addressing — the key-addressed analogue of the
    ``duplicate_path`` guard. Derived from the already-built path index, so
    no extra tree walk.
    """
    counts: dict[str, int] = {}
    for hits in live_index.values():
        for component, _grid_context in hits:
            key = component.get("key") or ""
            if key:
                counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# plan_to_operations
# ---------------------------------------------------------------------------
def plan_to_operations(
    plan_rows: list[dict[str, Any]], live_components: list[dict[str, Any]]
) -> dict[str, Any]:
    """Transform actionable plan rows into live-re-verified ``form_patch``
    SET operations.

    Pure — never mutates ``plan_rows``, ``live_components``, or anything
    reachable from them. Only rows whose plan ``action`` is "append" or
    "resize" are considered; "skip" rows are ignored entirely (they never
    appear in ``operations``, ``applied_rows``, or ``skipped``).

    Returns ``{"operations": [...], "applied_rows": [...], "skipped": [...]}``:
      - ``operations``: ``{"op": "set", "key": <live key>,
        "properties": {"columns": <live-derived new_columns>}}`` — the
        columns ALWAYS come from re-running ``analyze_columns_component`` on
        the live component, never from the (possibly stale) plan row.
      - ``applied_rows``: ``{"path", "key", "before_columns", "new_columns"}``
        — ``before_columns`` is a deep copy of the live component's columns
        as found (pre-write); pairs with ``revert_operations``.
      - ``skipped``: ``{"path", "reason"}`` where reason is one of
        ``row_not_found`` (plan path absent live), ``duplicate_path`` (plan
        path resolves to more than one live component — ambiguous, so
        neither is touched), ``duplicate_key`` (the live component's ``key``
        is shared by another columns component elsewhere in the tree, so a
        key-addressed SET op would be ambiguous — skipped, not emitted),
        ``layout_changed`` (live verdict action no
        longer matches the plan row's action), or the live verdict's own
        skip reason (e.g. ``already_normalized``, ``over_12``, ``complete``,
        ... — including ``null_width``/``invalid_width``: unlike
        ``build_plan``, a single malformed live row is folded into
        ``skipped`` here rather than raising, so one anomalous row doesn't
        abort an otherwise-valid batch apply).

    Raises ``ValueError`` if ``live_components`` is not a list (e.g. a
    caller passed the whole form dict instead of ``form["components"]``).
    """
    _require_live_components_list(live_components)
    live_index = _build_live_index(live_components)
    key_counts = _live_key_counts(live_index)

    operations: list[dict[str, Any]] = []
    applied_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in plan_rows:
        if row.get("action") not in ("append", "resize"):
            continue
        path = row["path"]

        hits = live_index.get(path, [])
        if not hits:
            skipped.append({"path": path, "reason": "row_not_found"})
            continue
        if len(hits) > 1:
            skipped.append({"path": path, "reason": "duplicate_path"})
            continue
        live_component, live_grid_context = hits[0]

        live_key = live_component.get("key") or ""
        if key_counts.get(live_key, 0) > 1:
            skipped.append({"path": path, "reason": "duplicate_key"})
            continue

        verdict = analyze_columns_component(
            live_component, grid_context=live_grid_context
        )

        if verdict.action == "skip":
            skipped.append({"path": path, "reason": verdict.reason})
            continue

        if verdict.action != row.get("action"):
            skipped.append({"path": path, "reason": "layout_changed"})
            continue

        new_columns = copy.deepcopy(verdict.new_columns)
        before_columns = copy.deepcopy(live_component.get("columns") or [])

        operations.append(
            {
                "op": "set",
                "key": live_key,
                "properties": {"columns": copy.deepcopy(new_columns)},
            }
        )
        applied_rows.append(
            {
                "path": path,
                "key": live_key,
                "before_columns": before_columns,
                "new_columns": new_columns,
            }
        )

    return {
        "operations": operations,
        "applied_rows": applied_rows,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# revert_operations
# ---------------------------------------------------------------------------
def revert_operations(
    applied_rows: list[dict[str, Any]], live_components: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the CONDITIONAL restore operations for a previous apply.

    Pure — never mutates ``applied_rows``, ``live_components``, or anything
    reachable from them. For each applied row, restores ONLY when the live
    component's ``columns`` still deep-equal exactly ``row["new_columns"]``
    (i.e. nothing has touched the row since apply — a pristine match). This
    is never a blind restore: a row modified since apply is skipped as
    ``modified_since_apply`` rather than overwritten.

    Returns ``{"operations": [...], "skipped": [...]}`` where ``operations``
    entries are ``{"op": "set", "key": ..., "properties":
    {"columns": <before_columns>}}`` and ``skipped`` entries are
    ``{"path", "reason"}`` with reason ``row_not_found``, ``duplicate_path``
    (path resolves to more than one live component — ambiguous, so neither
    is restored), ``duplicate_key`` (the live key is shared by another
    columns component elsewhere in the tree), or ``modified_since_apply``.

    The restore op addresses the live component by the ``key`` captured at
    apply time. That addressing is unambiguous only when the key is unique
    in the live tree, so revert independently re-checks BOTH ambiguity
    kinds — ``duplicate_path`` (path resolves to >1 live component) and
    ``duplicate_key`` (the live key is shared elsewhere) — and skips either
    rather than restoring: path uniqueness alone does NOT imply key
    uniqueness.

    Raises ``ValueError`` if ``live_components`` is not a list (e.g. a
    caller passed the whole form dict instead of ``form["components"]``).
    """
    _require_live_components_list(live_components)
    live_index = _build_live_index(live_components)
    key_counts = _live_key_counts(live_index)

    operations: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in applied_rows:
        path = row["path"]
        hits = live_index.get(path, [])
        if not hits:
            skipped.append({"path": path, "reason": "row_not_found"})
            continue
        if len(hits) > 1:
            skipped.append({"path": path, "reason": "duplicate_path"})
            continue
        live_component, _grid_context = hits[0]

        live_key = live_component.get("key") or ""
        if key_counts.get(live_key, 0) > 1:
            skipped.append({"path": path, "reason": "duplicate_key"})
            continue

        live_columns = live_component.get("columns") or []
        if live_columns != row["new_columns"]:
            skipped.append({"path": path, "reason": "modified_since_apply"})
            continue

        operations.append(
            {
                "op": "set",
                "key": row["key"],
                "properties": {"columns": copy.deepcopy(row["before_columns"])},
            }
        )

    return {"operations": operations, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI (`python3 scripts/columns_apply.py`)
# ---------------------------------------------------------------------------
def _require_list_field(payload: Any, field: str) -> list[Any]:
    """Return ``payload[field]``, failing loud (ValueError) when the stdin
    payload isn't a JSON object or the field is missing / not an array.

    A missing or non-list key is never silently defaulted to ``[]``: an
    empty apply and a malformed payload must not look identical.
    """
    if not isinstance(payload, dict):
        raise ValueError(
            'stdin must be a JSON object with "plan_rows" and "live_components" arrays'
        )
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"stdin JSON object must have a {field!r} array")
    return value


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    """CLI seam: read ``{"plan_rows": [...], "live_components": [...]}`` as
    JSON on stdin, emit the JSON apply result on stdout.

    Fails loud (non-zero exit + explanatory stderr) on non-JSON input, a
    missing/non-list ``plan_rows`` or ``live_components``, or an unexpected
    component shape. Never emits a result on stdout for invalid input.
    """
    parser = argparse.ArgumentParser(
        prog="python3 scripts/columns_apply.py",
        description="Emit the live-re-verified form_patch SET operations for a "
        "columns normalization plan, reading "
        '{"plan_rows": [...], "live_components": [...]} as JSON on stdin.',
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the payload JSON from stdin (default behaviour).",
    )
    parser.parse_args(argv)

    if stdin_text is None:
        stdin_text = sys.stdin.read()

    try:
        payload = json.loads(stdin_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"error: invalid JSON on stdin: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    try:
        plan_rows = _require_list_field(payload, "plan_rows")
        live_components = _require_list_field(payload, "live_components")
        result = plan_to_operations(plan_rows, live_components)
    except (ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
