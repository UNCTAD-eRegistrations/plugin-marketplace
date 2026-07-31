---
name: columns-normalization-migration
description: Scan-and-plan (read-only) workflow for normalizing Form.io column layouts to sum 12 across a service's forms, plus a gated apply, covering BOTH tracks — the under-12 PAD track (widen a short row's columns) and the over-12 SPLIT track (break a too-wide row into multiple sum-12 containers). The APPLY half (any form_patch write) is ENABLED but gated on per-instance deployment of the platform precondition (TOBE-18004 / DS-Frontend#173, DS >= 2.18.326 on the 2.18 line / >= 2.19.188 on develop) AND the instance allowlist — apply only on an allowlisted instance where the DS empty-column exemption is deployed. Use when preparing a columns normalization migration.
argument-hint: "[instance] [service_id]"
license: UNCTAD-Internal
compatibility: Requires an active BPA MCP connection for form_get / form_patch; the scan scripts are stdlib-only Python 3.9+ and run with no install step.
allowed-tools: Read, Write, Grep, Glob, Bash(python3 *), Bash(mkdir -p *), Bash(cat *), Bash(date *), mcp__BPA__form_get, mcp__BPA__form_patch, mcp__BPA__componentbehaviour_generate_newkeys, mcp__BPA__instance_list, mcp__BPA__connection_status
metadata:
  version: "1.3.0"
  version-date: "2026-07-30"
  changelog:
    - "1.3.0 (2026-07-30): TOBE-18041 — the APPLY half for editgrid-nested rows; the 18037 freeze is lifted. Nested rows (panel-in-grid etc.) are now ORDINARY rows on both tracks: the pad scan emits real append/resize plans and the split scan emits full runnable split plans, each tagged `grid_context: nested` (the `in_grid_nested` reason is retired -- nested rows report ordinary reasons; the reverse lockstep guard caught its orphaned vocabulary row, which is exactly the drift it exists to catch). The split apply's ancestry guard is narrowed: a datagrid/editgrid ancestor no longer poisons its whole subtree -- a panel inside the grid resolves as an ordinary container parent -- but a DIRECT child of the grid stays refused (defense-in-depth; the DS grid rule lays those out correctly and a forged plan row must not degrade one), and tabs/table/unknown ancestors keep their blanket rule including inside grids. The pad apply's live re-verification now passes `grid_context` (the legacy `inside_grid` boolean path remains for API stability but has no caller in these scripts), so a live direct child refuses with `grid_direct_child` while a live nested row pads normally. Malformed-width handling is refined: a NESTED row fails loud exactly like a top-level row (it is actionable, and silently skipping it is the corrupt-plan path the raise exists to prevent); only a malformed DIRECT child keeps the swallow + `base_sum: null`. PHASE 3 gains the in-grid canary rule: the first grid-nested apply ever must run on els-dev and verify grid-subtree placement, saved-entry survival (entry data is keyed by field keys, which the split preserves -- verified, not assumed), and the revert round-trip. Tests cover in-grid position arithmetic across rows sharing a panel, the forged-direct-child refusal, tabs-inside-grid staying unsupported, and the grid-nested revert. Review follow-up (#66, Erick): the retirement had left the PHASE 1 prose stale -- the `in_grid_nested` review bullet and the classification paragraph still described the 18037 freeze (an editing mishap: the rewrite was authored but its patch script crashed before writing, and the verification grep checked the pre-1.2.2 spelling). The reverse lockstep cannot see prose (it scrapes markdown table rows only) -- recorded as a known limitation in the test docstring rather than papered over with a curated retired-reasons list, which would itself be a drift vector. Also aligned three annotations from the same rename: the `inside_grid` vocabulary row no longer claims the pad apply calls the boolean API, `_search_descendants`'s docstring now states the two-class grid rule, and the live-index tuple type is `str` (grid_context), not `bool`."
    - "1.2.2 (2026-07-30): Two follow-ups from the #61 review. (1) `base_sum` for an in-grid skip is now None when any width is malformed (null / bool / non-int / outside 1..12): the 1.2.0 raw sum filtered to valid ints, so a nested `[4, null, 4]` row reported a confident-looking 8 and would have passed for an ordinary sub-12 row in the very inventory TOBE-18037 exists to produce, quietly never entering TOBE-18041's scope. The swallowing itself is unchanged and deliberate -- in-grid rows return before the fail-loud width checks so a malformed row inside a grid never aborts a whole-form scan; only the number stopped lying. (2) The pad track's `inside_grid_nested` is renamed `in_grid_nested`, matching the split track: one concept, one spelling in one inventory. The direction is deliberate -- `inside_grid` / `inside_grid_nested` differ only by suffix, the exact substring hazard the 1.2.1 token-bounded check defused, while `in_grid_nested` shares no token boundary with the legacy reason. Vocabulary is one day old and in no report yet, so no migration concern."
    - "1.2.1 (2026-07-30): Closed the scan-reason lockstep gap found reviewing #61. The 1.1.3 contract test only read `columns_split.py` and only matched `\"reason\": \"...\"` dict literals, so it could not see the pad track at all: `columns_logic.py` emits 14 reasons, 11 of which were undocumented in PHASE 1, and TOBE-18037's two new ones arrive as `reason = (\"grid_direct_child\" if ... else \"inside_grid_nested\")` -- a form the regex never matched. Redacting both from PHASE 1 left all 203 tests green, i.e. the guard built to stop this drift class could not stop it on the other track. Three fixes: (a) the guard reads BOTH scan modules -- and deliberately NOT the apply modules, whose skip reasons (`row_not_found`, `modified_since_apply`, ...) are PHASE 3 vocabulary and would be wrong to demand in PHASE 1; (b) reasons are collected by parsing the module with `ast` instead of grepping, covering dict literal / `reason=` keyword / plain and conditional assignment, and no longer matching reason names quoted inside docstrings -- the IfExp handling reads only the branches, since walking the whole subtree also harvests `\"direct_child\"` out of the CONDITION and invents a reason that is really a comparison operand; (c) the documented-check is token-bounded, because the old bare substring test let `inside_grid` count as documented purely because `inside_grid_nested` appears, so the shorter reason could vanish from the runbook without failing anything. PHASE 1 gains a full scan-reason vocabulary table for all 17 reasons -- no curated exclusion set, since a second list is itself a drift vector -- including the two fail-loud ones (`null_width`, `invalid_width`) and the note that an in-grid row returns BEFORE those checks, so a malformed row inside a grid surfaces as a grid skip carrying a sum over only its valid widths. Controls: redacting a pad reason fails; removing the `inside_grid` row while keeping `inside_grid_nested` fails; a new reason added via conditional assignment fails; renaming the PHASE 1 heading raises rather than passing vacuously; and a new APPLY-only reason correctly does NOT fail."
    - "1.2.0 (2026-07-30): Two-class in-grid scan (TOBE-18037, scan half only). The old sticky `inside_grid` boolean skipped every columns row anywhere under an editgrid/datagrid, on the premise that grid rows keep their own CSS grid — true only for DIRECT children of the editing entry (the DS rule uses a `>` combinator plus per-width `grid-column: span N`, so 9 x col-md-4 wraps into the authored 3x3 by construction; render-confirmed live on test.kenya, TOBE-18037 comment 103432). Rows nested deeper (panel-in-editgrid, the kenya-test DOSH 'Workplace physical location' case) fall through to the #171 fluid flex model and render all-on-one-line exactly like top-level over-12 rows — invisible to every scan until now. The walker now classifies `grid_context` as none/direct_child/nested: direct children skip permanently (pad reason `grid_direct_child`; split scan never emits them — splitting one would degrade a working row); nested rows enter the scan but the APPLY STAYS FROZEN for both classes until TOBE-18041 (grid-subtree insertion and editgrid submission-data survival unproven) — the pad scan reports them skip `inside_grid_nested`, the split scan surfaces would-be splits as review `in_grid_nested` with base_widths and NO containers (flag-not-transform). Both in-grid pad skips now carry a RAW width sum (spacers included, matching the split boundary semantics) where the old single skip reported base_sum None, so the all-form-type inventory can size them. Effect-level freeze pinned by test: a forged plan row claiming an actionable pad for a live in-grid row is refused by the pad apply's live re-verification, which still runs the unchanged legacy `inside_grid` path — zero apply-side changes. Top-level rows keep their exact prior output shape; nested rows that #58/TOBE-18030 already classify (all_columns_empty / mixed width-12) keep those more specific reasons, annotated `grid_context: nested`."
    - "1.1.3 (2026-07-29): Over-12 rows ending in empty spacer columns no longer split into a container holding no fields (marketplace #58, found on the kenya-test DOSH guide form `guidecolumns2` -- 10 x width-4 with two trailing spacers, which emitted a 4th container of nothing but empties). The greedy 12-boundary walk can close a group made entirely of spacers, and NO existing gate caught the result: widths still summed to 12, every container still had >= 2 columns, the post-apply assertions still passed and the re-scan still converged, so an applied split would have left a junk component behind on a clean-looking run. Route 1 per Erick's decision on #58: filter the groups AFTER grouping, immediately before the pad loop, so padding / `_split{n}` numbering / the >= 2-column guard stay downstream and unmodified. The over-12 boundary does NOT move -- it keeps counting raw widths with spacers included and keeps diverging from `columns_logic` on purpose; only the grouping output is filtered. A spacer sharing a group with real content is KEPT, so any row without a wholly-empty group produces byte-identical output to before (the existing 39 split tests and the whole corpus stayed green unchanged). Three cases handled explicitly: (a) if EVERY group is content-less the row returns `{action: review, reason: all_columns_empty}` rather than an empty container list -- apply is `remove` original + `add` N, so emitting zero containers would SILENTLY DELETE an authored component; (b) a drop can leave a single surviving container (a 1->1 rewrite), verified tolerated by `plan_to_split_operations` and by the revert round-trip; (c) a dropped group need not be trailing -- with content in the 1st and 3rd groups the MIDDLE group goes and the survivors renumber from 1, a visible reordering now documented. Added a runtime defense-in-depth guard mirroring the < 2-columns one, a `_assert_no_content_less_container` test invariant, and the corpus's first split-track fixture with empty source columns (`split_spacer_group.json`; `over_12.json` is a `columns_logic` pad-track fixture and blesses nothing here). Root cause of the gap: `_col()` in `tests/test_columns_split.py` unconditionally inserted a textfield, making every empty-source-column case unreachable from the suite -- it now takes `empty=True`. Review follow-up (#59, Erick): the new reason is also documented in the PHASE 1 review-row enumeration -- the operator-facing surface, where a flagged row actually becomes visible to a human -- with its own disposition (debris or deliberate spacer block; human decides; no TOBE-18030 pointer, that ticket covers only the mixed-width-12 case). Locked in by a contract test that reads the emitted reason list from columns_split.py and requires each one in the PHASE 1 SECTION specifically, so a changelog mention cannot mask the gap again."
    - "1.1.2 (2026-07-28): Fixed a Python 3.9 incompatibility that broke the columns split REVERT path, found by the first live els-dev canary (TOBE-18009). `revert_split_operations` used `zip(container_keys, written_containers, strict=True)`, which is Python 3.10+ only, so on stock macOS -- where `python3` is still 3.9 and this skill explicitly promises operators can run the bundled scripts with plain `python3` and no virtualenv -- the entire revert died with `zip() takes no keyword arguments`. The forward apply was unaffected (sole 3.10+ construct, and only in the revert function), so an operator could APPLY but not ROLL BACK: the recovery path was the broken one. Replaced with an explicit length-equality check that raises ValueError, preserving the safety intent the `strict=True` carried -- a prefix-only zip would leave `pristine` True while later containers went unverified, emitting a blind restore over unchecked state. Also de-`strict`ed two test helpers where the lists are equal by construction, and added a 3.9 leg to the CI matrix plus a whole-tree `compileall` (previously a single 3.13 job, which is why this was invisible). Declared the 3.9 floor in `compatibility`. On 3.10+ the guard is STRONGER than the `strict=True` it replaces, not merely equivalent: the verification loop breaks on the first non-pristine container and `strict=` only fires when zip advances past an exhausted iterator, so a corrupt row whose first container was already non-pristine used to break out before `strict` ran and was silently downgraded to a `modified_since_apply` skip. It is now reported as the error it is, as a pre-pass naming every corrupt row at once."
    - "1.1.1 (2026-07-28): Fixed a self-contradiction (TOBE-18009, Erick review 102772): the 'Instance allowlist — the operator's checklist' section still said writes may target only els-dev and aborted on anything else, predating the #54 pinned instance-identifiers table that marks cuba and kenya-test as migration targets — followed literally, the skill would abort on the instances the rollout targets. Reconciled the checklist's permitted-set language and abort rule to name the same pinned set as the table: permit {elsalvador-dev (canary), cuba, kenya-test}, never write {vucecuba, cuba-test, jamaica, lesotho2}. No change to the pinned table, the AUTOPILOT_MODE-is-a-no-op reframe, the vucecuba never-write pin, the canary-states-its-target rule, or any LWW/hash/Envers/publish-gate content."
    - "1.1.0 (2026-07-27): Restored two safety guardrails that fell through the seam when this skill was relocated from the MCP repo (this skill predates MCP_eRegistrations#470, still open, which added them to the pre-move SKILL.md). Added the pinned instance-identifiers table (cuba -> cuba.eregistrations.org is the migration target; vucecuba -> vucecuba.mincex.gob.cu is sovereign production and NEVER a write target; kenya-test, elsalvador-dev, cuba-test also pinned) under the instance-allowlist checklist. Required the first-use canary to print the resolved target instance and intended change BEFORE its write, so a wrong target is caught before the batch, not after."
---

# Columns Normalization Migration (scan + plan + gated apply)

Normalize Form.io `columns` layouts so each row's widths sum to 12. This skill
drives **two parallel tracks** under **one shared safety model** (allowlist,
LWW re-verify, canary, off-hours, per-service human-gated publish):

- **Under-12 PAD track** — a row whose widths sum to **less than 12** is
  widened in place: scan via the stdlib `columns_logic` module (`build_plan`),
  apply via `columns_apply` (`plan_to_operations` → `form_patch` SET-ops on the
  same component's `columns`).
- **Over-12 SPLIT track** — a row whose widths sum to **more than 12** is
  broken into multiple sum-12 container rows: scan via `columns_split`
  (`scan_form_for_splits`), apply via `columns_split_apply`
  (`plan_to_split_operations` → one atomic `form_patch` `remove`+`add` batch),
  including managed rows that carry a BPA behaviour (their visibility pointer is
  **re-attached** after the structural write — see PHASE 3).

This skill ships the **read-only scan and plan** portion of both tracks, plus a
**gated apply** portion. The platform precondition
(**TOBE-18004 / DS-Frontend#173**) has **merged and released**
(**2.18.326** on the 2.18 line, **2.19.188** on develop), so the apply half is
no longer categorically deferred. It is **enabled**, but must run **only** on
an **allowlisted** instance whose **deployed** DS build meets that version
floor — **deployment is per-instance, and merged does not mean deployed.**

## Where this lives — MCP is the interface, this skill is the processing

The work is split in two, and the split is deliberate:

| Half | Who provides it | What it does |
|------|-----------------|--------------|
| **Interface** | the **BPA MCP server** | `form_get` to read a form, `form_patch` to write it, plus auth, instance resolution, and the audit log |
| **Processing** | this skill's **bundled scripts** (`scripts/*.py`) | all columns logic: scan, plan, build operations, revert |

**The MCP server contains no columns logic.** Every scan/plan/operation-build
step runs in the four stdlib-only scripts shipped in `<skill-dir>/scripts/`:
`columns_logic.py`, `columns_split.py`, `columns_apply.py`,
`columns_split_apply.py`. They are **pure and read-only** — they never open a
socket and never write a form. All network I/O goes through the MCP tools
named in the phases below. Run the scripts with plain `python3`; they need no
virtualenv and no dependency install. They target **Python 3.9+** — the
version stock macOS still ships as `python3` — so this promise holds on an
operator's machine without a toolchain setup. Both the apply **and the
revert** paths must stay inside that floor: an apply you cannot roll back is
worse than no apply, and a 3.10-only construct in the revert path is exactly
the bug the first els-dev canary caught (skill 1.1.2).

## ⚠ Safety model — read this first

The safety of this migration does **NOT** rest on an AI agent faithfully
re-reading this prose. Almost every gate here is **procedural** and
**unenforceable at the code layer**. Be explicit with yourself:

| Gate | Enforced where? |
|------|-----------------|
| Instance allowlist (`check_autopilot_allowlist`) | Platform-enforced **at `auth_login`, and only under `AUTOPILOT_MODE`** — see the scope note below |
| Off-hours apply window | Procedural — **not platform-enforced** |
| One operator per instance (one-operator / per operator) | Procedural — **not enforced** |
| Plan review by an analyst | Procedural — **not enforced** |

Because the off-hours window, one-operator-per-instance, and plan-review gates
are **not enforced** / **unenforceable** at the code layer, the plan file is a
convenience, not a control. **The instance allowlist is the only gate with any
platform enforcement at all** — and its reach is narrower than it looks.

### Allowlist scope — know exactly what it does and does not block

`check_autopilot_allowlist` is an **internal function of the MCP server**, not
an exposed MCP tool. **A skill session cannot call it.** Do not read the rule
below as an instruction to invoke it — you cannot.

Where it actually runs:

- It gates **`auth_login`** (`mcp_eregistrations_bpa/server.py`), refusing a
  non-allowlisted instance before any auth I/O reaches Keycloak/CAS.
- It is a **no-op when `AUTOPILOT_MODE` is unset.**
- **`form_patch` does not call it.** No per-write allowlist check exists.

What that means in practice:

- **Under `AUTOPILOT_MODE`:** a non-allowlisted instance cannot authenticate,
  so it cannot be written to. The protection is real but **transitive** — it
  works by denying the session, not by inspecting each write.
- **Running interactively** (`AUTOPILOT_MODE` unset, an operator already
  authenticated to any instance): **nothing in the platform blocks a
  `form_patch` against jamaica or lesotho2.** In that mode every gate on this
  page, allowlist included, is procedural.

So: pass an explicit allowlisted instance to every apply step and verify the
resolved value yourself, because on an interactive session **you are the
enforcement.** Never rely on the platform to catch a wrong instance here.

### Authoritative record

**Envers** history plus the **form_patch audit** log are the **authoritative**
record of what was written. Plan files are **per-operator** and
**non-authoritative** — never treat a plan file as proof of what happened on
the server. Reconcile against Envers and the audit log.

## Backend reality: last-write-wins, no conflict detection

The BPA endpoint `form_patch` writes through does a read-modify-overwrite of
the **whole form** with **no optimistic locking**: **no @Version, no ETag, no
If-Match**, and therefore **no conflict detection**. The backend is
**last-write-wins (LWW)**. Never assume a concurrent edit will be detected or
rejected — it will be silently clobbered. This skill and any script it drives
**must not assume conflict detection exists**.

## Instance allowlist — the operator's checklist

Writes may target only the **pinned permitted set**: **elsalvador-dev**
("els-dev", the canary / first write), then **cuba** and **kenya-test** —
see the pinned identifiers table below for exact hosts and roles. **Never**
write to **vucecuba**, **cuba-test**, **jamaica**, or **lesotho2**. Read the
scope note above first: `form_patch` carries no allowlist check, so on an
interactive session these rules are enforced by **you**, not by the platform.

- Every apply step must pass an **explicit** allowlisted instance. **Never
  instance=None** — no `instance=None` default, no env-configured profile that
  could resolve to vucecuba/cuba-test/jamaica/lesotho2.
- Resolve the instance **first**, then check the **resolved** value, not the
  raw passed-in string. A profile name and the instance it resolves to are not
  the same thing, and only the resolved value is what gets written to.
- Confirm the resolved target with `instance_list` / `connection_status`
  before the first write of a session, and state it out loud in the plan file.
- If resolution is ambiguous or yields anything but one of the **permitted**
  targets (**elsalvador-dev**, **cuba**, **kenya-test**), **abort**.

### Instance identifiers (pinned — confirmed by Erick)

Use these exact names/hosts; do not guess or substitute a look-alike:

| `instance=` value | Host | Role |
|---|---|---|
| `cuba` | `cuba.eregistrations.org` | **Migration target** (Keycloak realm). NOT `vucecuba`. |
| `kenya-test` | `test.kenya.eregistrations.org` | Migration target. |
| `elsalvador-dev` | `dev.els.eregistrations.org` | The "els-dev" canary instance. |
| `vucecuba` | `vucecuba.mincex.gob.cu` | **Sovereign production (CAS) — NEVER WRITE.** |
| `cuba-test` | `test.cuba.eregistrations.org` | Out of scope for this migration. |

`cuba` and `vucecuba` are **not the same instance** — do not conflate them.
`vucecuba` must never receive a write from this skill under any circumstance.

## PHASE 1 — Scan (read-only, SHIPS NOW)

1. For each target service, read the form with **form_get** (force a fresh
   read; do not trust a possibly-stale cache — see the cache note below).
2. Run the form JSON through **both** scanners. Each reads the form JSON on
   **stdin** and prints JSON on **stdout**:
   - **Under-12 pad:**
     `python3 <skill-dir>/scripts/columns_logic.py < form.json`
     to get the pad normalization plan.
   - **Over-12 split:**
     `python3 <skill-dir>/scripts/columns_split.py < form.json`
     to get the split worklist. Its rows are of two kinds:
     - **`action:"split"`** — the runnable split worklist; each such row is a
       full split plan (`containers`, etc.) applied by the over-12 sub-track in
       PHASE 3.
     - **`action:"review"`** — a row the scan flags but never transforms
       (flag-not-transform): record it in the plan for a human, and do **not**
       feed it to the split apply. Two reasons, with different dispositions:
       - **`mixed_width12_remainder_over12`** — a mixed row whose split is
         ambiguous (contains a width-12 column AND its non-12 remainder itself
         overflows 12). These are **DEFERRED to TOBE-18030**.
       - **`all_columns_empty`** — every column in the row is an empty spacer,
         so a split would either emit containers holding no fields or (with
         zero containers) silently delete the authored component. The row is
         either debris or a deliberate spacer block, and the tool must not
         decide which — a human disposes of it per row. No ticket pointer:
         this is not the TOBE-18030 case.

     In-grid classification (TOBE-18037/18041): a row whose schema parent IS
     the editgrid/datagrid is a **direct child** — the DS grid rule lays it
     out correctly by construction, so both scanners skip it permanently
     (pad skip reason `grid_direct_child`; the split scan never emits it,
     and both applies refuse a forged plan row for one). A row nested deeper
     (panel-in-grid etc.) is an **ordinary row on both tracks**: real pad
     plans, real runnable split plans, tagged `grid_context: "nested"`. That
     tag is load-bearing for PHASE 3 — the first grid-nested apply of a
     session is its own canary class, and the first ever runs on els-dev
     (see the in-grid canary rule there). A malformed nested row fails loud
     like any top-level row; only a malformed DIRECT child keeps the swallow
     (skip + `base_sum: null`), since the scan will never act on it.
3. Persist the plan to a **plan** file. Each **plan row addresses exactly one
   component**: keyless or duplicated component paths are **skipped and
   reported**, never applied to a first/arbitrary match. The scan **routes**
   under-12 rows to the **pad apply** (`columns_apply`) and over-12
   `action:"split"` rows to the **split apply** (`columns_split_apply`); the two
   tracks never touch the same row.

The scan/plan output is safe to produce on any instance because it performs no
writes.

### Scan reason vocabulary — every `reason` the two scanners can emit

This is the complete set for the **scan**. The apply modules carry their own
separate skip reasons (`row_not_found`, `modified_since_apply`, …), documented
in PHASE 3 — do not mix the two vocabularies when reading a plan.

A contract test reads these names straight out of `columns_logic.py` and
`columns_split.py` and fails if any one of them is missing from this section,
so the table cannot drift out of step with the code.

**Pad track (`columns_logic.py`)** — `action` is `skip` for every reason except
`under_12`:

| `reason` | Meaning |
|---|---|
| `under_12` | **Actionable.** The row's body sums under 12; the plan appends a filler (`action:"append"`) or resizes/merges existing trailing empties into one (`action:"resize"`). |
| `complete` | Body already sums to exactly 12. Nothing to do; trailing empties are left untouched. |
| `over_12` | Body sums past 12 — this row belongs to the split track, not the pad apply. |
| `already_normalized` | The computed padding would be a no-op, so it is reported instead of proposed as a change. |
| `all_empty` | Every column is an empty spacer, so there is no body to size. |
| `no_columns` | The component has no `columns` array at all. |
| `no_key` | The component has no key, so it cannot be addressed unambiguously — skipped and reported, never applied to an arbitrary match. |
| `excluded_key` | The key is in the module's `EXCLUDED_KEYS` pin. |
| `adjust_columns` | The row carries the `adjust-columns` customClass — the author's explicit opt-out. |
| `grid_direct_child` | Direct child of an editgrid/datagrid: the DS grid rule owns its layout, so it is skipped **permanently** (TOBE-18037). Carries a raw width sum for the inventory — or `base_sum: null` when any width is malformed. Rows nested DEEPER inside a grid do not appear here: since TOBE-18041 they are ordinary rows reporting ordinary reasons, tagged `grid_context: "nested"`. |
| `inside_grid` | Legacy pre-TOBE-18037 classification. No script in this skill calls the boolean API any more (the pad apply passes `grid_context=` since TOBE-18041); the parameter and this reason remain for API stability, so an external caller still gets the historic skip. |
| `null_width` | A width is not an integer (null, float, bool). **`build_plan` raises** — a malformed layout is never silently skipped. |
| `invalid_width` | An integer width outside 1–12. **`build_plan` raises**, as above. |

Two things that trip people reading a plan:

- The pad track's `base_sum` is the **body** sum, with trailing empty spacers
  stripped; the split track counts **raw** widths including spacers. The same
  row legitimately reports two different sums — see the divergence note in the
  `columns_split.py` module docstring.
- `null_width` / `invalid_width` fail loud for every row the scan could act
  on — top-level AND grid-nested alike (TOBE-18041). Only a malformed DIRECT
  child of a grid is swallowed (skip `grid_direct_child` with
  `base_sum: null`): the scan will never act on that row, so it must not
  abort a whole-form scan, and the null keeps "unknown" from reading as a
  confident healthy sum.

**Split track (`columns_split.py`)** — `mixed_width12_remainder_over12` and
`all_columns_empty`, both `action:"review"`, described under step 2 above.

## PHASE 2 — Analyst plan review (procedural)

An analyst hash-checks the plan: for every row, record the source form's
content hash so the apply step can re-verify the form has not drifted. This
review is **procedural / not enforced** — the platform will not block an apply
whose plan was never reviewed.

## PHASE 3 — Apply — gated on per-instance DS deployment + allowlist

The apply half is **enabled** only when the resolved, allowlisted target
instance is running a DS build with the TOBE-18004 empty-column exemption
**deployed**: 2.18-line ≥ **2.18.326**, develop/2.19-line ≥ **2.19.188**
(els-dev tracks develop, so ≥ **2.19.188**). **Verify the resolved instance's
deployed DS version meets that floor before any write; if it does not,
abort.** The code precondition (**TOBE-18004 / DS-Frontend#173**) is
**merged**; the remaining gate is **per-instance deployment** — merged is
not deployed.

The apply half runs **two sub-tracks** — the **under-12 pad sub-track** (below)
and the **over-12 split sub-track** (further down) — under the **same** gates:
resolved-allowlisted-instance, deployed-DS-version floor, off-hours window,
LWW whole-form-hash re-verify, first-use canary (stating the resolved target
instance before its write), and per-service human-gated publish. Neither
sub-track weakens any of those controls.

### Building the operations — both apply scripts have a CLI

Both apply scripts read **one JSON object on stdin** and print the resulting
operations JSON on stdout. Feed them the plan rows produced in PHASE 1 plus the
**live** components read fresh with `form_get` immediately beforehand:

| Command | stdin shape |
|---------|-------------|
| `python3 <skill-dir>/scripts/columns_apply.py` | `{"plan_rows":[...],"live_components":[...]}` |
| `python3 <skill-dir>/scripts/columns_split_apply.py` | `{"plan_rows":[...],"live_components":[...]}` |
| `python3 <skill-dir>/scripts/columns_split_apply.py --revert` | `{"applied_rows":[...],"live_components":[...]}` |

`live_components` is the live form's component tree from the fresh `form_get`;
`applied_rows` (revert only) is the `applied_rows` list the split apply
returned. Send the returned operations to **form_patch** yourself — the scripts
never write.

### PHASE 3a — under-12 pad sub-track

The pad sub-track drives **form_patch** per plan row inside the off-hours
window — building each row's operations via the `columns_apply` script's
live re-verification (stdlib, bundled with this skill) — with these
constraints:

### Pre-write re-verify scope (chosen: WHOLE-FORM hash)

Before each write, re-read the form and compare against the plan's recorded
hash. This skill selects the **whole-form hash** scope, not a per-row hash:

- **Trade-off:** a **per-row hash** would silently revert concurrent edits made
  elsewhere in the same form (LWW overwrites the whole form); a **whole-form
  hash** aborts the row if *any* unrelated part of the form changed. We accept
  the stricter whole-form-hash aborts to avoid silently clobbering a
  third-party edit.
- Re-reading immediately before the write only **narrows** the LWW race window;
  it **does not close** it. A **residual** window remains between re-verify and
  the PUT. If the whole-form hash no longer matches the plan, **abort that row**
  and re-plan.

### First-use canary + rollback (LWW-scoped)

The first applied row is a **canary**. **Before the canary write**, the
canary step must **print the resolved target instance** (the exact
`instance=` value and host it resolved to — see the identifiers table above)
**and the intended change** (component key, current → target widths) — so a
wrong target (e.g. `vucecuba` instead of `cuba`) is visible **before the
write**, and before the rest of the batch, not discovered after. Abort if the
printed target instance does not match the operator's intended instance.

**In-grid canary (TOBE-18041):** the first GRID-NESTED row a session applies
(`grid_context: "nested"` on the plan row) is a canary of its own class, and
the first one EVER must run on **els-dev** before any real instance: verify
the split lands inside the grid subtree (containers under the same panel
parent, correct positions), that an editgrid holding SAVED ENTRIES still
loads and renders its entries afterwards (entry data is keyed by FIELD keys,
which the split preserves — verify it, do not assume it), and that
`revert_split_operations` round-trips. A DIRECT child of a grid must never
be applied — the scan does not emit them and the apply refuses them.

After the canary write, record its **post-write hash**. The **canary
rollback** is itself a **whole-form LWW write**, so it is scoped narrowly:

- Only **re-read-then-restore** when the **live form still matches the canary's
  post-write hash** (i.e. nothing else wrote in between). If the live form no
  longer matches the canary post-write hash, **do not** blind-restore.
- Rollback **cannot recover a concurrent third-party edit**, and it **cannot
  undo the whole batch** — **earlier rows** already committed need **Envers
  rollback**, not the canary path. Do not overstate the canary as a safe
  guarantee.

### Failure / recovery paths during apply

- **Keycloak token expiry mid-batch (401):** refresh / re-auth (token refresh),
  then **resume** — the batch is **resumable** from a **partial batch /
  half-applied** state; do not restart from zero.
- **`_invalidate_form_cache` failure after a write:** the verify step must not
  trust a **cached form_get** — force a fresh read (`force_refresh`) rather than
  relying on a possibly-**stale cache** / **invalidate** failure.
- **Network partition between re-verify and the next write:** the state is
  **ambiguous** — the write may or may not have landed. Do **not blindly
  retry**. **Re-read-and-compare** (the writes are **idempotent** by target
  state) to detect whether the write applied, then decide; never blind-retry a
  non-idempotent overwrite.

### PHASE 3b — over-12 split sub-track (structural)

The split sub-track applies the `action:"split"` worklist from PHASE 1 under
the **same** gates as the pad sub-track (resolved-allowlisted-instance,
deployed-DS floor, off-hours, LWW whole-form-hash re-verify, canary). Build the
operations with `columns_split_apply.plan_to_split_operations(split_plan_rows,
live_components)` — via the script's CLI above — it re-verifies each row
against the **live** form and returns `{"operations", "applied_rows",
"skipped"}` — then apply the structural batch via a **single atomic
`form_patch`**: per split row it is one `remove` (the original component)
**+ N `add`** (the N new sum-12 containers). Because `form_patch` is one LWW
whole-form overwrite, emit the whole structural batch as **one** `form_patch`
call inside the off-hours window, guarded by the same whole-form-hash re-verify
and canary as the pad sub-track.

The split emits **full deep-copied containers** with their identity fields
(`id`, `behaviourId`, `effectsIds`) **cleared** — those are the caller's
responsibility. `id` is assigned by the platform on add; `behaviourId` /
`effectsIds` are (re-)attached by the managed-determinant step below.

#### managed-determinant replication + behaviour re-attach (per managed row)

Over-12 rows whose original component carries a **BPA-managed behaviour**
(non-empty `behaviourId` / `effectsIds` / `determinantIds`) are **no longer
deferred**: `columns_split_apply` splits them structurally like any other row
and attaches a **`determinant_replication`** descriptor to that row's
`applied_rows` entry:

```
{"source_key", "target_keys" (== the N new container keys),
 "source_behaviour_id", "target_behaviour_ids": {}}
```

BPA resolves a container's visibility by its **`component.behaviourId`** pointer
(NOT by `componentKey`). The split cleared each new container's `behaviourId`,
so until the skill **writes a pointer back onto each container**, the containers
render **unconditionally**. The clone tool does **not** attach itself — cloning
alone is **never** sufficient in either order. Execute this as a **distinct
step** for each such row:

- **ORDERING (still load-bearing, but not sufficient): run the clone AFTER the
  structural `form_patch` batch commits.** The N new container keys must already
  **exist** on the form before cloning — calling
  `componentbehaviour_generate_newkeys` before the structural write creates the
  behaviour row against a key that isn't on the form yet. Correct ordering does
  **not** by itself attach the pointer; you must still write it back (below).
  Never clone before the new keys exist.
- **CLONE (1→1, capture the returned ids):** for each row's descriptor, call
  **`componentbehaviour_generate_newkeys(service_id,
  source_component_key=<source_key>, new_component_key=<each target key>)`
  ONCE PER target key** — the endpoint is **1→1** (one call clones the source
  behaviour onto **one** new key) and returns an old→new id map. **Capture the
  returned new `behaviourId` and `effectsIds`** for that target key. The clone
  creates the behaviour row but, per its own docstring, does **NOT** attach the
  new id to any form component.
- **CRITICAL — WRITE THE POINTER BACK onto each container.** After cloning all
  target keys, issue a **SECOND `form_patch` SET batch** — **one op per managed
  container**:
  ```
  {"op": "set", "key": <container key>,
   "properties": {"behaviourId": <new id>, "effectsIds": [<new effect ids>]}}
  ```
  Record each written id into `target_behaviour_ids[target_key]` (used by
  revert). (Alternative: `form_component_update` once per container to set the
  same `behaviourId`/`effectsIds`.) All N containers thereby inherit the
  source's original condition.
- **POST-APPLY ASSERTION (the check that would have caught the bug):** after the
  SET batch, **re-read each managed container fresh** (`force_refresh`, not
  cached) and confirm its `behaviourId` is **non-empty** and **matches the
  cloned id**. If **any** managed container comes back with an **empty**
  `behaviourId`, the condition did **NOT** attach → treat that row as a
  **failed apply**: do **not** proceed, **surface** it, and apply the row's
  **revert path** (below). Never accept a managed split whose pointer did not
  land.
- **IDEMPOTENCY: behaviour creation via `componentbehaviour_generate_newkeys`
  is NOT idempotent** — a blind retry after a partial failure **duplicates
  behaviours**. Before re-calling for a target key, **check that key for an
  existing matching behaviour (or clean it up) first**; never blind-retry.
- **CANARY (managed split):** extend the first-use canary so that for a managed
  split it re-reads and verifies the **visibility POINTER** — `behaviourId`
  present on the container **and** the condition resolves — **not only** the
  column widths. A canary whose widths sum to 12 but whose pointer is empty is a
  **failed** canary.
- **ORPHANED SOURCE BEHAVIOUR (tracked debt):** the structural `remove` of the
  original component leaves its behaviour **orphaned-but-intact**. **LEAVE IT**
  — revert re-binds it by re-adding the original key, so no recreation is
  needed. But it is **invisible to `recover_orphaned_config`** (which only
  detects forward orphans), so **RECORD the orphaned source `behaviourId` as
  tracked debt** in the apply output/log. Do **not** delete it, and do **not**
  gate the migration on its cleanup.
- **REVERT ordering for a managed row:** **FIRST** delete the replicated
  behaviours on the new keys (using the recorded `target_behaviour_ids`),
  **THEN** run the structural revert (`revert_split_operations` — the
  `--revert` CLI above: remove the split containers, re-add the original
  component) — re-adding the original key **re-binds its intact original
  behaviour automatically**.

## PHASE 4 — Verify

After each row, re-read the form with **form_get**
(fresh, not cached) and confirm the widths now sum to 12 and no unrelated
component changed.

## PHASE 5 — Publish (per-service serialized, human-gated)

Publish is **per-service serialized** — one service at a time — and
**human-gated** (**human review** / manual approval before publish). Gate the
publish on the real Envers-based readiness result (**PublishReadinessResult**
from `ServicePublishController` / **Envers** audit history). Do **not** invent
a non-existent readiness step or API — gate only on the real
PublishReadinessResult / Envers history.
