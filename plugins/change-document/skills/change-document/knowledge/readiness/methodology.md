# Readiness of a change document: the two-stage methodology

Written 14-09-2026 by the page session of the Lesotho recovery case, from the two houses' methodology reports ([the Claude house](../../../../../../../2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/reviews/methodology-claude-14-09-2026.html), [Codex Sol](../../../../../../../2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/reviews/methodology-codex-14-09-2026.html)), the six reviews of that case and its [lessons page](../lessons-lesotho-recovery-11-09-2026.md). Frank's frame (14-09-2026): the first reviews judged consistency, logic and completeness; the pre-build review judges other things; together they must assess the readiness of a change document thoroughly, as two skills. Names by Frank: **change doc review** (stage 1) and **change build review** (stage 2).

## What a readiness review is, and is not

A change document says, with drawings as the contract, what an eRegistrations service looks like today, what it looks like after the change, and how a service designer gets from one to the other in the BPA screens without code. Readiness is two questions asked in order. **Stage 1, the document:** is it true, consistent and complete, so that everyone who reads it, the citizen, the officer, the registry, the platform, the builder, the Director, sees the same service? **Stage 2, the build:** can each drawn element be made in BPA as drawn, from a live model; what does each change touch elsewhere in the service and in the instance; and does the plan build and test every element in an order that works, up to live and back?

Stage 2 does not start before stage 1 hands over a settled page: a build review of a page still moving is redone. Neither stage repairs the service, publishes anything or changes the method's criteria; both read the live instance read only; both are run by two houses (a Claude agent and Codex Sol) from the same brief, and closed by the same reviewers after the repairs. The page session that owns the document verifies every finding live before applying it, and keeps the refuted ones with their evidence.

## The element classes, the spine both stages walk

Every check below names its class. The list is the shared knowledge of the two skills; a review that skips a class says so in "What I could not verify".

1. **Screens per outcome**: the citizen screens as the person sees them, one per outcome of each path, and the BPA canvases, every component once.
2. **Fields**: added; removed, renamed or type changed; their labels, keys and defaults; hidden fields with their filler and their readers.
3. **Determinants and effects**: the condition, its source field and the stored answer, the empty-state answer, the component acted on, the three axes (Activate/Deactivate, Show/Hide, Enable/Disable) against the component's Default behavior, the ancestors.
4. **Validations**: the rule, the message, the moment it is checked (a row's Save, the page, Send).
5. **Formulas and copy devices**: the operator, the source, the moment it recomputes, what reads the result.
6. **Grids**: the row fields, the root or nested counter, the multiple bots over the grid, what an internal bot does to the list.
7. **Bots and mappings**: data bots (read, list, exists, update, create, update or create, entries), internal bots, document bots, message bots; each with its GDB table and version, its key, its input and output mappings, its action row and BotRole.
8. **GDB tables**: columns, versions (draft and live are two GDBs), views, triggers, GDB-sourced catalogues that pin a version, the row set shared across versions.
9. **Catalogues and subcatalogs**: entries, keys and values, groups, the parent a copied select points to.
10. **Registrations, roles, BotRoles**: the activation key, the routing conditions, the destinations per button and status, the institution link, the processing start role, the users who hold a role.
11. **Certificates**, **messages** and **translations**: the fields and columns they show, their templates, the moment they fire, the rows every new text needs.
12. **Fees and payments**, even when none.
13. **Shared surfaces**: My Dashboard and any screen every citizen opens; the cost and the failure mode of what is placed there.
14. **The old GDB tables** (the Legacy stores) and the facts of the old system, written by their owner, dated.
15. **The plan**: phases, sizes, publish steps, tests on new files, probes with fallbacks, decisions with owners, go-live, regression, the way back.
16. **The moment**: when a validation or a determinant reads a field against when the bot or the formula fills it; when a desk formula computes against when the button is pressed.

## Stage 1: change doc review

**Question.** Is the document true, consistent and complete? **When.** Once the drawings are settled and Frank's screen review is applied; again after each pass of repairs, as a closure. **Who.** Two houses from the same brief, read only, each writing one findings file; the page session merges, verifies and applies. **Reads.** The page as published (its version recorded), the decisions list, the facts of the old system, the one-pager and every sibling page; the live service only to establish the current situation (what exists today), never to judge the proposed one.

**Procedure.**

1. **Freeze the evidence set.** Record the page's published version and address, the decisions of the sessions, the facts of the old system, the one-pager, the date of the last live read of the current service. Stop if the page version or the authority of a decision is uncertain.
2. **Inventory the contract.** Count once every screen, canvas, component, hidden field, determinant, effect, validation, formula, action, bot, GDB table and version, catalogue, role form, registration, BotRole, certificate, message, translation, fee. The machine counts what it can (logic check, screen labels check); a human finds the promises that have no letter and no row.
3. **Current against end situation.** The current drawing against the live screen; each current element against its end-state element, changed or untouched; every decision against every summary sentence, canvas note, component note, effects row, bot description, phase line and test line. Stop on a contradiction between two controlling sentences.
4. **The two drawings and the logic lists.** Every citizen label exists on its canvas; every E, V and A letter has its row; the counts match the drawings (the checks exist as tools). A human reads what the tools cannot: an undrawn case, a plausible wrong sentence, a layout BPA would not draw.
5. **The decision sweep by words.** For every decision that removed a rule (a mask, a question, a road), search the whole page for the words and examples of the withdrawn rule, tips and notes included, and list every place before the first edit. This is the pitfall that survived three reviews on the case.
6. **Conditions in the empty state.** For every determinant: source field, stored answer, empty answer, component, axes against the Default behavior, ancestors. Stop if an empty bot answer exposes Send, a required field stays active inside a deactivated panel, or an effect cannot reach its component.
7. **Fields and outcomes.** For every live GDB row the change creates, each column is taken from an old store, asked, copied, computed or a mapping constant, against the page's own GDB grid. Every hidden field names its filler and its readers. Every outcome has a citizen screen, a canvas condition, an officer route where one applies, a final-test line. The state grid: every path against every outcome, the reviewer's own.
8. **People, evidence and words.** Seven personas walk the page: the citizen holding an old certificate, the officer, the registry, the platform with its rules, the plan, the builder, and the third party whose record the service may expose. The citizen's sentences say what to do, what to give and what happens next; the officer's desk shows what the decision rests on; every number, name, code, count and legal claim traces to its authority; the vocabulary, slop and token checks run.
9. **The plan's coverage.** Every element of the inventory is built in a named step, every edge of the final test has a phase that builds what it tests (the phase-coverage check). Order and publish steps are stage 2's.
10. **The moment, read on paper.** Where a validation or determinant reads a field a bot fills, the page says which comes first; where a desk formula gives a date, the page says the day it records.
11. **The findings file and the hand-off.** Findings numbered, grouped (consistency, cases, people's words, evidence, plan coverage), each with a scenario, the two places that conflict, the authority, a one-line repair, the stage it belongs to. Then "What I could not verify". The hand-off to stage 2: the frozen page version, the inventory, the findings resolved and refuted, the open authorities, the case list, the "could not verify" items, so that nothing is lost between the stages.

**Refuses.** To review a page whose version is not recorded; to approve a sentence because it is plausible; to call a page ready while a decision is open on a sentence a citizen reads.

## Stage 2: change build review

**Question.** Can it be built as drawn, what does each change touch, and does the plan get there and back? **When.** After stage 1's hand-off; again as a closure after repairs; the plan chapter again after any restructure of the phases. **Who.** Two houses from the same brief with the BPA and GDB tools on the instance, read only; a house whose readers do not connect says so in its first line and falls back to dated copies, marked. **Reads.** Everything live: the models named on the page, the mappings, the versions of every GDB table named, the catalogues, the roles and institution of a live service of the same shape, the instance-wide use of every GDB table the change versions.

**Chapter A, each device.** For every component, determinant, effect, validation, formula, copy device and bot: the BPA device, the live model (a component key or a bot name read this day), the platform rule that governs it, the status: buildable as drawn · probe (named) · not as drawn (with the repair in the page's words) · left to guess (a mapping's source, a condition value, a hidden field's filler, a catalogue unnamed). A model's name is read off the product, never assumed from the page. A bot's mappings belong to the bot: one bot per level, never one bot filling a row field and a root field.

**Chapter B, the impact grid.** For every change, the classes it touches and the read that proves each cell:

| Change | Touches | Read that proves it |
|---|---|---|
| A field added | the bots that read or write it, the GDB column and version it lands in, the desk and the certificate that show it, its translation row | field list, bot mapping summary, GDB schema, component read |
| A field removed, renamed or type changed | determinants, formulas, copy devices, mappings, certificates, translations that name it (a rename dangles in four places) | the raw export swept, determinant and bot reads |
| A bot added or changed | the GDB version it pins, its columns, its mappings, its action row, its BotRole, the registration and institution that let it run | bot read, mapping summary, GDB schema, service read |
| A determinant or effect | the source's answers, the component's Default behavior, the ancestors, the validation beside it | determinant, behaviour and component reads |
| A grid | its row fields, its counter (root or nested), its formulas, every bot over it, what a second run does to its rows | component, formula and bot reads; the rules on grids |
| A role form or registration | the activation key, the routing conditions, the destinations, the institution, the processing start role, the users who hold the role, the load | service read, role list, the users' assignment, an estimate of files |
| A new GDB version | every bot and GDB-sourced catalogue of every service on that GDB table, the views the dashboards read, the draft and live GDBs as two places | GDB schema, an instance-wide census of bots and catalogues |
| A catalogue or subcatalog | entries, groups, keys and values, the parent a copied select points to, the pinned version | classification reads |
| A certificate, message or translation | the fields and columns shown, its template, the moment it fires, recipient and language, the rows every new text needs | service export, bot reads, the translation document |
| A shared surface | every citizen's opening time, the failure mode of the bot placed there | a draft measurement with the bot running and stopped |
| Exposure | what a person typing numbers can read of other people's records, what the officer sees of third parties | the screens per outcome, the role's fields |
| The moment | when the reader of a field runs against when its filler runs | the action rows and the validation's trigger, read; else a probe |

**Chapter C, the plan.** The order (components, then bots, then determinants, then wiring, then publish); a publish to draft before every test and the test on a file created after it; the roles, institution and processing start role created before the first publish; the routing conditions named with their answers; the destinations per button; the sizes per phase; the probes placed in the phase that builds their device, each with a passing result, a failing result and a fallback; the decisions with owners and dates; GDB versions created on draft and created again on live, the pinned bots moved; go-live in stops, one per publish, a regression after each, the census of the instance before; the way back rehearsed and timed, and where none exists (a GDB version), a forward repair named; the real recovery on live with its holder and its own way back; who is told and when.

**Probes.** A device no rule and no live model proves gets a probe: device · draft action · passing result · failing result · fallback · evidence kept. A failed probe selects its fallback or stops the build; a probe never becomes a test of the finished service.

**Closure.** After the repairs, the same reviewers reread their own list and the changed elements, then compare each repaired case across the citizen screen, the canvas, the logic list, the phases, the final test and the one-pager. The mapping-level faults of the case surfaced only here.

**The findings file and the hand-off to the builder.** Five verdict lines (walked · buildable as drawn · probe · not as drawn · left to guess), the grid by canvas then bots, the impact record, the probes, the plan's findings by phase, "What I could not verify". The hand-off: the readiness grid, the probes with fallbacks, the impact record, the build order with its publish steps, the final-test cases, the go-live order, the closure list.

**Refuses.** To start on a page stage 1 has not handed over; to name a model it did not read that day; to assume a column absent because the id it was given lacks it (read the catalogue's version list); to call the plan buildable while a probe's fallback is unnamed; to let a test approve through a desk that does not exist yet.

## The briefs

One brief per pass, given to both houses, carrying: the page's version and address; the reading order; the facts of the old system and the instruction to attack every shape sentence with an old certificate in hand; the decisions, dated; the live ids of the day (the latest version of every GDB table by its catalogue, never a pinned id); the read tools allowed and the words "read only"; the output format; the success criteria. The five briefs of the reference case are the templates: the adversarial read of the document, the builder's pass, the closure, the adversarial read of the plan, the method's own reading.

## The checks, as tools

Existing in the kit: `screen-labels-check.py` (every citizen label on its canvas), `logic-check.py` (letters, bot names, counts against the lists), `phase-coverage.py` (every element built in a named step), `vocabulary-check.py`, `slop-check.py`, `token-audit.py`, `screen_truth.py` (the current live screen). To build: decision coverage (every decision found on the page, its withdrawn words absent); state and outcome coverage (every outcome with a screen, a condition, a test line); plan order (no test before its device, a publish before each test); GDB usage census (instance-wide, every bot and catalogue pinning a GDB table); certificate, message and translation impact. A check that cannot run fails, never skips.

## What the case taught, in one line each

A finding is patched where it points unless the assumption's words are swept first · the facts of the old system are written by their owner before any drawing · a pattern in the data is not a rule of the system · the example screen hides what can be missing · our reasons never sit on the applicant's screens · counts are computed from the drawings by script · one copy of everything · the platform's rules are stamped on the first canvas · every promise of the prose is followed to its device · reviewers are briefed with facts and live ids, not with decisions and pinned ids · reviews, repairs, then the builder's pass once · the vocabulary check runs on replies · a closure by the same reviewers after every merge · the dossier from day one.
