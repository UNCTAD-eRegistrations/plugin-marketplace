# How the Lesotho recovery change document was built, and what it taught the tool

Written 11-09-2026 at the end of the day that closed the drawings, for two readers: the next session of this stream, and Codex Astra, asked for an adversarial reading of the method. The document itself: https://smartrules.ai/service-change-doc/change.html (source `3 - Projects/service-change-documents/lesotho-recover-not-on-dashboard/change.html`). Its one-pager: https://smartrules.ai/service-change-doc/proof-driven-migration.html. The tool's criteria, C1 to C76: `knowledge/criteria-change-document.md` in this folder. The reviews of 11-09: `2 - eR services/countries/Lesotho/services/renew-not-on-dashboard/reviews/`.

## The change in five lines

Sole proprietors registered before the current system cannot renew: their old Business ID or licence is not tied to their verified identity, so My Dashboard never lists it. The answer is a second route: a new service where the person declares the number, the old record is read where it sits (two GDB tables in the Legacy group), the person proves ownership, an OBFC officer confirms, the live registry is written one recovered record at a time, and the existing renewal services do the rest. 6,178 businesses and 22,034 licences. Nothing is migrated in bulk: Frank named it proof-driven migration on 08-09.

## The iterations, dated

| Date | What was built | What was refused, and why |
|---|---|---|
| 18-08 | The evidence pack: every figure of the brief verified read-only on the instance; a choice page for the dashboard placement (A chosen) | |
| 21-08 | The change document written, eight contract screens, placement A put back | The service designers' 20-08 wording (nobody approved it; the button opened an absent service) |
| 22 to 27-08 | The cookbook rework; a collaboration layer for a colleague (his tabs beside the agreed text, a remark tool, a shared repository, a publisher on louis) | The colleague's kit could not write; the layer cost more than it gave |
| 02-09 | The document worked with the colleague; a sentence sweep parked | The collaboration layer set aside: core tool first |
| 03-09 | The criteria file born (C1 to C38); shape B, one screen at a time; a day of UI verdicts | Shape B, set aside 07-09 |
| 07-09 | Two kinds of drawing, never mixed: as the person sees it, and in BPA every component; the citizen look; every screen reviewed; criteria C54 to C65 | The mixture (DS data on a BPA canvas); a second "What is missing" screen; a shape validation where an input mask does; letters on components whose default is the effect |
| 08-09 | The prose reconciled with the drawings; the search rewritten on the Legacy stores; three reviews, 102 findings, applied; the logic check (C70); the officer on every business recovery | Reading the live BUSINESS ID table to find a record; the mask (it fitted 1,450 of 6,036 numbers) |
| 09-09 | A business name on every recovered activity, optional, the live availability check reused, the system refuses a held name; the old activities translated to the live catalogue in advance and written into a new version of the old store (C73, C74) | A yes/no question before the name field |
| 11-09, morning | Two lanes: the data (the licence store's activities and places translated, version 1.9) and the page | |
| 11-09, day | Frank's screen review, 25 findings applied one by one: the migration plan page withdrawn, the Director's seven questions folded into the page, OBFC digital records as the citizen's word, the district letter refuted, every field a licence can lack measured, the licence record without status, a licence follows its business (no conflict desk), a grid instead of a select for the person's businesses, the facts of the old system written (C76) | The shape hint of the new system on old numbers; sentences that state our reasons on the applicant's screens; a catalogue for a list a bot fills; a Recorded field that said what the screen implies |
| 11-09, evening | Two adversarial reviews (Codex Sol 52 findings, a Claude agent 58) applied in one pass; three decisions of Frank (the certificate or another document; the licences tied to the number arrive as activity rows; one click instead of a write bot on the shared dashboard); the phases reviewed; two builder's passes launched | A no-click write bot on the live dashboard: three unproven devices for one saved click |

## The pitfalls, each with the rule it produced

1. **A finding is patched where it points, not where the assumption lives.** "No mask" (08-09) removed the input mask and left "a Business ID looks like A2019/03412" in the nothing-found message, in rule One and in a canvas note, through three reviews. Rule: when a decision removes a rule, search the page for the assumption's tokens and list every place before editing (C76).
2. **A fact of the old system was never written down, so nobody could check against it.** The new number pattern, the district letter, the licence number shapes, the status column, the business name on every licence row: each was assumed, then refuted by Frank or by a count on the full export. Rule: one list of facts from the owner of the old system, dated, every shape sentence tracing to a line of it, every reviewer briefed with it (C76, `evidence/old-system-facts.md`).
3. **A regularity in the data was taken for a rule of the system that produced it.** The first letter of 6,110 old numbers named a district on every live district; the old system never encoded one. Rule: measuring says what the data holds, only the owner says what it meant (C75).
4. **The example screen hid what can be missing.** One named example (C54) showed only the fields that example lacked; Frank could not see District, Starts and Ends. Rule: the "What is missing" screen draws every field the live row can lack, the caption says who sees which and how many.
5. **Our sentences on the applicant's screens.** "Like most licences in OBFC digital records", "asked only when the licence carries none", "this record carries no owner identity", "nothing is written before they decide": true, and not for the applicant. Rule: a citizen line says what to do, what to give and what happens next, never why the field exists (C16 extended).
6. **Counts typed by hand drift the moment a drawing changes.** Bots, determinants, validations, formulas, roles, GDB changes: all six disagreed with the drawings by the evening. Rule: recompute from the drawings by script before every publish (C69, C70); the logic check catches two of the six, the others still need a script.
7. **A hidden pane is where edits land by mistake** (08-09, the colleague's pane). Rule: one copy of everything (C68).
8. **The platform's rules were read late.** Required fields inside a deactivated panel are still demanded at Send (rule 25); a design default written as Hide and Disable strands the component (rule 72); a bot on a nested grid's row count never fires (rule 12); an internal bot writing a grid replaces the list (rule 7). The adversarial reviews found them; the drawings should have carried them from the first canvas. Rule: the canvas stamp names the platform rules its letters obey.
9. **The prose promised what the drawings did not do.** "Its licences come with it", "an officer will search by hand", "one answer, and nothing else". Rule: a consistency reviewer reads every promise against the device that keeps it (C71), and the one-pager is written last, from the page, never beside it.
10. **The reviews were briefed with decisions, not with facts.** The reviewers' citizen persona carried the new system's habits. Rule: the brief carries the facts list and the instruction "attack every sentence that says what a number looks like, with a 2015 certificate in hand".
11. **Speed over order.** A builder's pass proposed before the reviews had landed would have been redone. Rule: reviews, findings applied, then the builder's pass once, on the page that will be built.
13. **The reviewers were briefed with a pinned id, not with the store.** Both builder's passes read the Legacy stores through the ids the brief gave them, 596 and 588, the versions of July; the page reads 1.7 and 1.9, published on 09-09 and 11-09 as ids 637 and 639. Both passes returned "the store lacks the columns the page names" as their stopping finding, and it was false: a GDB id addresses one version, and the brief had frozen an old one. Rule: a brief names a GDB by its catalogue and says "the latest version", and gives the ids of that version read the same day; a reviewer who finds a column missing reads the catalogue's version list before writing "missing" (the same lesson as tier-0 rule 51, refetch the schema in-session, seen from the brief's side).

14. **The mapping-level faults surfaced only on the closure pass.** Two adversarial reviews and two builder's passes read the page; the closure pass, each builder rereading its own list against the repaired page, found that the licence path's name check reused the activity row's three bots (a bot's mappings belong to the bot, so the root-level flags could never fill) and that no hidden field received the old row's Recovered on (the formula's date would have made every licence read as recovered). Rule: after the merge, a short closure pass by the same reviewers, scoped to their list and the changed elements, before the probes; it costs a fraction of a walk and reads the seams the merge created (Frank, 11-09-2026: "closure", not a full re-walk).

12. **Jargon in the replies.** "Served page", "gate", "node", "integration": each cost a question. Rule: the vocabulary check runs on replies as on files (tier-0 rule 75).

## What the method got right, and the skill must keep

- The screens as the contract, drawn from the live service, with a check that every citizen label exists on its canvas (`tools/screen-labels-check.py`) and a check that the logic prose matches the canvases' letters (`tools/logic-check.py`).
- Two kinds of drawing, never mixed; the E, V and A letters on the canvas only (C54, C59, C61).
- Measure before drawing a rule (C69): the mask, the identity numbers, the district letter, the licence shapes, the status column, the business names: every one of them fell to a count on the full export.
- The proof-driven principle: nothing copied, a record moves when its proof exists, ownership decided once, on the business (C72, C51).
- Frank's screen review as the last gate before the adversarial reviews: 25 findings in one day, most of them about words a citizen reads.
- Two independent adversarial readers, then a builder's pass, then the probes on draft: each layer found what the previous one could not.

## What the skill should do next time, in order

1. Write the facts of the old system with the owner on day one, before any screen.
2. Read the tier-0 rules before the first canvas and stamp them on it.
3. Draw the "What is missing" screens from every column the live row can lack, measured on the full export.
4. Run the vocabulary check on every reply to Frank, not only on files.
5. Compute every count from the drawings by script; extend the logic check to validations, formulas, roles and GDB changes.
6. Brief every reviewer with the facts list and the decisions, and read the reviews' findings against the live service before applying them.
7. Write the one-pager last, from the page.
8. Keep the migration plan out of the set unless the decision is bulk: the proof-driven principle makes it one section of the page.
10. Keep a dossier from day one: one HTML landing page of every document of the case, by category, current first, the superseded ones marked, linked from the topic file; on 14-09-2026 Frank could no longer see what had been written about the case ("I am a bit lost"), after six review files, eleven handovers and a dozen pages.
9. Brief every reviewer with the live version ids read that day, and verify each of its findings against the live service before applying it: on 11-09 the two builder's passes agreed on a stopping finding that a single catalogue read refuted, while two thirds of their other findings stood and improved the page.

## For Codex Astra, the questions

Read this page, the criteria, the change document and its one-pager, the two reviews of 11-09 and the two builder's passes. Then, as an adversary of the method, not of the page: where did we lose time that a better order would have saved; which of the twelve pitfalls would you have prevented by a rule, and which by a tool; what should the skill refuse to do at all; what is missing from "What the skill should do next time"; and what would you cut from the criteria, which have grown from 38 to 76 in eight days.

## What follows (14-09-2026)

The two readiness skills, `change-doc-review` (stage 1, the document) and `change-build-review` (stage 2, the build), named by Frank on 14-09-2026, are written from this page, the two methodology reports of the houses and the merged verdicts of the case: topic `5 - Handovers/topics/change-doc-readiness-skills.md`.
