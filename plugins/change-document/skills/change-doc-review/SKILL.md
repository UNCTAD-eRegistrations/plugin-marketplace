---
name: change-doc-review
description: Stage 1 of the readiness review of a change document for an eRegistrations service. Judges the DOCUMENT: true, consistent and complete, before anyone judges the build. Two houses read the published page from one brief, read only, with seven personas; the page session verifies every finding live, applies what stands, keeps the refuted with its evidence, and closes with the same reviewers. TRIGGER when a change document's drawings are settled and Frank's screen review is applied ("review the change document", "adversarial review of the page", "is the document consistent"), and again as a closure after each pass of repairs. NOT for buildability, mappings, versions or the plan's order (that is change-build-review), NOT for writing the page (change-document).
metadata:
  version: 1.0.0
---

# Change doc review, stage 1: the document

The method, whole, with the element classes, the personas, the procedure and the findings file: [`knowledge/readiness/methodology.md`](../change-document/knowledge/readiness/methodology.md) in the parent skill, section "Stage 1". Read it before the first run; this file says how to run it.

## What it answers

Is the change document true, consistent and complete: the current situation against the end situation; every decision of the sessions against every sentence, letter, note, effects row, bot description, phase line and test line; the two kinds of drawing against each other; every condition read in the empty state and every effect's axes against the component's Default behavior; every outcome with a screen, every hidden field with a filler and a reader, every promise with a device; the facts of the old system behind every shape sentence; the citizen's and the officer's words; the plan's coverage. Stage 2 waits for this stage's hand-off.

## How to run it

1. **Freeze the evidence set** and write the brief: the page's published version and address; the reading order; the decisions, dated; the facts of the old system with the instruction to attack every shape sentence with an old certificate in hand; the live ids of the day, by catalogue and latest version, never a pinned id; the tools allowed and the words "read only"; the output format; the success criteria. Template: `2 - eR services/countries/Lesotho/services/renew-not-on-dashboard/reviews/brief-adversarial-11-09-2026.md`.
2. **Run the machine checks** from the parent skill's tools on the page as published, and record the numbers: `screen-labels-check.py`, `logic-check.py`, `phase-coverage.py`, `vocabulary-check.py`, `slop-check.py`, `token-audit.py`. A check that cannot run fails; it never skips.
3. **Launch the two houses** from the same brief, read only, in the background: a Claude agent (general purpose, with the BPA and GDB read tools for the current situation only) and Codex Sol (`gpt-5.6-sol`, effort xhigh, `sandbox_mode="workspace-write"`, its output saved by the session). Each walks the eleven steps of the procedure and writes one findings file in the case's `reviews/` folder, dated, in the methodology's form.
4. **Merge and verify.** Every finding that hinges on a fact is verified live or against the page before it is applied; the merged verdict file records each finding, its verdict (stands, partly, refuted, on the page already), its evidence and what changed; the refuted ones stay with their evidence. Template: `reviews/builders-passes-merged-11-09-2026.md` of the reference case.
5. **Apply, check, publish, prove**: the repairs into the page, the five checks at their baselines, the publish, the served blob equal to the recorded one.
6. **Close**: the same two reviewers reread their own list against the repaired page and the changed elements (brief template: `reviews/brief-closure-pass-11-09-2026.md`); each repaired case compared across the citizen screen, the canvas, the logic list, the phases, the final test and the one-pager.
7. **Hand over to stage 2**: the frozen page version, the inventory, the findings resolved and refuted, the open authorities, the case list, the "could not verify" items, written at the end of the merged file.

## Refuses

To review a page whose version is not recorded · to approve a sentence because it is plausible · to call a page ready while a decision is open on a sentence a citizen reads · to repair the service, publish anything to live, or change the criteria file (a criteria change goes to Frank as one lettered-choices page).

## Done when

Both houses' files exist and are read; the merged verdict file names every finding with its verdict and evidence; the page is published with the repairs and proven served; the closure is filed; the hand-off note exists; the dossier of the case lists the new files.
