---
name: change-build-review
description: Stage 2 of the readiness review of a change document for an eRegistrations service. Judges the BUILD, after change-doc-review's hand-off: can each drawn element be made in BPA as drawn, from a live model and under the platform's rules; what does each change touch elsewhere in the service and in the instance (the impact grid); does the plan build and test every element in an order that works, up to live and back. Two houses with the BPA and GDB read tools, one brief, read only; probes for what no rule and no model proves; a closure by the same reviewers. TRIGGER when stage 1 has handed over a settled page ("builder's pass", "can this be built as drawn", "review the phases", "pre-build review"), and again after any restructure of the phases. NOT for the document's consistency (change-doc-review), NOT for building (the build follows the plan).
metadata:
  version: 1.0.0
---

# Change build review, stage 2: the build

The method, whole, with the element classes, the impact grid, the probe form and the plan chapter: [`knowledge/readiness/methodology.md`](../change-document/knowledge/readiness/methodology.md) in the parent skill, section "Stage 2". Read it before the first run; this file says how to run it.

## What it answers

Three chapters, each with its own findings section. **A, each device**: buildable as drawn · probe · not as drawn · left to guess, with the live model read that day and the platform rule. **B, the impact of each change** on every other class: fields, bots and mappings, determinants and defaults, grids, roles and registrations, GDB versions across every service of the instance and across the draft and live GDBs, catalogues, certificates, messages, translations, shared surfaces, exposure, users and load, the moment. **C, the plan**: order, publish steps and tests on new files, roles, institution and start role, routing conditions and destinations, sizes, probes in the phase that builds their device, decisions with owners, go-live in stops with a regression after each, the way back or the forward repair.

## How to run it

1. **Take stage 1's hand-off** and refuse to start without it: the frozen page version, the inventory, the case list, the "could not verify" items.
2. **Read the live truth of the day** and write it into the brief: every GDB table named on the page by its catalogue, its latest published version with its id, and the version each bot and catalogue of the page pins, the draft site's state, the services whose devices the page names as models, the instance-wide use of the GDB tables the change versions (bots and GDB-sourced catalogues, every service). The reads: `gdb_catalog_list`, `gdb_database_get`, `bot_list`, `bot_get`, `bot_mapping_summary`, `form_query`, `form_component_get`, `field_list`, `classification_groups_list`, `service_get`, `role_list`, `muleservice_list`, `service_export_raw`; all read only.
3. **Launch the two houses** from the same brief (templates: `reviews/brief-builders-pass-codex-11-09-2026.md` for chapters A and B, `reviews/brief-adversarial-phases-14-09-2026.md` for chapter C, both of the reference case), read only, each with the BPA and GDB tools on the instance; a house whose readers do not connect says so in its first line and falls back to dated copies, marked. Output: the five verdict lines, the grid by canvas then bots, the impact record, the probes, the plan's findings by phase, "What I could not verify".
4. **Merge and verify live.** Every "not as drawn", every "left to guess" and every plan finding is checked against the live service and the platform's rules before it is applied; the merged verdict file records verdict and evidence; refuted findings stay. A model's name is read off the product.
5. **Apply, check, publish, prove.** The repairs into the page: canvases, the hidden block, the bot grid with its model column, the logic list, the counts by script, the phases; every probe placed in the phase that builds its device, with its fallback; the five checks and `phase-coverage.py` at their baselines; publish; the served blob equal to the recorded one.
6. **Close** with the same reviewers on their own lists and the changed elements; compare each repaired case across the canvas, the logic list, the phases, the final test and the one-pager; the mapping-level faults of the reference case surfaced only here.
7. **Hand over to the builder**: the readiness grid, the probes with fallbacks, the impact record, the build order with its publish steps, the final-test cases, the go-live order in stops, the closure list.

## Refuses

To change the service or run a probe under a reviewer's authority (the reviewers read; the build lane runs the probes on draft and returns the results) · to give an unconditional readiness verdict while a controlling decision, an incomplete repair or a consequential probe is unresolved · to start on a page stage 1 has not handed over · to name a model it did not read that day · to assume a column absent because the id it was given lacks it (read the catalogue's version list) · to let a dated copy stand for a live read · to call the plan buildable while a probe's fallback is unnamed · to let a test approve through a desk that does not exist yet · to change the criteria file.

## Done when

Both houses' files exist and are read; the merged verdict file names every finding with its verdict and its live evidence; the page is published with the repairs and proven served; every probe sits in its phase with a fallback; the closure is filed; the builder's hand-off exists; the dossier of the case lists the new files.
