"""Pure logic for over-12 columns "split-APPLY" OPERATIONS: transform a
``columns_split.scan_form_for_splits`` split PLAN plus a freshly-fetched live
form's component list into the ``form_patch`` remove+add operations a skill
session would send to replace an over-12 columns component with N 12-sum
containers in its exact slot. Spec: TOBE-18009 (split-detection), apply phase.

IMPORTANT — placement / invariants:
  - This is a SEPARATE, ADDITIVE module. It must NEVER change the behaviour
    of ``columns_logic.analyze_columns_component``, ``columns_split.plan_split``,
    or ``columns_apply.plan_to_operations`` — this module only adds a new,
    independent capability alongside them.
  - This is a stdlib-only script bundled in the columns-normalization-migration
    skill, invoked by CLI, exactly like ``columns_logic.py`` /
    ``columns_split.py`` / ``columns_apply.py``.
  - It must remain STDLIB-ONLY (no third-party dependencies), plus intra-
    package reuse of ``columns_logic`` (the tree walker + grid constant) and
    ``columns_split`` (``plan_split``, re-run live) — no other ``tools`` or
    ``BPAClient`` imports, and no import of ``columns_apply`` (a sibling, not
    a dependency).
  - READ-ONLY / NO WRITES: this module never calls ``form_patch`` and never
    mutates a form or a component. It only computes the operations a caller
    (the skill session) would send. It never registers an MCP tool.
  - SCAN-DERIVED: the plan rows this module consumes come from
    ``columns_split.scan_form_for_splits`` — a read-only detection pass. This
    module never re-derives the split boundary itself; it re-runs
    ``plan_split`` on the LIVE component and trusts that verdict.

LAST-WRITE-WINS SAFETY (why re-verification, not blind apply):
  A split plan is built from a form snapshot that may be stale by the time a
  skill session is ready to write — another designer may have edited the
  form in between. Since BPA's ``form_patch`` is last-write-wins (it
  overwrites whatever is live, not a merge), applying a stale plan verbatim
  could silently clobber a concurrent edit or split a row that no longer
  needs it. So ``plan_to_split_operations`` re-walks the LIVE component tree
  and re-runs ``columns_split.plan_split`` on the live component right before
  building each row's operations, and only proceeds when the live component
  is still an over-12 splittable row. The emitted containers are always the
  LIVE-derived ``plan_split(...)["containers"]`` — never the plan row's
  (possibly stale) snapshot — so a live width change since the plan was built
  is reflected in what gets written, not silently overridden.

  ``revert_split_operations`` mirrors this caution: it restores a row's
  original columns component only when every one of its N written containers
  still exists, unmodified, in the live tree (i.e. nothing has touched the
  split since apply) — never a blind restore.

DETERMINANT / VISIBILITY HANDLING (behaviourId-sourced rows carry a descriptor):
  Splitting a columns component means the ONE original component becomes N
  new components. A BPA-managed behaviour (visibility driven by a
  ``behaviourId``/``effectsIds``/``determinantIds`` chain) targets the single
  original key; replicating it correctly onto N new keys is an API operation
  (behaviour-clone via ``componentbehaviour_generate_newkeys``), not something
  this pure module performs — and that clone needs a source ``behaviourId``
  to clone FROM. So EVERY row splits structurally regardless of any managed
  chain (emit the ``remove`` + N ``add`` ops, carry its inline conditionals —
  see below); but the ``applied_rows`` entry gains a
  ``determinant_replication`` descriptor ONLY when the live original
  component carries a non-empty ``behaviourId`` — the descriptor's actual
  clone source. A row managed ONLY via ``determinantIds``/``effectsIds`` (no
  ``behaviourId``) has no clone source, so it gets NO descriptor: it splits
  structurally like any other unmanaged row, and no clone is attempted (per
  Erick's "handle source_behaviour_id is None explicitly", comment 102512) —
  avoiding a spurious ``SOURCE_NOT_FOUND`` clone failure downstream in the
  skill. When present, the descriptor is what the SKILL executes after the
  write by calling ``componentbehaviour_generate_newkeys`` (PR #458) ONCE PER
  new container key (the endpoint is 1→1: one call clones the source
  behaviour onto ONE new key). All N containers thereby inherit the source's
  condition. The module makes NO API calls — the descriptor is derived purely
  from the live component already in scope. A row with no ``behaviourId``
  carries ``determinant_replication: None``.

  ORPHANED SOURCE BEHAVIOUR (tracked debt): the structural ``remove`` of the
  original component leaves its managed behaviour orphaned-but-intact. Per
  Erick's decision it is LEFT in place — revert re-binds it by re-adding the
  original key, so no behaviour recreation is needed in the module or the
  revert. But it is invisible to ``recover_orphaned_config`` (which only
  detects forward orphans), so the SKILL records the orphaned source
  behaviourId as tracked debt; the migration is not gated on its cleanup.

  For everything else, EVERY new container is built as a DEEP COPY of the
  live original component (see CONTAINER CONSTRUCTION below), so inline
  Form.io visibility fields — ``conditional``, ``customConditional``,
  ``logic``, ``hidden`` — (and every other authored property:
  ``registrations``, ``customClass``, ``customClasses``, ``activate``,
  ``tableView``, ...) come along automatically, verbatim, onto EVERY new
  container. This is a mechanical carry, not a redesign: all N containers
  become visible/hidden together, and keep every other authored property,
  exactly as the single original component was.

CONTAINER CONSTRUCTION (deep-copy blacklist, not a field whitelist):
  Each of the N new containers is built as an independent
  ``copy.deepcopy`` of the live original component — never a hand-picked
  subset of fields — so nothing authored on the original is silently
  dropped. Only ``key`` and ``columns`` are then overridden (to the split
  container's own key and its column subset, incl. any padded filler), and
  only the fields in ``_CONTAINER_IDENTITY_FIELDS_TO_CLEAR`` — ``id``,
  ``behaviourId``, ``effectsIds``, ``componentActionId``,
  ``componentFormulaId``, ``componentValidationId``, ``actionRowIds``,
  ``formulaRowIds`` — are then cleared (popped): the identity / 1:1-binding
  fields the split handles explicitly. A fresh container has no platform
  ``id`` yet; clearing ``behaviourId``/``effectsIds`` is exactly what leaves
  a managed container with no behaviour pointer, so the SKILL (PR #448) can
  write the cloned behaviour id back after ``generate_newkeys``. The other
  cleared fields are OTHER 1:1 binding pointers (action/formula/validation
  component ids, action/formula row id lists) that would otherwise ride the
  deepcopy unchanged and be silently SHARED across all N containers if ever
  set on a columns component — cleared defensively even though zero-instance
  on live data today (Erick, comment 102512). ``determinantIds`` is
  deliberately NOT cleared here — out of scope, tracked separately. Every
  other field — including ``conditional``/``customConditional``/``logic``/
  ``hidden`` — is kept verbatim, which subsumes the old explicit inline-
  visibility-carry mechanism; there is one source of truth (the deep copy),
  not two. Each container's deep copy is independent (no shared references
  across containers, and ``live_components`` is never mutated).

PARENT-CONTEXT RESOLUTION (conservative; a pure-Python read-only walk):
  This module re-implements, in stdlib-only Python, the read-only portion of
  what ``formio_helpers.find_component_parent`` / ``insert_component`` do at
  write time: locate the live original component's parent and position so
  the emitted ``add`` ops carry the right ``parent_key``/``position``（+
  ``column_index`` when the parent is itself a ``columns`` component). Only
  three contexts are supported: form root, a plain container parent
  (``panel``/``well``/``container``/``fieldset`` holding children directly in
  its own ``components`` list), and a columns parent (nested inside another
  columns component's column). Anything else — tabs, table, datagrid/
  editgrid, or any component found ANYWHERE beneath such an ancestor (not
  just as its direct child) — is skipped ``unsupported_parent_context``. A
  wrong structural op is far worse than a skip.

  A keyless (``key`` missing/empty) intermediate container or columns
  parent is likewise skipped ``unsupported_parent_context`` rather than
  treated as the form root: only the ACTUAL form root (the target sitting
  directly in the top-level ``live_components`` list) legitimately omits
  ``parent_key`` — a non-root parent that has no addressable ``key`` is
  unaddressable, not root, and lifting its child to root would be a wrong
  structural op.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any

from columns_logic import (
    GRID_TYPES,
    iter_columns_components,
)
from columns_split import plan_split

_PLAIN_CONTAINER_TYPES = frozenset({"panel", "well", "container", "fieldset"})
# Identity / 1:1-binding fields cleared on every deep-copied container: a
# fresh container has no platform `id` yet; clearing `behaviourId`/
# `effectsIds` is exactly what lets the skill re-attach a cloned behaviour
# after `generate_newkeys`. The remaining fields are other 1:1 binding
# pointers (action/formula/validation component ids, action/formula row id
# lists) that would otherwise ride the deepcopy unchanged and be shared
# across all N containers if ever set on a columns component -- cleared
# defensively, zero-instance on live data today (Erick, comment 102512). Do
# NOT add `determinantIds` here -- out of scope, tracked separately. See
# CONTAINER CONSTRUCTION in the module docstring.
_CONTAINER_IDENTITY_FIELDS_TO_CLEAR = (
    "id",
    "behaviourId",
    "effectsIds",
    "componentActionId",
    "componentFormulaId",
    "componentValidationId",
    "actionRowIds",
    "formulaRowIds",
)


def _require_live_components_list(live_components: Any) -> None:
    """Fail loud when ``live_components`` isn't a list — e.g. a caller
    passed the whole form dict instead of ``form["components"]``. Mirrors
    ``columns_apply``'s fail-loud shape check instead of silently walking
    nothing and reporting every row ``row_not_found``.
    """
    if not isinstance(live_components, list):
        raise ValueError("live_components must be a list of Form.io components")


# ---------------------------------------------------------------------------
# live indices (path -> hits, key -> hits, full-tree key set)
# ---------------------------------------------------------------------------
def _build_live_path_index(
    live_components: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index every live columns component by walker path, built ONCE per
    call. Walker paths are not guaranteed unique (e.g. two sibling panels
    sharing a key, each containing a same-keyed columns component, both
    resolve to the same path) — so each path maps to a LIST of hits.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for hit in iter_columns_components(live_components):
        index.setdefault(hit.path, []).append(hit.component)
    return index


def _live_columns_by_key(
    live_components: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index every live columns component by ``key`` (used by revert to
    locate previously-written containers by their key)."""
    index: dict[str, list[dict[str, Any]]] = {}
    for hit in iter_columns_components(live_components):
        key = hit.component.get("key") or ""
        if key:
            index.setdefault(key, []).append(hit.component)
    return index


def _iter_all_components(
    components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten every component dict anywhere in the tree (not just columns
    hits) — components/columns[].components/tabs[].components/rows[][].cells.
    Used only to build a full key set for collision checks; local to this
    module rather than shared with ``columns_logic``'s walker, which is
    columns-hit-specific."""
    result: list[dict[str, Any]] = []
    for node in components:
        if not isinstance(node, dict):
            continue
        result.append(node)
        children = node.get("components")
        if isinstance(children, list):
            result.extend(_iter_all_components(children))
        cols = node.get("columns")
        if isinstance(cols, list):
            for col in cols:
                if isinstance(col, dict):
                    result.extend(_iter_all_components(col.get("components") or []))
        panes = node.get("tabs")
        if isinstance(panes, list):
            for pane in panes:
                if isinstance(pane, dict):
                    result.extend(_iter_all_components(pane.get("components") or []))
        rows = node.get("rows")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    for cell in row:
                        if isinstance(cell, dict):
                            result.extend(
                                _iter_all_components(cell.get("components") or [])
                            )
    return result


def _all_component_key_counts(
    live_components: list[dict[str, Any]],
) -> dict[str, int]:
    """Count every non-empty ``key`` anywhere in the tree, across ALL
    component types (not just columns components).

    A ``remove``/``add`` op addresses a component by ``key``, and a
    ``remove`` resolves to the first DFS component of ANY type with that
    key — so the ``duplicate_key`` ambiguity guard (and the
    ``container_key_collision`` check) must be computed over the WHOLE
    tree, not just columns hits: a live key colliding with a same-keyed
    ``textfield`` elsewhere is just as ambiguous/unsafe as colliding with
    another columns component.
    """
    counts: dict[str, int] = {}
    for node in _iter_all_components(live_components):
        key = node.get("key")
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


def _all_component_keys(live_components: list[dict[str, Any]]) -> set[str]:
    """Every non-empty ``key`` anywhere in the tree — used to detect a
    proposed new container key colliding with ANY existing component, not
    just other columns components."""
    return set(_all_component_key_counts(live_components))


# ---------------------------------------------------------------------------
# parent-context resolution (read-only mirror of formio_helpers addressing)
# ---------------------------------------------------------------------------
def _contains(components: list[dict[str, Any]], target: dict[str, Any]) -> bool:
    """True if ``target`` (by identity) appears ANYWHERE in ``components`` or
    its descendants. Used to classify an entire subtree beneath an
    unsupported ancestor (tabs pane / table cell / grid / unknown container)
    as unsupported regardless of depth — a component nested several levels
    under such an ancestor is still unsupported, not just a DIRECT child of
    it."""
    for node in components:
        if node is target:
            return True
        if not isinstance(node, dict):
            continue
        children = node.get("components")
        if isinstance(children, list) and _contains(children, target):
            return True
        cols = node.get("columns")
        if isinstance(cols, list):
            for col in cols:
                if isinstance(col, dict) and _contains(
                    col.get("components") or [], target
                ):
                    return True
        panes = node.get("tabs")
        if isinstance(panes, list):
            for pane in panes:
                if isinstance(pane, dict) and _contains(
                    pane.get("components") or [], target
                ):
                    return True
        rows = node.get("rows")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    for cell in row:
                        if isinstance(cell, dict) and _contains(
                            cell.get("components") or [], target
                        ):
                            return True
    return False


def _search_descendants(
    components: list[dict[str, Any]], target: dict[str, Any]
) -> dict[str, Any] | None:
    """Recursive descent used by ``_find_parent_context``. Only two parent
    KINDS are ever returned as supported: "container" (plain panel/well/
    container/fieldset) and "columns" (nested inside another columns
    component's column) — matched at whichever level DIRECTLY holds
    ``target``. Anything reachable only through a tabs pane, table cell,
    datagrid/editgrid, or an unrecognised container type is "unsupported",
    even when ``target`` sits several levels deeper inside a supported
    container that is itself nested under one of those — being ANYWHERE
    beneath such an ancestor is disqualifying, not just being its direct
    child.

    A DIRECT parent (container or columns) whose own ``key`` is missing/
    empty is ALSO "unsupported": it is a non-root, unaddressable container
    (an ``add`` op needs a ``parent_key`` to target it), which is a
    different case from the true form root (the only context that
    legitimately has no ``parent_key`` at all — handled by
    ``_find_parent_context``, not here). Treating a keyless intermediate
    parent as if it were root would silently lift the child to the form
    root, which is a wrong structural op — skip instead.
    """
    for node in components:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        key = node.get("key")

        if node_type in _PLAIN_CONTAINER_TYPES:
            children = node.get("components")
            if isinstance(children, list):
                for i, child in enumerate(children):
                    if child is target:
                        if not key:
                            return {"kind": "unsupported"}
                        return {"kind": "container", "parent_key": key, "position": i}
                found = _search_descendants(children, target)
                if found is not None:
                    return found

        elif node_type == "columns":
            cols = node.get("columns")
            if isinstance(cols, list):
                for ci, col in enumerate(cols):
                    if not isinstance(col, dict):
                        continue
                    col_children = col.get("components")
                    if isinstance(col_children, list):
                        for i, child in enumerate(col_children):
                            if child is target:
                                if not key:
                                    return {"kind": "unsupported"}
                                return {
                                    "kind": "columns",
                                    "parent_key": key,
                                    "column_index": ci,
                                    "position": i,
                                }
                        found = _search_descendants(col_children, target)
                        if found is not None:
                            return found

        elif node_type == "tabs":
            panes = node.get("tabs")
            if isinstance(panes, list):
                for pane in panes:
                    if isinstance(pane, dict) and _contains(
                        pane.get("components") or [], target
                    ):
                        return {"kind": "unsupported"}

        elif node_type == "table":
            rows = node.get("rows")
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, list):
                        continue
                    for cell in row:
                        if isinstance(cell, dict) and _contains(
                            cell.get("components") or [], target
                        ):
                            return {"kind": "unsupported"}

        elif node_type in GRID_TYPES:
            children = node.get("components")
            if isinstance(children, list) and _contains(children, target):
                return {"kind": "unsupported"}

        else:
            # Unrecognised container-ish type: still may nest components; be
            # conservative and treat any match beneath it as unsupported.
            children = node.get("components")
            if isinstance(children, list) and _contains(children, target):
                return {"kind": "unsupported"}

    return None


def _find_parent_context(
    live_components: list[dict[str, Any]], target: dict[str, Any]
) -> dict[str, Any] | None:
    """Locate ``target``'s parent context in ``live_components``.

    Returns ``{"kind": "root", "position": i}``,
    ``{"kind": "container", "parent_key": ..., "position": i}``,
    ``{"kind": "columns", "parent_key": ..., "column_index": ci, "position": i}``,
    ``{"kind": "unsupported"}``, or ``None`` if ``target`` isn't found at all
    (defensive; treated the same as "unsupported" by callers).
    """
    for i, node in enumerate(live_components):
        if node is target:
            return {"kind": "root", "position": i}
    return _search_descendants(live_components, target)


def _is_structurally_pristine(live: dict[str, Any], written: dict[str, Any]) -> bool:
    """True when ``live`` matches ``written`` on the fields a designer edit
    would actually change: ``key``, ``type``, and the ``columns`` array
    (widths + each column's ``components``), deep-equal.

    Full-dict ``==`` is too strict here: ``form_patch add`` into a columns
    parent routes through ``insert_component``, which injects default keys
    (``determinantIds``, ``version``, ``tableView``, ...) onto the live
    container, so it is always a strict SUPERSET of the minimal emitted
    payload and never deep-equals it. Comparing only the structural fields
    means injected defaults alone are pristine, while a designer adding,
    removing, or reordering columns — or editing a child field somewhere in
    ``columns`` — still correctly trips ``modified_since_apply``.
    """
    if live.get("key") != written.get("key"):
        return False
    if live.get("type") != written.get("type"):
        return False
    return live.get("columns") == written.get("columns")


# ---------------------------------------------------------------------------
# plan_to_split_operations
# ---------------------------------------------------------------------------
def plan_to_split_operations(
    plan_rows: list[dict[str, Any]], live_components: list[dict[str, Any]]
) -> dict[str, Any]:
    """Transform ``scan_form_for_splits`` plan rows into live-re-verified
    ``form_patch`` remove+add operations.

    Pure — never mutates ``plan_rows``, ``live_components``, or anything
    reachable from them. Only rows whose plan ``action`` is ``"split"`` are
    considered; any other row is ignored entirely (never appears in
    ``operations``, ``applied_rows``, or ``skipped``).

    Two internal passes:

      PASS 1 (resolve) — for each considered row:
        1. Resolve the row's ``path`` against a live path index built once
           from ``iter_columns_components``. 0 hits -> skip
           ``row_not_found``; more than 1 -> skip ``duplicate_path``.
        2. The live component's ``key`` appearing more than once anywhere in
           the WHOLE tree (any component type, not just columns) -> skip
           ``duplicate_key`` (a key-addressed ``remove`` would be ambiguous:
           it resolves to the first DFS component of ANY type sharing that
           key).
        3. Re-run ``columns_split.plan_split`` on the LIVE component.
           ``None`` (no longer an over-12 splittable row: widths changed,
           now sums to 12 or under, etc.) -> skip ``layout_changed``.
           Otherwise the LIVE plan's ``containers`` are used — never the
           plan row's own (possibly stale) ``containers`` snapshot.
        4. Every row splits structurally regardless of any managed
           behaviour chain (``behaviourId``/``effectsIds``/``determinantIds``
           never skips a row). A non-empty ``behaviourId`` on the live
           original component is what gates the ``applied_rows`` entry
           gaining a ``determinant_replication`` descriptor (see below) the
           skill executes after the write — a row managed only via
           ``determinantIds``/``effectsIds`` (no ``behaviourId``) has no
           clone source and gets no descriptor. Independently, inline
           ``conditional``/``customConditional``/``logic``/``hidden``
           (whichever are truthy) are copied verbatim onto every new
           container regardless.
        5. Resolve the live original component's parent context (form root,
           a plain container, or a columns parent) via a pure-Python
           read-only walk. Anything else (tabs, table, datagrid/editgrid, a
           component found anywhere beneath such an ancestor, or a DIRECT
           non-root container/columns parent whose own ``key`` is missing/
           empty and therefore unaddressable) -> skip
           ``unsupported_parent_context``. Only the true form root
           legitimately omits ``parent_key``.
        6. Any proposed container key already existing anywhere in
           ``live_components`` -> skip the row ``container_key_collision``.
        Survivors are collected (not yet emitted) with their resolved
        context (``parent_key``, ``column_index``, ``base_position``) and
        live-derived containers/payloads.

      PASS 2 (emit, per-sibling-list offset accounting) — survivors are
        grouped by sibling-list key ``(parent_key, column_index)``. Within
        each group, rows are processed in ASCENDING ``base_position`` order
        with a running offset carried forward: the first row in a group
        emits its adds at ``base_position + n``; the offset then advances by
        ``len(containers) - 1`` (one ``remove``, N ``add`` — the sibling
        list's net length change); the next row in the SAME group emits its
        adds at ``base_position + running_offset + n``. This is necessary
        because ``form_patch`` applies every op in list order onto ONE
        working copy: a second split in the same sibling list would
        otherwise land at a stale (too-early, pre-batch) position and
        interleave into the first split's newly-inserted containers. A
        sibling list with only one surviving row is unaffected (offset
        stays 0), so all existing single-row behaviour is unchanged.
        Cross-group emission order is unspecified (groups don't interact).

    Returns ``{"operations": [...], "applied_rows": [...], "skipped": [...]}``:
      - ``applied_rows``: one entry per successfully-split row —
        ``{"path", "original_key", "original_component" (deep copy of the
        live component pre-split), "container_keys" (the N new keys),
        "written_containers" (deep copies of the exact component dicts
        written), "parent_key", "column_index", "position",
        "determinant_replication"}`` (``parent_key``/``column_index`` are
        ``None`` when not applicable) — pairs with
        ``revert_split_operations``. ``determinant_replication`` is ``None``
        unless the live original component carries a non-empty
        ``behaviourId``; when it does, it is
        ``{"source_key", "target_keys" (== ``container_keys``),
        "source_behaviour_id" (always truthy here), "target_behaviour_ids": {}}``
        — the skill fills ``target_behaviour_ids`` (one clone id per target
        key) when it calls ``componentbehaviour_generate_newkeys`` after the
        write, and uses them to delete the replicated behaviours on revert.
        A row managed only via ``determinantIds``/``effectsIds`` (no
        ``behaviourId``) has no clone source, so it also carries
        ``determinant_replication: None``.
      - ``skipped``: ``{"path", "original_key", "reason"}`` — see the reasons
        listed above.

    Raises ``ValueError`` if ``live_components`` is not a list (e.g. a caller
    passed the whole form dict instead of ``form["components"]``).
    """
    _require_live_components_list(live_components)
    path_index = _build_live_path_index(live_components)
    all_key_counts = _all_component_key_counts(live_components)
    all_keys = set(all_key_counts)

    skipped: list[dict[str, Any]] = []

    # ---- pass 1: resolve ---------------------------------------------
    # Do all locate/re-verify/skip logic and, for survivors, compute the
    # parent context, the live containers, and the emitted component
    # payloads — but don't decide final positions or emit ops yet. Final
    # positions depend on sibling-list offsets that can only be computed
    # once every row in the batch has been resolved (pass 2).
    survivors: list[dict[str, Any]] = []

    for row in plan_rows:
        if row.get("action") != "split":
            continue
        path: str = row["path"]
        original_key = row.get("original_key")

        hits = path_index.get(path, [])
        if not hits:
            skipped.append(
                {"path": path, "original_key": original_key, "reason": "row_not_found"}
            )
            continue
        if len(hits) > 1:
            skipped.append(
                {"path": path, "original_key": original_key, "reason": "duplicate_path"}
            )
            continue
        live_component = hits[0]

        live_key = live_component.get("key") or ""
        # Finding 2: a `remove` op is key-addressed across ALL component
        # types, so the ambiguity guard must count keys over the WHOLE
        # tree, not just other columns components.
        if all_key_counts.get(live_key, 0) > 1:
            skipped.append(
                {"path": path, "original_key": original_key, "reason": "duplicate_key"}
            )
            continue

        live_plan = plan_split(live_component)
        if live_plan is None:
            skipped.append(
                {"path": path, "original_key": original_key, "reason": "layout_changed"}
            )
            continue
        live_containers = live_plan["containers"]

        # Fix (Erick, comment 102512): "handle source_behaviour_id is None
        # explicitly". The determinant_replication descriptor exists only to
        # drive componentbehaviour_generate_newkeys, which clones a source
        # behaviourId onto each new key -- with no behaviourId there is
        # nothing to clone FROM. So gate the descriptor on a REAL
        # behaviourId, not on the broader managed-chain check
        # (behaviourId/effectsIds/determinantIds): a row managed ONLY via
        # determinantIds/effectsIds (no behaviourId) still splits
        # structurally like any other row, just with no descriptor and no
        # clone attempted -- avoiding a spurious SOURCE_NOT_FOUND clone
        # failure downstream in the skill. Read BEFORE the deep-copy (in
        # pass 2) clears `behaviourId` on the containers -- the descriptor
        # must carry the SOURCE's id. Inline conditionals are independent of
        # this and still carried below regardless.
        source_behaviour_id = live_component.get("behaviourId") or None
        is_managed = source_behaviour_id is not None

        context = _find_parent_context(live_components, live_component)
        if context is None or context["kind"] == "unsupported":
            skipped.append(
                {
                    "path": path,
                    "original_key": original_key,
                    "reason": "unsupported_parent_context",
                }
            )
            continue

        proposed_keys = [container["key"] for container in live_containers]
        if any(key in all_keys for key in proposed_keys):
            skipped.append(
                {
                    "path": path,
                    "original_key": original_key,
                    "reason": "container_key_collision",
                }
            )
            continue

        survivors.append(
            {
                "path": path,
                "live_key": live_key,
                "original_component": copy.deepcopy(live_component),
                "live_containers": live_containers,
                "is_managed": is_managed,
                "source_behaviour_id": source_behaviour_id,
                "parent_key": context.get("parent_key"),
                "column_index": context.get("column_index"),
                "base_position": context["position"],
                "container_keys": proposed_keys,
            }
        )

    # ---- pass 2: emit, with per-sibling-list offset accounting --------
    # Finding 1: `form_patch` applies ops in list order onto ONE working
    # copy, and each split changes its own sibling list's length by
    # +(len(containers) - 1) (one remove, N adds). Positions computed
    # from the static pre-batch tree go stale for a SECOND row in the
    # same sibling list once the first row's ops have been replayed. Fix:
    # group survivors by sibling-list key (parent_key, column_index),
    # process each group in ascending original-position order, and carry
    # a running offset forward within the group so later rows land AFTER
    # earlier rows' newly-inserted containers instead of interleaving.
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    group_order: list[tuple[Any, Any]] = []
    for survivor in survivors:
        group_key = (survivor["parent_key"], survivor["column_index"])
        if group_key not in groups:
            groups[group_key] = []
            group_order.append(group_key)
        groups[group_key].append(survivor)

    operations: list[dict[str, Any]] = []
    applied_rows: list[dict[str, Any]] = []

    for group_key in group_order:
        group_survivors = sorted(groups[group_key], key=lambda s: s["base_position"])
        running_offset = 0
        for survivor in group_survivors:
            live_key = survivor["live_key"]
            live_containers = survivor["live_containers"]
            original_component = survivor["original_component"]
            parent_key = survivor["parent_key"]
            column_index = survivor["column_index"]
            adjusted_base = survivor["base_position"] + running_offset

            row_operations: list[dict[str, Any]] = [{"op": "remove", "key": live_key}]
            written_containers: list[dict[str, Any]] = []
            for n, container in enumerate(live_containers):
                # Deep-copy BLACKLIST (not a field whitelist): start from a
                # full, independent deep copy of the live original component
                # so every authored property (`registrations`, `customClass`,
                # `customClasses`, `activate`, `tableView`, inline
                # visibility, ...) is preserved verbatim. Only override the
                # two fields the split changes, and clear only the
                # identity/1:1-binding fields the split handles explicitly
                # (see _CONTAINER_IDENTITY_FIELDS_TO_CLEAR).
                new_component: dict[str, Any] = copy.deepcopy(original_component)
                new_component["key"] = container["key"]
                new_component["columns"] = copy.deepcopy(container["columns"])
                for identity_field in _CONTAINER_IDENTITY_FIELDS_TO_CLEAR:
                    new_component.pop(identity_field, None)
                add_op: dict[str, Any] = {
                    "op": "add",
                    "component": new_component,
                    "position": adjusted_base + n,
                }
                if parent_key is not None:
                    add_op["parent_key"] = parent_key
                if column_index is not None:
                    add_op["column_index"] = column_index
                row_operations.append(add_op)
                written_containers.append(copy.deepcopy(new_component))

            # Managed rows carry a `determinant_replication` descriptor the
            # skill executes AFTER this structural write, cloning the source
            # behaviour onto each new container key (1 call per key). Kept
            # PURE: derived only from the live component already in scope.
            if survivor["is_managed"]:
                determinant_replication: dict[str, Any] | None = {
                    "source_key": live_key,
                    "target_keys": list(survivor["container_keys"]),
                    "source_behaviour_id": survivor["source_behaviour_id"],
                    # filled in by the SKILL after it calls generate_newkeys,
                    # one per target key:
                    "target_behaviour_ids": {},
                }
            else:
                determinant_replication = None

            operations.extend(row_operations)
            applied_rows.append(
                {
                    "path": survivor["path"],
                    "original_key": live_key,
                    "original_component": survivor["original_component"],
                    "container_keys": survivor["container_keys"],
                    "written_containers": written_containers,
                    "parent_key": parent_key,
                    "column_index": column_index,
                    "position": adjusted_base,
                    "determinant_replication": determinant_replication,
                }
            )

            running_offset += len(live_containers) - 1

    return {
        "operations": operations,
        "applied_rows": applied_rows,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# revert_split_operations
# ---------------------------------------------------------------------------
def revert_split_operations(
    applied_rows: list[dict[str, Any]], live_components: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the CONDITIONAL restore operations for a previous split apply.

    Pure — never mutates ``applied_rows``, ``live_components``, or anything
    reachable from them. For each applied row, restores ONLY when every one
    of its recorded ``container_keys`` still resolves to EXACTLY ONE live
    columns component that is STRUCTURALLY PRISTINE relative to the
    corresponding recorded ``written_containers`` entry — same ``key``,
    ``type``, and ``columns`` array (see ``_is_structurally_pristine``).

    The STRUCTURAL revert is unchanged for managed rows: re-adding the
    original key re-binds its intact orphaned source behaviour automatically,
    so no behaviour recreation happens here. This function ignores the
    ``determinant_replication`` field entirely — the skill handles deleting
    the replicated behaviours on the new keys (using
    ``target_behaviour_ids``) BEFORE invoking this structural revert.
    This is a subset comparison, not full-dict equality: ``form_patch add``
    into a columns parent routes through ``insert_component``, which injects
    platform default keys (``determinantIds``, ``version``, ``tableView``,
    ...) onto the live container, so the live dict is always a strict
    superset of what was written and would never full-dict-equal it. A
    missing container, a container key that has become ambiguous (now
    shared by more than one live component), or a container whose ``key``/
    ``type``/``columns`` has changed are all folded into the same
    ``modified_since_apply`` skip — never a blind restore.

    Returns ``{"operations": [...], "skipped": [...]}`` where a clean row
    emits N ``{"op": "remove", "key": <container key>}`` operations (one per
    container) followed by one ``{"op": "add", "component": <the deep-copied
    original component snapshot>, "position": <recorded position>, ...}`` —
    ``parent_key``/``column_index`` are included exactly as recorded by
    ``plan_to_split_operations`` (omitted when not applicable) — to restore
    the original component to its exact original slot. ``skipped`` entries
    are ``{"path", "original_key", "reason": "modified_since_apply"}``.

    Raises ``ValueError`` if ``live_components`` is not a list (e.g. a caller
    passed the whole form dict instead of ``form["components"]``), or if an
    applied row's ``container_keys`` and ``written_containers`` differ in
    length (a corrupt row: verifying only a prefix could emit a blind
    restore over containers that were never checked).
    """
    _require_live_components_list(live_components)
    key_index = _live_columns_by_key(live_components)

    # Length equality is a SAFETY invariant, not a formality: if
    # written_containers were shorter than container_keys, the verification
    # loop below would silently check only a prefix, leave `pristine` True,
    # and emit a blind restore over containers it never verified.
    #
    # Validated as a PRE-PASS over every row, before a single operation is
    # emitted, for two reasons. (1) It reports ALL corrupt rows at once --
    # an operator recovering from a bad apply should not fix row 2, re-run,
    # and only then discover row 5; this is the recovery path, so its
    # ergonomics matter most exactly when things are already going wrong.
    # (2) It is checked up front rather than via zip(strict=True) inside the
    # loop, which is BOTH a 3.9-compatibility fix (`strict=` is 3.10+, and
    # `python3` is still 3.9 on stock macOS -- see SKILL.md) AND a strictly
    # stronger guard: the loop `break`s on the first non-pristine container,
    # and zip(strict=True) only raises when it advances past an exhausted
    # iterator, so a corrupt row whose FIRST container was already
    # non-pristine used to break out before `strict` ever fired and got
    # silently downgraded to a `modified_since_apply` skip.
    corrupt = [
        (
            row["original_key"],
            len(row["container_keys"]),
            len(row["written_containers"]),
        )
        for row in applied_rows
        if len(row["container_keys"]) != len(row["written_containers"])
    ]
    if corrupt:
        detail = "; ".join(
            f"{key!r}: container_keys ({n_keys}) != written_containers ({n_written})"
            for key, n_keys, n_written in corrupt
        )
        raise ValueError(
            f"{len(corrupt)} applied row(s) corrupt -- container_keys and "
            f"written_containers must have the same length: {detail}"
        )

    operations: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in applied_rows:
        path = row["path"]
        original_key = row["original_key"]
        container_keys = row["container_keys"]
        written_containers = row["written_containers"]

        pristine = True
        for container_key, expected in zip(container_keys, written_containers):
            hits = key_index.get(container_key, [])
            if len(hits) != 1 or not _is_structurally_pristine(hits[0], expected):
                pristine = False
                break

        if not pristine:
            skipped.append(
                {
                    "path": path,
                    "original_key": original_key,
                    "reason": "modified_since_apply",
                }
            )
            continue

        for container_key in container_keys:
            operations.append({"op": "remove", "key": container_key})

        add_op: dict[str, Any] = {
            "op": "add",
            "component": copy.deepcopy(row["original_component"]),
            "position": row["position"],
        }
        if row.get("parent_key") is not None:
            add_op["parent_key"] = row["parent_key"]
        if row.get("column_index") is not None:
            add_op["column_index"] = row["column_index"]
        operations.append(add_op)

    return {"operations": operations, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI (`python3 scripts/columns_split_apply.py`)
# ---------------------------------------------------------------------------
def _require_list_field(payload: Any, field: str) -> list[Any]:
    """Return ``payload[field]``, failing loud (ValueError) when the stdin
    payload isn't a JSON object or the field is missing / not an array.

    A missing or non-list key is never silently defaulted to ``[]``: an
    empty apply and a malformed payload must not look identical.
    """
    if not isinstance(payload, dict):
        raise ValueError(
            "stdin must be a JSON object with the required arrays "
            '("plan_rows" + "live_components", or "applied_rows" + '
            '"live_components" with --revert)'
        )
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"stdin JSON object must have a {field!r} array")
    return value


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    """CLI seam: read the payload as JSON on stdin, emit the JSON result on
    stdout.

    Default (apply) reads ``{"plan_rows": [...], "live_components": [...]}``
    and runs ``plan_to_split_operations``. With ``--revert`` it reads
    ``{"applied_rows": [...], "live_components": [...]}`` and runs
    ``revert_split_operations``.

    Fails loud (non-zero exit + explanatory stderr) on non-JSON input, a
    missing/non-list required array, or an unexpected component shape. Never
    emits a result on stdout for invalid input.
    """
    parser = argparse.ArgumentParser(
        prog="python3 scripts/columns_split_apply.py",
        description="Emit the live-re-verified form_patch remove+add "
        "operations for an over-12 columns split plan, reading "
        '{"plan_rows": [...], "live_components": [...]} as JSON on stdin.',
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the payload JSON from stdin (default behaviour).",
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Compute the conditional restore operations instead, reading "
        '{"applied_rows": [...], "live_components": [...]}.',
    )
    args = parser.parse_args(argv)

    if stdin_text is None:
        stdin_text = sys.stdin.read()

    try:
        payload = json.loads(stdin_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"error: invalid JSON on stdin: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    try:
        if args.revert:
            applied_rows = _require_list_field(payload, "applied_rows")
            live_components = _require_list_field(payload, "live_components")
            result = revert_split_operations(applied_rows, live_components)
        else:
            plan_rows = _require_list_field(payload, "plan_rows")
            live_components = _require_list_field(payload, "live_components")
            result = plan_to_split_operations(plan_rows, live_components)
    except (ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
