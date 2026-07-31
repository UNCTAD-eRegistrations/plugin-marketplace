"""Pure logic for over-12 "split" DETECTION: identify columns rows whose
widths sum above 12 and compute the proposed split-into-multiple-containers
plan. No I/O except the optional ``python -m`` CLI seam at the bottom.
Spec: TOBE-18009 (raised by Erick), gated on DS-Frontend#173 for apply.

IMPORTANT — placement / invariants:
  - This is a SEPARATE, ADDITIVE module. It must NEVER change the behaviour
    of ``columns_logic.analyze_columns_component`` (which keeps returning
    "skip"/"over_12" for these rows unmodified) — this module only adds a
    new, independent read-only capability alongside it.
  - This is a stdlib-only script bundled in the columns-normalization-migration
    skill, invoked by CLI, exactly like ``columns_logic.py``.
  - It must remain STDLIB-ONLY (no third-party dependencies), plus intra-
    package reuse of ``columns_logic`` for the tree walker and shared
    constants — no other ``tools`` or ``BPAClient`` imports.
  - SCAN-ONLY: this module never mutates a form or a component, never calls
    ``form_patch``, and never applies anything. It only computes a plan.

RESOLVED RULES (from Erick + render test; TOBE-18009):
  - Over-12 boundary counts ALL column widths, including trailing empty
    spacer columns. This deliberately DIVERGES from
    ``columns_logic.analyze_columns_component``, which strips trailing empty
    columns before summing (so it labels e.g. ``[6,6,{6,empty}]`` "complete"
    and skips it). An empty ``col-md-6`` still occupies 6 grid units at
    render, so the raw width sum is the true overflow measure — a row summing
    >12 by spacer width is a real visual overflow this module splits on
    purpose. The two modules owning different boundaries is intended, not a
    bug: ``columns_logic`` normalizes under-12 rows, this module splits
    over-12 rows.
  - Greedy 12-boundary grouping: walk columns left-to-right accumulating
    width; when adding the next column would push the running sum PAST 12,
    close the current group and start a new one with that column. Each
    column keeps its own width and its ``components`` (fields). Order is
    preserved.
  - Content-less groups are DROPPED after grouping (marketplace #58). A group
    in which no column carries content never becomes a container: padding one
    to 12 and emitting it added a ``columns`` component holding no fields,
    which no other gate catches (widths still sum to 12, the >= 2-column guard
    still passes, the post-apply assertions still pass, the re-scan still
    converges). This is a POST-filter on the grouping output, NOT a pre-trim
    of the input: a spacer sharing a group with real content is KEPT, and a
    row without a wholly-empty group produces byte-identical output to before.
    The over-12 boundary above is untouched. Two consequences worth knowing:
    (a) if EVERY group is content-less the row is returned as
    ``{"action": "review", "reason": "all_columns_empty"}`` and never split —
    emitting zero containers would be a silent DELETION, since apply is
    ``remove`` the original + ``add`` N; (b) a dropped group need not be the
    trailing one, so with content in the 1st and 3rd groups the MIDDLE group
    goes, the survivors become adjacent and ``_split{n}`` re-closes from 1 —
    a visible reordering, and the right outcome for a row that renders
    raggedly as authored. A drop can also leave a SINGLE surviving container
    (a 1->1 rewrite), which is structurally sound and which the apply side
    tolerates. NB this is not a general "strip empty columns" rule: a trailing
    empty column is the sanctioned way to pad an under-12 row back to 12
    (TOBE-18004 makes those visually free; TOBE-18006 has the builder append
    them). What makes a spacer disposable HERE is only that the row is being
    restructured into sum-12 containers anyway, so the pad step takes over
    its job.
  - Split-then-pad remainder: after grouping, EVERY group whose sum is under
    12 — not just the last one — gets an appended empty filler column of
    width ``12 - sum`` (empty ``components``, ``size`` = the dominant size
    of that group's non-empty columns, offset/push/pull 0, never
    ``hideIfEmpty``). A wide column can force the greedy walk to close a
    middle group short (e.g. ``[8,8,8]`` closes each ``[8]`` group on its
    own), so padding is computed per-group. Groups that already sum to 12
    are untouched (``padded: False``).
  - Three-way classification for a genuinely over-12 row (``base_sum >
    12``): (1) NO width-12 column at all — normal greedy split + pad-every-
    group, exactly as below. (2) has a width-12 column AND the sum of its
    non-12 columns is <= 12 — fully handled by the TOBE-18019 CSS rule
    (shipped: ``> .col-md-12:not(.col-empty){flex:0 0 100%;max-width:100%}``)
    so the 12 breaks to its own line and the (already <=12) remainder wraps
    cleanly beneath it; ``plan_split`` returns ``None``, no plan needed.
    (3) has a width-12 column AND the sum of its non-12 columns is ITSELF
    over 12 (e.g. ``[12,8,8]``: the 12 breaks to its own line via CSS, but
    the remaining ``[8,8]`` = 16 still overflows) — the CSS rule alone does
    NOT fix this, and it cannot be auto-split without either wrapping a lone
    width-12 (the ``defaultsDeep`` 2x width-6 back-fill trap, see below) or
    unwrapping it (determinant-carry for unwrapped pieces is an OPEN design
    question on TOBE-18009). ``plan_split`` returns a ``"action": "review"``
    entry (reason ``"mixed_width12_remainder_over12"``) instead of silently
    dropping the row or emitting an unsafe plan — surfaced for human
    review rather than transformed. This also sidesteps a real editor bug:
    a lone ``[12]`` container is silently back-filled by the BPA editor to
    ``[12,6]`` (lodash ``defaultsDeep`` against ``ColumnsComponent.schema()``
    's hardcoded 2x width-6 default, sum 18 — over 12 again), so a row
    containing a 12 must never reach the grouping step in the first place.
  - Never-emit-under-2-columns guard: as a defensive invariant (belt and
    suspenders against future regressions, not expected to ever trigger for
    valid input given the two rules above), ``plan_split`` returns ``None``
    instead of a plan if any computed container would end up with fewer
    than 2 columns.
  - Determinant carry: the plan records ``determinant_carry: "all"`` — intent
    only. At apply time (out of scope here, gated on DS-Frontend#173) the
    original columns component's conditional/logic/customConditional must be
    copied to ALL new containers; detection does not copy anything.
  - Each new container gets a proposed unique key
    ``f"{original_key}_split{n}"`` (n starting at 1).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any

from columns_logic import (
    EXCLUDED_CUSTOM_CLASS,
    EXCLUDED_KEYS,
    TARGET_SUM,
    iter_columns_components,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _is_valid_width(width: Any) -> bool:
    """True for an int width strictly in 1..12 (bools excluded)."""
    return (
        isinstance(width, int)
        and not isinstance(width, bool)
        and 1 <= width <= TARGET_SUM
    )


def _dominant_size(columns: list[dict[str, Any]]) -> str:
    """Dominant ``size`` among a group's NON-EMPTY columns.

    Local to this module (intentionally not shared with
    ``columns_logic._dominant_size``, which operates on a whole row's body
    rather than one post-grouping group). Falls back to all of the group's
    columns if none are non-empty, then to "md" if the group is itself empty.
    Ties break toward the earliest column (dict preserves insertion order).
    """
    non_empty = [c for c in columns if c.get("components")]
    candidates = non_empty or columns
    sizes = [c.get("size") or "md" for c in candidates]
    if not sizes:
        return "md"
    return max(dict.fromkeys(sizes), key=sizes.count)


def _group_columns(columns: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Greedy 12-boundary grouping (see module docstring). ``columns`` must
    already be a deep copy owned by the caller — this function does not
    copy."""
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_sum = 0
    for col in columns:
        width = col["width"]
        if current and current_sum + width > TARGET_SUM:
            groups.append(current)
            current = []
            current_sum = 0
        current.append(col)
        current_sum += width
    if current:
        groups.append(current)
    return groups


# ---------------------------------------------------------------------------
# plan_split
# ---------------------------------------------------------------------------
def plan_split(component: dict[str, Any]) -> dict[str, Any] | None:
    """Compute the proposed split plan for one over-12 columns component.

    Pure — never mutates ``component`` (or anything reachable from it).
    Returns one of three things:
      - None: NOT an over-12 splittable row (widths sum <= 12, any width is
        non-int/bool/out of 1..12, no columns, keyless, ``customClass``
        carries ``adjust-columns``, the key is in ``EXCLUDED_KEYS``, the
        computed plan would emit a container with fewer than 2 columns
        (defensive invariant)); OR a row with a width-12 column whose non-12
        remainder is <= 12 — fully handled by the TOBE-18019 CSS rule.
      - ``{"action": "review", ...}`` (no ``containers``): a row with a
        width-12 column whose non-12 remainder itself sums > 12 (e.g.
        ``[12,8,8]``) — the CSS rule alone does not fix it, and it is
        surfaced rather than auto-split or dropped (reason
        ``"mixed_width12_remainder_over12"``).
      - ``{"action": "split", "containers": [...], ...}``: a normal
        splittable over-12 row with no width-12 column.
    """
    columns = component.get("columns")
    if not isinstance(columns, list) or not columns:
        return None

    key = component.get("key")
    if not key:
        return None

    custom_class = component.get("customClass")
    custom_class = custom_class if isinstance(custom_class, str) else ""
    if EXCLUDED_CUSTOM_CLASS in custom_class.split():
        return None
    if key in EXCLUDED_KEYS:
        return None

    widths: list[Any] = [
        col.get("width") if isinstance(col, dict) else None for col in columns
    ]
    # Float/non-int widths are treated as not-over-12 (return None) in the
    # detection phase, mirroring the existing columns_logic rule — out of
    # scope here; deliberate, not a bug.
    if any(not _is_valid_width(w) for w in widths):
        return None

    base_sum = sum(widths)
    if base_sum <= TARGET_SUM:
        return None

    # Rows containing a width-12 column: narrow the skip to only the rows
    # the TOBE-18019 CSS rule actually handles (the 12 breaks to its own
    # line, and the remainder — if it itself already fits in 12 — wraps
    # cleanly beneath it). A remainder that itself overflows 12 (e.g.
    # [12,8,8]: [8,8]=16) is NOT fixed by that CSS rule and must not be
    # silently dropped. Splitting it here would risk emitting a lone [12]
    # container, which the BPA editor silently back-fills to [12,6] (lodash
    # defaultsDeep against ColumnsComponent.schema()'s hardcoded 2x width-6
    # default, sum 18 — over 12 again) — or would require unwrapping the 12,
    # whose determinant-carry semantics are an open design question
    # (TOBE-18009). So it is surfaced as a review entry instead.
    has_12 = any(w == TARGET_SUM for w in widths)
    non12_sum = sum(w for w in widths if w != TARGET_SUM)
    if has_12:
        if non12_sum <= TARGET_SUM:
            return None  # fully handled by the TOBE-18019 CSS rule
        return {
            "action": "review",
            "original_key": key,
            "base_widths": widths,
            "reason": "mixed_width12_remainder_over12",
            "determinant_carry": "all",
        }

    groups = _group_columns(copy.deepcopy(columns))

    # Drop any group in which no column carries content. The greedy walk can
    # close a group made entirely of spacer columns — an ordinary shape, since
    # a trailing empty column is the sanctioned way to pad a row back to 12.
    # Padding such a group to 12 and emitting it added a `columns` component
    # holding no fields at all, which no other gate catches: the widths still
    # sum to 12, the >= 2-column guard still passes, the post-apply assertions
    # still pass and the re-scan still converges (marketplace #58).
    #
    # This is a POST-filter on the grouping output, deliberately not a pre-trim
    # of the input: a spacer that shares a group with real content is KEPT, and
    # any row without a wholly-empty group produces byte-identical output to
    # before. The over-12 boundary above is untouched — it keeps counting raw
    # widths with spacers included, and keeps diverging from `columns_logic`
    # on purpose.
    #
    # Note this is NOT a general "strip empty columns" rule. What makes a
    # spacer disposable here is narrow: the row is being restructured into
    # sum-12 containers anyway, so the pad step below takes over the spacer's
    # job and re-creates whatever filler each surviving group needs.
    surviving = [group for group in groups if any(c.get("components") for c in group)]
    if not surviving:
        # Every group is content-less. Emitting nothing would be a SILENT
        # DELETION: apply is `remove` the original + `add` N containers, so an
        # empty container list removes an authored component and puts nothing
        # back. An entirely empty over-12 row is either debris or a deliberate
        # spacer block, and this tool must not decide which — surface it.
        return {
            "action": "review",
            "original_key": key,
            "base_widths": widths,
            "reason": "all_columns_empty",
            "determinant_carry": "all",
        }
    # A dropped group is not always the trailing one: with content in the 1st
    # and 3rd groups the MIDDLE group goes, the survivors become adjacent and
    # `_split{n}` re-closes from 1. That is a visible reordering, and the right
    # outcome for a row that renders raggedly as authored.
    groups = surviving

    containers: list[dict[str, Any]] = []

    for n, group in enumerate(groups, start=1):
        group_widths: list[int] = [col["width"] for col in group]
        group_sum = sum(group_widths)
        group_columns: list[dict[str, Any]] = list(group)
        padded = False

        if group_sum < TARGET_SUM:
            filler_width = TARGET_SUM - group_sum
            filler: dict[str, Any] = {
                "size": _dominant_size(group),
                "width": filler_width,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "components": [],
            }
            group_columns = [*group_columns, filler]
            group_widths = [*group_widths, filler_width]
            padded = True

        containers.append(
            {
                # Provisional key: two distinct over-12 rows sharing an
                # original key would collide here. Deliberate for the
                # detection phase — containers are re-keyed at apply time.
                "key": f"{key}_split{n}",
                "widths": group_widths,
                "padded": padded,
                "columns": group_columns,
            }
        )

    # Defensive invariant: never emit a container with fewer than 2 columns
    # (the defaultsDeep back-fill trap guard). Reaching this point means
    # `has_12` was False (any width-12 row returns above, either None or a
    # review entry, before grouping ever runs) — so, by construction, every
    # under-12 group gets a filler (>= 2 columns) and every full group of
    # non-12 columns already has >= 2 columns. This branch is therefore
    # UNREACHABLE for the normal (no-12) path; it exists purely as
    # defense-in-depth to fail safe against a future regression rather than
    # ever emit an unsafe plan.
    if any(len(c["columns"]) < 2 for c in containers):  # pragma: no cover
        return None

    # Companion invariant to the one above (marketplace #58): never emit a
    # container that holds no content-bearing column. UNREACHABLE by
    # construction — the content-less groups were filtered out before padding,
    # and the pad step only ever APPENDS an empty filler to a group that
    # already survived that filter, so it cannot create a content-less
    # container. Defense-in-depth against a future regression, mirroring the
    # < 2-columns guard: fail safe rather than emit a junk component.
    if any(
        not any(col.get("components") for col in c["columns"]) for c in containers
    ):  # pragma: no cover
        return None

    plan: dict[str, Any] = {
        "action": "split",
        "original_key": key,
        "base_widths": widths,
        "containers": containers,
        "determinant_carry": "all",
    }
    return plan


# ---------------------------------------------------------------------------
# scan_form_for_splits
# ---------------------------------------------------------------------------
def _extract_components(form: dict[str, Any]) -> list[dict[str, Any]]:
    """Mirror how the bot reads a form: prefer a NON-EMPTY top-level
    ``components`` array; otherwise fall back to ``formSchema`` (a dict, or
    a stringified JSON blob as forms round-trip through some BPA endpoints).
    An empty top-level ``components: []`` does not short-circuit the
    ``formSchema`` fallback — some BPA payloads carry the real tree only in
    ``formSchema`` while leaving a vestigial empty ``components`` at the top
    level. If ``formSchema`` yields nothing usable either, fall back to
    returning the (possibly empty) top-level list rather than raising."""
    components = form.get("components")
    if isinstance(components, list) and components:
        return components

    form_schema = form.get("formSchema")
    if isinstance(form_schema, str):
        try:
            form_schema = json.loads(form_schema)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"formSchema is not valid JSON: {e}") from e
    if isinstance(form_schema, dict):
        schema_components = form_schema.get("components")
        if isinstance(schema_components, list):
            return schema_components

    if isinstance(components, list):
        return components

    raise ValueError(
        "form must have a 'components' array, or a 'formSchema' "
        "(dict or JSON string) with a 'components' array"
    )


def scan_form_for_splits(form: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk a form and return the split plan for every over-12 columns
    component found, under the two-class in-grid rule (TOBE-18037):

    - DIRECT children of an editgrid/datagrid are never emitted. The DS grid
      rule (12 tracks + per-width ``grid-column: span N``) wraps them
      correctly by construction — splitting one would degrade a working row.
    - Rows NESTED deeper inside a grid (panel-in-editgrid etc.) fall through
      to the ordinary #171 fluid flex model and suffer the same over-12
      raggedness as top-level rows. They are ORDINARY split rows
      (TOBE-18041): full runnable plans, annotated ``grid_context: "nested"``
      so the runbook's in-grid canary gate and the inventory can see the
      class. A nested row that plan_split classifies as review (mixed
      width-12 / all-columns-empty) keeps that more specific reason, same
      annotation. Top-level rows keep their exact pre-18037 output shape.
    """
    if not isinstance(form, dict):
        raise ValueError(
            "form must be a JSON object with a 'components' array or 'formSchema'"
        )
    components = _extract_components(form)

    results: list[dict[str, Any]] = []
    for hit in iter_columns_components(components):
        if hit.grid_context == "direct_child":
            continue
        plan = plan_split(hit.component)
        if plan is None:
            continue
        if hit.grid_context == "nested":
            # TOBE-18041: nested rows are ordinary rows — the split plan is
            # RUNNABLE (containers and all). The annotation stays so the
            # runbook's in-grid canary gate and the inventory can see the
            # class; review rows (#58 all_columns_empty, TOBE-18030 mixed)
            # keep their more specific reasons.
            plan = {**plan, "grid_context": "nested"}
        results.append({"path": hit.path, **plan})
    return results


# ---------------------------------------------------------------------------
# CLI (`python3 scripts/columns_split.py`)
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    """CLI seam: read a form as JSON on stdin, emit the JSON split-plan list
    on stdout. Fails loud (non-zero exit + explanatory stderr) on non-JSON
    input or an unexpected form shape. Never emits a plan on stdout for
    invalid input."""
    parser = argparse.ArgumentParser(
        prog="python3 scripts/columns_split.py",
        description="Emit a read-only over-12 columns split-detection plan "
        "for a Form.io form read as JSON on stdin.",
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
        results = scan_form_for_splits(form)
    except (ValueError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    json.dump(results, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
