---
name: change-document
metadata:
  version: 1.0.0
  argument-hint: "[service-id] [instance]"
description: Write a change document for an eRegistrations service the house way, where the SCREENS are the contract and the text explains them. Situation and end situation drawn canvas-true from the LIVE service, what to build listed at a glance, phases that carry their own tests. TRIGGER when a decided or studied change on a service needs its document ("make the change document for X", "turn this study into a proposal", "apply the change document format to X"), or when reworking an existing one. NOT for citizen leaflets, NOT for teaching pages, NOT for the legal study itself.
---

# The change document

## Before anything: what is bundled with this skill

Everything this method needs travels with it. Paths are relative to this skill folder.

| File | What it is | When you touch it |
|---|---|---|
| `tools/screen_truth.py` | Prints what a BPA container actually puts on the screen: what renders and why not, every `headerComponents`, each grid's `fieldsShownInGrid`, each panel's collapsed state, the classes that change a drawing | **Before drawing anything.** Read `tools/screen-truth-README.md` first |
| `tools/bpa-mockup-kit.css` | The canvas-true CSS. **The style authority.** Never copy a style block out of a finished plan: a delivered plan freezes and keeps corrections this kit has since made | Every drawing |
| `tools/token-audit.py` | Must return 0 before delivery | Before delivery |
| `tools/slop-check.py` | Strips the machine smell. Must return 0 | Before delivery |
| `tools/vocabulary-check.py` + `tools/terms.md` | The eRegistrations vocabulary. Grid never table, the GDB by its name | Before delivery |
| `knowledge/forms-runtime-quirks.md` | **Read it before your first drawing.** What renders is not what the definition says: header components invisible to every tree walk, `hidden:true` proving nothing inside a grid, ancestors switching children off, effects that show a panel without opening it | Once, then as reference |
| `knowledge/gdb-quirks.md` | Full-text search only sees tagged paths; repeated imports duplicate rows | When a GDB is read |
| `knowledge/bpa-mockup-rendering.md` | How to render, and the rule that the kit outranks any plan | Every drawing |
| `knowledge/feedback-bot-naming-convention.md` | GDB name in capitals, action in lowercase | Every bot you name |
| `knowledge/criterios-de-analisis.md` | The accumulated verdicts, in Spanish. C14 and C15 are primary; C19 to C24 are about drawing and about this document | Before producing |
| `knowledge/feedback-er-implementation-plan-style.md` | The style law, dated, as the reviews produced it | When in doubt on form |
| `knowledge/leaflet-editing-spirit.md` | How every sentence is written | While writing |

**The three checks that gate delivery**, all three must return 0:

```
python3 tools/token-audit.py <your file>
python3 tools/slop-check.py <your file>
python3 tools/vocabulary-check.py <your file>
```

**What you also need, and this skill does not carry:** the BPA, GDB and DS MCP servers, from the same marketplace, with a profile for the instance you are working on. Without them there is no live reading, and a drawing that is not read from the live service is not a contract.

## Connecting to BPA

Before any tool call:
1. If the instance is unknown, call `mcp__BPA__instance_list()` to see registered profiles.
2. Check auth: `mcp__BPA__connection_status(instance="{name}")`.
3. If not authenticated → `mcp__BPA__auth_login(instance="{name}")`, wait for success.

Pass `instance="{name}"` to every `mcp__BPA__*` tool call.

**Read only until the document is approved.** A change document is written from the live service and changes nothing in it. Every call in this method is a read.

**Delegate the big reads.** A whole applicant form saturates a context. Fetch it with `form_component_get(summary=False)` on the outermost container, let the harness save it to a file, and run `tools/screen_truth.py` on that file. Never paste a form dump into the conversation.

## The doctrine (read first, three lines)

1. **The screens are the contract and the main content; the text is just the explanation.** "Current situation" = the detailed screen of the service today, real BPA look, with its plain-English why underneath. "End situation" = the screens of the result, same faithfulness, as many screens as necessary, comments in plain English. Frank verdicts the screens; the approved end-situation screens ARE the acceptance contract.
2. **The drawing shows today's reality and the change. Nothing else.** No traces of abandoned ideas, no design history, no invented styles, no invented fields.
3. **Done = the built service indistinguishable from the contract screens.** The check is mechanical: re-run the same rendering pipeline on the built service and put contract and reality side by side.
4. **The shared document holds only what is agreed (Frank, 23-08-2026).** The current situation never moves: it is read from the live service. Every contract section carries two tabs, "Agreed contract" and "<name>'s try"; the agreed pane is always the default view. Everything a colleague sends about a section, his remarks (numbered J1, J2, his words verbatim, the answer under each, states open · answered · agreed · kept as is) and his own drawn version, lands under that section's try tab, never in the main body and never in a separate section. A try moves into the contract only when both agree, and the row records the move. Nothing is deleted.
6. **The colleague never sees the plumbing (Frank, 27-08-2026).** He says what he wants to change and his proposal appears in his own tab, in the section it concerns, inside the one document everybody reads. He never clones, never sends anything up, never opens a pull request, never hears the words repository, working line or merge. The session does all of it silently. Frank accepts in the same language: "accept Julien's proposal on the end situation". Anything technical shown to a colleague is a fault of this skill, not of the colleague. How it works: §Proposing and accepting.

5. **Choices first, one door, no meta documents (Frank, 18-08-2026).** The review starts with ONE page presenting the open choices as lettered options (A, B, C), recommendation marked; the full proposal, evidence and any audience versions sit behind it, linked, never announced beside it. Deliver exactly one link: the door is an INDEX listing every document of the change in reading order, and every published document links back to it (no orphan pages). Never produce a "how we did it" / method-narration page unasked: a page that neither shows the change nor asks a choice is noise. Backstop: memory `feedback-choices-first-one-door.md`.

## Proposing and accepting (one document, his tabs, no technical words)

**One document, one address.** https://smartrules.ai/service-change-doc/change.html . One switch at the top of the document, `Agreed contract` and `<name>'s try`, flips every section at once; the agreed side is always the default. **The try side starts as a copy of the agreed contract**, so the colleague edits real content instead of a blank pane, and what he changed is read by comparing the two sides. There is no second address.

**Underneath, invisible to both.** The pages are held in the private repository `UNCTAD-eRegistrations/service-change-documents`, folder per change, and a publisher on the server carries `main` to that address every two minutes. Local copy: `~/Claude/3 - Projects/service-change-documents` on Frank's machine, `~/service-change-documents` elsewhere; clone or refresh it silently, never mention it.

**When a colleague says what he wants to change** ("I have a remark on the end situation", "I would draw the phases differently"):

1. Refresh the local copy, silently. If it is not there, clone it: `git clone git@github.com:UNCTAD-eRegistrations/service-change-documents.git`.
2. Run the tool that does the writing, never edit the page by hand:
   `python3 tools/remark.py add --doc lesotho-recover-not-on-dashboard/change.html --section <band id> --author <name> --text "his words, verbatim"`
   It writes the numbered remark into that section's try tab with its state, runs both checkers, and publishes. A wrong section id makes it print every id.
3. A version he draws himself goes in the same pane, as his own screens, written by hand after the tool has opened the pane.
4. Answer him in one line: *"It is in the document, End situation, your tab: https://smartrules.ai/service-change-doc/change.html . Frank sees it when he opens it."*
5. If nothing can be sent because he has no access, say only *"Frank has to give you access, I have asked him"*, and tell Frank.

**When Frank says "show me Julien's proposals"**: list them, one line each, section, what he asks, state. Nothing technical.

**When Frank says "accept Julien's proposal on the end situation"**: `python3 tools/remark.py answer --doc <the document> --id J1 --state agreed --text "<Frank's words>"`, then carry what he accepted into the agreed pane by hand and publish. When he refuses or only answers, the same call with `--state answered` or `--state "kept as is"`, and the try stays in his tab.

**Words to use with anyone**: propose, remark, his tab, the agreed contract, accept. **Words never to use with a colleague**: repository, clone, branch, commit, push, pull request, merge, deploy, address of a copy.

**One-time setup on a colleague's machine**, part of installing the kit, never explained again: he signs in to GitHub once (`gh auth login`) so his session can carry his proposals into the document. If a send fails for lack of access, ask Frank to grant it and say only *"Frank has to give you access, I have asked him."*

## The knowledge, all of it (load before writing)

Every place where this craft's knowledge lives. A session applying this skill reads 1-4 and knows where the rest is.

1. **The living style law** (Frank's rules, dated, updated first): `knowledge/feedback-er-implementation-plan-style.md`
2. **The finished exemplar** (copy its grammar exactly: pairs, done chips, hidden keys, phases): `2 - eR services/countries/Lesotho/services/register-a-business/capital-shares-implementation-plan.html`
3. **The editing spirit** (how every sentence is written): `knowledge/leaflet-editing-spirit.md`
4. **The vocabulary**: the eRegistrations Glossary `2 - eR services/work on services/ai-guides/eRegistrations-glossary.md` + Rosetta Stone `…/guides for AI/rosetta-stone.md`. Grid never table; data bot / internal bot; publishing to draft or live; the GDB by its name.
5. **The drawing pipeline**: `tools/bpa-mockup-kit.css` + `knowledge/bpa-mockup-rendering.md` + the Visual Dictionary digest `…/ai-guides/digests/visual-dictionary.digest.md`.
6. **Reasoning patterns** (the faithful mockup is the contract; a derivable figure is not a field): `2 - eR services/knowledge/patterns.md`. Failure modes: `2 - eR services/knowledge/lessons.md`.
7. **Tool gaps with proof** (e.g. validations unreadable by tool, issue #452 — read them from a dated copy via service_export_raw componentValidation): `2 - eR services/knowledge/mcp-improvement-proposals.md`.
8. **The format registry entry**: `9 - System/ui-ux/formats/implementation-plan/`. Verification: token audit `tools/token-audit.py` must return 0.

## The document skeleton

**The top part, in this order, and nothing else above the first section** (Frank, 2026-07-27, shown against his publishing concept note; same law as the concept-note head, `9 - System/ui-ux/formats/concept-note/concept-note.md` §The pages 20/20a):

1. **The navigation bar, first thing on the page** — brand · the current page named · the operation's other pages · "More" for sources. Full width, white, one bottom border, sticky. It sits ABOVE the title, not under it.
2. **Title** — subject dark, qualifier paler and one size down.
3. **One qualifier line** that says something: "Six phases, all built, proven from the citizen's screen to the registry row", never "implementation plan".
4. **One provenance box** — version, date, state, and the links (change document, test report, legal ground). Everything that used to be a meta line and a backlink line goes in here, as one or two sentences.
5. **One row of index chips** — the sections of this page. Page links belong in the bar, section links belong in the chips; never mix them.

**Every block carries a small bold title** (Frank, 2026-07-27): each sentence, or each group of sentences that says one thing, opens with a two or three word bold title, then a full stop, then the sentences — **Today.** · **What the law asks.** · **What we want.** · **Where it lands.** · **Build order.** The title says the thing, never its category. A bulleted list without titles is five equal grey lines; with them the eye reads five words and knows the argument. Rule: `feedback-bold-small-title-per-block.md`.

Then the sections, all `<details>` collapsed. **"Change in short" is the first one**, and it holds two things: **how it works today, and how we want it to work** (Frank, 2026-07-27: "For the time being, this is the way it works, and what we want is that it works this way"). Announce the two, then take them one by one, and say what is at stake for the company before any mechanics.

Detail of the older head rules, still true inside the provenance box: service · country · version · date and time, written day month year ("22 July 2026, 23:29"), nothing more (Frank, 2026-07-22, removed "(live registry)" and "read-only proposal": "I don't use registry... read-only proposal doesn't mean anything"); backlinks to the change document, the legal review, the law live in their own line, each `target="_blank"` · title with the subject dark and the qualifier clearly set apart (Frank, 2026-07-22): a spaced hyphen between the two, the qualifier one size step down and a PALER grey than the muted token (`Capital and shares<span class="titleq"> - implementation plan</span>`, `.titleq{color:oklch(0.70 0.015 260);font-size:var(--t-lg)}`) · **the opening summary is a collapsible `<details id="short">` titled "Change in short", collapsed by default, holding the `.stamp` bullets inside; it is NOT an index chip** (Frank, 2026-07-23: "make opening summary collapsible" + "see capital and shares, collapsed" — the capital-shares plan is the reference form; the bullets that used to sit in an always-visible box now collapse like every other section) · index chips (ONE row of pill links with quiet inline group labels, never a stacked list) · then sections, ALL `<details>` collapsed by default:

1. **Current situation** (pill: "the current screen") — the detailed screen(s) of the CURRENT situation (BPA-faithful, from a live pull), each followed by short plain-English commentary in the owner's logic (what the service does: the screens · the bots · the database; never configuration states). Facts stamped with their pull dates.
2. **End situation** (pill: "the contract") — EVERY element the change makes visible, not only the screens (Frank, 2026-07-23): the form screens, the certificates (today beside the changed version, as a pair), and any other artifact a citizen or officer sees, each as a contract drawing. ORDER: all the drawn things first (screens, then certificates, then further drawn tabs), the "logic, spelled out" annex and the method subs after — what you look at together, then the explanations. Comments in plain English; same three-part logic in the text: screens · bots · database.
3. **Checks that change** — three plain sentences in a collapsed sub INSIDE the end situation (a standalone section only when the checks truly need their own space): only what a screen cannot show (an operator = becoming ≤, a validation's meaning).
4. **Phases** (plan-sized changes only) — **one separate COLLAPSIBLE block per phase** (settled 2026-07-22 after a one-table trial was rolled back the same day: "it was better when phases were separate, tests at the end of each phase"; if a table form ever returns, each phase must collapse). `details.sub` cards, WHITE (`#phases details.sub{background:#fff}`), collapsed by default, preparations first. Inside each: the build actions as BULLET POINTS, one action per bullet (Frank, 2026-07-22: "separate the actions"), then a closing paragraph of fixed labeled lines, **tests at the end**: **My test** (the session tests first, on draft; the test states the pass bar — a separate "Success criteria" line was tried and REMOVED as duplicative, Frank 2026-07-22: "more or less the same as the task") · **Sol's test** (the independent GPT tester run through Codex, AFTER and BLIND — briefed with the contract screens and the phase's tests only, never the build notes; scripts, Playwright + REST, not MCP) · **Your decision** where one exists ("answer in the chat, I write it here"; NEVER the word "gate") · **Your check** (the visual thing Frank looks at before the next phase starts, "so we progress on solid bases and correct early" — **with direct links to the exact BPA and GDB pages** he opens, Frank: "to make my check easier, put the link to the concerned BPA or GDB pages"; only verified URL patterns, e.g. `…/services/<id>` and `…/database/<id>`). A phase touching an undrawn screen starts with its own live reading + contract drawing and builds nothing until Frank approves the drawing — and **the drawing is as big as the change** (Frank, 2026-07-23): read the whole tab always, but when the change is minor draw only the changing part as a today/changed PAIR (the certificates pattern; recognizable context, rest = one quiet 'unchanged' line); the full-page drawing is for structural changes. Bots are created with their grids; each phase checks rows land; the GDB is the judge. A collapsed "For the builder" note may hold keys, UUIDs and tool names.
5. **What the change triggers** — one table grouped by Frank's categories, every row LOCATED by the name of its bot, register, document or label. **Every named element is a LINK to the thing itself** (Frank, 2026-07-25: "we should put links to all elements"): the reader opens it from the document, never hunts for it. This is the citation rule applied to elements, and it extends beyond this table — a drawing's caption and its summary chip, a certificate, a database, a bot, a screen, the labels row: wherever an element is named as the subject, the name carries its link. Verified BPA routes (read from the frontend's own route table, 2026-07-25), all under `https://<bpa-host>/services/<serviceId>`: the applicant form `/forms/applicant-form` · one certificate `/print-documents/<documentId>` · all certificates `/print-documents` · one bot `/bots/<botId>` · all bots `/bots` · the service's databases `/settings/databases` · translations `/formiotranslate` · roles `/roles/<roleId>` · registrations `/registrations/<registrationId>` · determinants `/determinantstable` · fields `/fieldstable` · messages `/messagestable`. A GDB database is `https://<gdb-host>/database/<numericId>` (the published version, not a draft). Never invent a route: if the pattern is not verified, link the nearest verified parent page (e.g. the databases list) and say so. Ids stay in `data-key`; the visible text stays the plain name. Groups: **The screens** (first a one-line pointer: the chips and badges on the contract screens ARE the change list; then only undrawn screens get rows) · **The bots** (mappings) · **The database** (the register, its GDB version) · **The certificates** (print documents, verify live; Frank 2026-07-22: "say certificates, not papers") · **The words** (label renames + their translation rows; nothing published shows without them). Also cover: removals' leftover conditions/effects/actions (usually in the logic annex), Part B, the leaflet if one exists. Never a flat mixed list where a one-line check sits beside a whole bot as an equal.
6. **Tensions with parked changes** — where this change meets another parked one; merge, never overwrite. Say WHERE the parked change lives (its document, linked) and NAME THE BUILD ORDER: the phases decide who builds first, so never "whoever builds second" (Frank, 2026-07-22: "we are masters of the phases"). Open questions Frank wants kept open are WRITTEN IN the document ("Open question, kept here until you close it") and stay until he closes them.
7. **Legal ground**, anchored — each requirement linking its exact article in the country's law pages (`#s-N` / `#reg-N`).
8. **Final test** (pill: *the proof*) — **the end-to-end test is NOT a phase; it is the document's last section** (Frank, 2026-07-25: "this should not be a phase but the last section, final test"). A phase is a piece of building, checked before the next one starts; the end-to-end run happens once, when the build is whole, and proves the whole change at once. It holds: the written scenario with concrete numbers, what the applicant must see, what the database must hold, the variants, the edges, the regression, then My test / Sol's test / Your check, and links to the results report. Per-phase tests stay inside their phases (they gate the next phase); only the whole-change run is lifted out. The phases section says so in one line and links here.
9. **For the AI, technical anchors** (collapsed, "Frank: skip this") — service and component keys, bot and register ids, formulas, drift notes, decision trails. UUIDs live ONLY here.

## During the build — plan vs progress (Frank, 2026-07-23, capital-shares phase 0)

- **The plan text is frozen; progress is a separate layer.** Each phase bullet stays ONE short task sentence. When a task finishes, add under it a green done line: `<div class="done"><b>done</b> a few plain words, dated.</div>` (`.done{color:var(--ok);font-size:var(--t-sm)}`, chip = bordered pill). Never rewrite a plan bullet to carry findings — the reader can no longer tell plan from progress. Phase body text one step smaller than the page (0.9rem).
- **Phase 0 = build-day preparations only**: the fresh dated copy, version/schema work, probes. Service understanding is plan-making work: validation rules → the logic annexes; the reach (which GDBs hold fields the change modifies → which bots write them → modified in which phase, exclusions with reasons) → "What the change triggers". Ask the reach question exactly so: "what are the GDBs in which there are fields which are modified in the change?"
- **GDB field names carry the durable meaning; form labels the moment** ("Shares issued" in the GDB, "Shares issued now" on the form).
- **Designers' open draft**: fold your additions into it and publish; nothing is lost. Do not park the build waiting for their word (Frank, 2026-07-23).
- **Reopen at the modified part**: stamp `open` on the edited section's details chain in the HTML (fragments alone are unreliable on reused tabs; force fresh loads with a changing `?v=N`). Strip all stamps at final delivery.
- **A finished phase wears a done chip in its summary line** (visible collapsed); the `open` stamp moves to the phase in build.
- Extra banned words in prose: "ceiling" (say "at most the capital"), "piece" (data field), "writer bot" (data bot). A done line always states read vs modified.

## Two sizes, one register (Frank, 2026-07-26)

The change document (`changes.html`) is the register of every decided change for a service. It holds two sizes.

**A big change** gets its own implementation plan: drawings, phases, final test. The entry links to it.

**A small change IS its entry.** No plan, no phases, no contract screens. Five parts, and nothing else:
1. **Today** the exact text or behaviour now, quoted from the live service.
2. **Becomes** the exact new text. For a wording change this pair IS the drawing.
3. **Why** one line, with the law or the reason.
4. **Check** what you open to see it landed.
5. **State** proposed → your go → built, with date and audit → proven, with date.

**Closed plans freeze.** They gain one line pointing to later changes on the same screens, and nothing else is edited: a contract you keep rewriting is neither a contract nor a record. Today's truth is the service and its truth file.

**Small changes batch**: collect entries, then build and publish in one pass, with one check afterwards.

**Testing is proportionate**, three levels: a text or label change is proven by opening the page and reading it, on a NEW file, with a screenshot in the entry · a logic change gets the thin-slice test · anything touching a database, a bot or a certificate gets the full final test.

Reference: `services/register-a-business/changes.html`, entry e7.

## Right-size the method, and test a thin slice first (Frank, 2026-07-23)

- **Match the ceremony to the change.** The full apparatus below (contract drawings of every screen, phase blocks, dual reviews) is for a substantial change. For a small one (a couple of fields, one rule), use a light change-note + the thin-slice test, not the full plan. The process is as big as the change, like the drawing.
- **Every phase test is a written scenario + a full results report.** The test states concrete numbers and an expected result per line (the golden scenario, its edges, and the regression). The run produces a REPORT of expected vs actual, pass/fail per line, the GDB/registry values printed, evidence linked — delivered as an HTML page and opened for Frank. Never report a test as "it works" (Frank, 2026-07-23). A phase whose test reads "run the whole path once" is undefined; write the scenario.
- **Walking-skeleton test FIRST.** Before building all phases to the contract, build ONE field + ONE rule, publish to draft, RENDER it, and confirm the citizen behaviour. Config-match is the design gate; the rendered form is the build gate. Do not call a phase "built" from a config diff. This catches BPA runtime surprises (a hidden validation row still fires; maxFromField is ignored when a validation store is set; a determinant operator-flip strips its field comparison — see 2 - eR services/knowledge/lessons.md) on turn one instead of after a full build.

## The test, two legs (settled 2026-07-24, Lesotho capital-and-shares run + the two Antonio reviews)

The end-to-end test of a built change is TWO legs with a hand-off at the moment of submission — the conclusion both independent reviews (a Claude agent and Sol) reached over Antonio vs the browser runner, applied:

1. **The browser leg proves what the citizen sees** (the only leg that can): a headless Playwright pass as a real user — dashboard, guide, every tab, real clicks on dropdowns (a JS click updates the widget but never reaches the model), grid rows committed and VERIFIED committed, uploads, the contract behaviours (formulas, red checks appearing AND clearing, warnings with their exact words), through the submit button. Reference implementation + reusable helpers: `2 - eR services/work on services/tools/citizen-runner/` (login, guide loop, fill/radio/choose/upload, tab navigation, evidence dumps, results ledger).
2. **The Antonio leg proves what the institution does**, taking the submitted file id: officer desks, the GDB rows, the certificates, the messages — his skill already owns that ground (sign-desk recipe, diagnosis rules, replay packs).

**The results report** (never "it works"): one HTML page beside the plan, linked both ways. Verdict numbers on top; EVERY check as expected against actual with its evidence link; the generated documents beside their contract drawings; a **"Findings beyond the change"** section, each finding with its recommendation (Frank, 2026-07-24: testing must report any problem in the service, not only the change); a **"Not exercised yet, honestly"** section — silence never counts as covered (Antonio's NOT EXERCISED state, adopted). A failing check fails the run.

**The five accelerations** (paid for in hours on 2026-07-24; the session diagnosis carries the evidence):
- Save progress per tab, so a retry starts where it stopped, never at the login.
- BEFORE opening any browser, read the form definition and list every required field per tab; an invisible required field costs one read there and four runs on screen.
- Never patch one field of a filled file through `file_set_data` — it replaces everything; read all, merge, send all, or do it in the browser (proof: `knowledge/mcp-improvement-proposals.md`, 2026-07-24).
- Verify each thing at the moment it is done (row saved, field present), not five tabs later.
- Keep a light fast mode (no per-step screenshots) for repeat runs once the path is proven.

Component registrations govern which Part B roles show an element in their data tab — they never hide anything from the applicant (Frank, 2026-07-24; `knowledge/lessons.md`). When an applicant element does not render, read its OWN effects and conditions.

## Process v2 — eight economies (adopted by Frank, 2026-07-25, from the capital-and-shares session review)

1. **The document is as big as the change.** Load-bearing parts only: the contract drawings, the phase cards, the report link. Commentary that repeats a drawing dies; a small change's plan stays under ~400 lines.
2. **One state file per change** (`<change>-state.json`: phase → state → evidence link); the plan page and the topic row render from it. Progress is written once.
3. **The contract compiles into the tests.** A generator reads the approved plan page (its chips, badges, `data-logic`) and emits the results-ledger skeleton with every expected value; the run fills actuals; the report builds itself. No hand-written checklists.
4. **The preflight, one motion (Frank, 2026-07-25: the checkup is part of the preflight)**: one reading of the published service → the truth file (7) AND its fault checkup AND the per-tab lists (required fields, computed fields, visibility rules) as machine files. It runs at the START of the plan (the systematic logical review of the WHOLE service, inside "Current situation") and re-runs at phase 0 on build day; the runner consumes its output. BEFORE any browser opens, ever. **Its result is VISIBLE in the plan** (Frank, 2026-07-25): "Current situation" opens with a collapsed sub "The service's logic, checked". **Its summary line carries the full verdict as chips**: the total then the three-way split — "9 faults · 3 fixed · 4 for you · 2 designers", "fixed" in the ok green; never a vague chip. **Its body is organized by those SAME three groups, in order**: FIXED — with a TENSE: before the build the group is "THIS CHANGE FIXES", neutral grey chip, rows reading today's fault → what the change does and in which phase; the green "fixed" appears only as phases land, with done lines and audits (green is progress, never plan) — (each row once built: what existed → what was done, audit in data-key) · NEEDS YOUR DECISION (fault in plain English · proposed fix · three owner chips unmarked, Frank rules: fixed by this change becomes a phase bullet · for the designers, reported · parked, written until closed) · FOR THE DESIGNERS (pre-marked, with the reason). The fault family (stripped comparison · never rendered · never filled · dead determinant · mapping) is a small grey tag per row, never the grouping. The machine files link only in the technical block.
5. **Two legs, hand-off at submission** (section above), with per-tab resume and a fast mode.
6. **Frank's check is one link to one pair** — expected beside actual, before beside after, per phase. He never hunts.
7. **The truth file, the preflight's engine**: a per-service machine dump (every determinant as compiled, every effect, formula, required field), refreshed at each publish, dated, diffable, PLUS the automatic fault checkup over it (comparisons against nothing, required fields no path can render, fields other logic reads but no path fills, effects on dead determinants). **The checkup's flow (Frank, 2026-07-25): scan → auto-fix what is safe and reversible (audited writes on the design, rollback kept) → THEN write the result in three groups: FIXED (what existed → what was done) · NEEDS YOUR DECISION (anything touching meaning: a default, a legal question, a text) · FOR THE DESIGNERS (beyond our tools). Nothing safe waits; nothing meaningful is decided silently.** The plan names which faults the change fixes and which it reports to the designers; faults are corrected BEFORE testing — testing proves only what reading cannot (real behaviour on screen). The 2026-07-24 defects were all visible in compiled logic nobody had dumped. Tool home: `2 - eR services/work on services/tools/truth-file/`. **The dated dump is shared property**: any session working the service reads `services/<service>/truth/` from disk BEFORE any API archaeology (a 17-call role sweep on 2026-07-25 rediscovered what the morning's dump already held); the API is for what the dump lacks and for verifying writes.
9. **The report proves conformity, never lists failures (Frank, 2026-07-25).** A failed check is not an outcome: fix it and re-run until green. The delivered report is the PROOF that all was done according to plan; the only failure it may carry is one outside the session's authority, named with its proposed fix.
10. **Section order (Frank, 2026-07-25, refined the same day).** What the change triggers, the tensions with parked changes and the legal ground all come BEFORE the phases: all analysis first, then the build plan, **then the final test as the closing section**, then only the technical block. The end-to-end test used to be the last phase; it is not a phase, it is the proof of the whole change and it ends the document.
8. **The scenario numbers live once**, in one small data file the plan, the runner and the report all read.

## The mockup-contract method

1. Pull the real section live: `form_component_get` (READ-ONLY), save the raw JSON to a NEW dated `exports/<section>-fetch-YYYY-MM-DD/` folder. Re-pull before building: services drift (the team edits the same design).
2. Render it in the measured BPA canvas styles: Visual Dictionary §"Spec visual verificada" + §"Component states" (exact greys, label sizes, input heights; `hideLabel` drives the strike, `deactivated` alone changes nothing) + Rosetta Stone Sections I/J; the `ai-guides/tools/bpa-visual-generator/generator.js` tool renders JSON to that look. **ONE kit per page**: when integrating a rendered import, strip its `<style>` block and fold what it adds into the page's single `<style data-specimen>` kit block, rule order preserved — two definitions of one class is the defect family that puts sections in the wrong face. **Each rendering sits in its own collapsed sub**, titled by the part of the system it shows, one grammar (Frank, 2026-07-23): "The <name> tab · <path or moment>" / "The <name> certificate · <part>" ("The Capital & shares tab · only ordinary" · "The Articles certificate · the capital recap"); prose says "the only-ordinary drawing", never "Screen 1"; the legend above the subs carries ONLY the non-obvious marks (striped hidden, logic circle, new/modified chips — white, grey and dashed boxes are self-evident); commentary runs full width. **Canvas-true or nothing** (Frank, 2026-07-22): dashed outlines around every component as the canvas draws them; striped background where `hidden:true`; no invented left bars; the REAL indicator badges (E/A/V/F/D/C) at each component's own top-right corner, each with a styled mouse-over tooltip (`data-tip` + a small CSS bubble) carrying the FULL logic sentence in the design vocabulary, the same sentence as its annex row, never just the type: an **E badge names the determinant first, then the effect axes, then the default** ("Determinant: Type of shares is Ordinary and preferred shares. Effect: Show + Enable + Activate. Default: hidden."); a **V badge states the check**; an **F badge states the formula**. ONE core sentence, no status words ("Kept unchanged" is banned: unmarked = kept, the chips mark change) and no commentary tails; drift notes and what-replaces-what live in the annex only. Information content components draw as a soft blue box. Each badge also carries a `data-logic` attribute with the ids and build detail for AI (existing logic; and for new components, the logic to build). Native `title` is not used anywhere on a drawing, badges or containers (small, delayed, clips, and it fights the styled bubble). **Never scope away a branch**: the whole section renders, every fieldset and grid inside, INCLUDING hidden fields that feed determinants (striped); the complexity is part of the situation. Editor chrome (toolbars, trash/gear icons) stays out. **The logic's content is reviewable**: under each drawing, a collapsed "The logic, spelled out" annex lists every badge: component · type · what it actually does in plain English (formula expression, validation rule, effect + its determinant) · the ids; pulled live via determinant_get / componentformula_get / componentbehaviour_get_by_component. For the end situation this annex is agreed with Frank like the pixels: logic is contract.
3. Apply the change ON the real rendering. The only overlay BPA does not have: two small chips anchored like BPA's own badges: **new** (blue outline) and **modified** (grey outline; absorbs renamed and repurposed; its help opens with *Was "…"*). Chips mark EVERY changed element, content texts included. No field-type tags for humans (the box says it: white dotted = the applicant types, grey solid = the form fills); types survive in hidden `data-type` attributes. The required asterisk stays. **The author never comments inside the screen**: paths are SHOWN (one end-situation screen per path, chips only on what changes in each); helps as short as possible without losing meaning. **Contract-grade logic**: every effect, validation and formula of the end situation carries its badge, a plain-English tooltip saying exactly when it fires, and a `data-logic` attribute with the build detail (what replaces what); an error message states its trigger condition. The approved screens are the implementer's roadmap.
4. Number-heavy sections: fields follow the story left to right; a unit suffix on every number; example values chosen so no two figures coincide; a trivially derivable figure is NOT a field (its name lives in a help line; a hidden computed field feeds the register if it must be stored).
5. The mock carries the texts and the changes: no separate texts table, no change table, unless the drawing genuinely abbreviates.

## Evidence and language

- Every claim stamped (live pull date, export date, or "Frank, date"); a wrong claim is removed loudly, not patched. Bot names in prose ("NP owns at least 10 of shares"); numbers substantiate in half a line (1 of 26 input mappings connected).
- Findings PROVEN (say how) or THEORY. The register is the judge, not the screen.
- Editing spirit throughout; NO em dashes anywhere; sentence case; simplest word.
- **GDB vocabulary (Frank, 2026-07-22):** name the database by its GDB name ("the GDB Legal Persons"), never "the register" as its name; **fields**, not columns, and new fields LISTED BY NAME ("Maximum shares the company can issue · Shares issued now"), never counted ("two columns"). A GDB **draft version is not operational**: the version the service needs is **published**.
- **The change's databases are part of the change (Frank, 2026-07-25, corrected).** The GDBs a change needs are ITS deliverable: make them match the agreed **end situation** fields and publish them — on the design side AND on any site the change must run on, draft included. On draft just do it: no informing the platform team, no repair packages, and overriding what the draft already holds is fine (publishing a service does not carry database versions across). Then test it works, registry row included. The earlier "record it and defer that proof" wording is RETIRED — deferring turns our own task into a wait. Only a genuine rights wall is worth raising, and as a request for ACCESS, never for someone else to build our database. **But prove it is rights before you say so (Lesotho, 2026-07-25):** read the RAW refusal body, because a site's catalog can be **mirror-managed from an origin GDB** and refuse edits by design, to every account — its 403 names the origin and says "re-sync". The discriminating test costs one call: a bare write returns **400** when the path is open and authenticated, versus 401/403 when it is not. The MCP wrappers relabel that mirror 403 as "authentication failed", which is exactly what sent two sessions chasing an access grant that would have changed nothing. When the site is a mirror, the action is a **re-sync from origin**, not a schema build and not a rights request.
- **Read the GDBs before writing the "database" trigger row; never pose a storage question the schema answers (Frank, 2026-07-23).** When a change adds data that may persist, enumerate the service's databases (`gdb_database_list`) and READ the schemas of the company DB and the per-actor DBs the bots write to, then choose the home by the **grain of the data**: company/class-level facts → the company DB (e.g. Legal Persons `CAPITAL/Prefered shares`), per-shareholder → the shareholders DB (Owners/Shareholders), per-owner → the owners DB. Do not accept a storage home (yours or Frank's) without reading the schema. The "What the change triggers → the database" row is grounded in that read, never left as an open "GDB or form-only?" question. Backstop: eR `knowledge/lessons.md` §"Read the service's GDBs before proposing where new data is stored"; working-style twin memory `feedback-evidence-over-agreement`.
- **Banned jargon in Frank-facing prose (Frank, 2026-07-22, phase 0 review):** never "pull" ("I re-read the tab from the live service and save a dated copy"), never "stale" ("the drawing shows the service exactly as it is on build day"), never "export" ("the dated copy"), never "the team" bare ("the service designers", and say plainly that THIS plan's changes are all the session's own, through the MCP tools). "pull"/"export" stay fine inside the collapsed for-AI technical block only.

## Before the build starts — MANDATORY, no exceptions

**Every plan must be reviewed by Codex before any implementation** (Frank, 2026-07-22: "the review by Codex was very, very useful; put this as part of the skill"). The full pre-build review is an **adversarial, evidence-based review by two independent reviewers**: Codex verifying the document against the saved raw files and its own internal consistency (offline, `codex exec --skip-git-repo-check -c sandbox_mode="workspace-write" --cd <service folder>`), and a Claude agent verifying every factual claim against the live service with READ-ONLY tools. Both are briefed to refute, not to admire; every finding carries its evidence or dies. Findings are applied INTO the document (the trail goes to the handover), then Frank's verdict, then the build session starts at phase 0. No phase 0 without the Codex review done and integrated.

## Three layers, each fact in exactly one (Frank, 2026-07-25: "simpler is always better")

The documents bloat because the same fact is told three times: on the drawing, in the logic annex, and again in the technical block. Fix the place of each kind of fact and the bloat cannot come back.

- **The drawing shows WHERE**: the element, its chips and its badges. The badge tooltip carries ONE core sentence.
- **The annex says WHAT, in one sentence per row**: determinant, effect, default · the formula · the validation, in the design vocabulary. Nothing else. The rows are contract, so none is ever deleted, but a row that needs a paragraph is hiding its tail.
- **The technical block holds IDS, DATES AND HISTORY**: what replaced what, when a row was retired, what the service designers changed, build reminders, decision trails. It is collapsed and marked "Frank: skip this" precisely so this material has a home.

Applied to the capital-and-shares annexes on 2026-07-25: 32 rows kept, the same logic, 1060 words down to 580. Write every new annex this way from the start.

## Every element is a link (Frank, 2026-07-25)

The document is a console, not a description: from any named element the reader reaches the element itself in one click. Apply it in the triggers table first, then everywhere an element is the subject — the drawing captions and their summary chips ("open in BPA"), the certificates, the databases, the bots, the labels row. The routes are listed in the skeleton's point 5; they were read from the BPA frontend's own route table, so they are verified, and anything not on that list is verified before use or replaced by its nearest verified parent. Repeat mentions inside the same section do not need the link again; the first, subject-position mention does.

## The words on the page (Frank's line reviews, 2026-07-25, one checklist)

Run this over every section before delivering. It is what separates a document he reads from one he wades through.

- **No article.** Titles, subsection titles, phase names, table headers, group labels: *Change in short · Current situation · End situation · What the change triggers · One tension to reconcile · Legal ground · Phases · Final test*; *Capital & shares tab · today*; *Logic, spelled out*; *Screens · Bots · Databases · Certificates · Words*. "Where we stand" is retired, it is **Current situation**.
- **The simplest word that carries the meaning**, everywhere. Say each idea once. Cut scaffolding ("the method, your words", "one page beside this plan", "grounded in the reading of"): state the thing.
- **No em dashes, ever.** Colon, comma or full stop.
- **Every figure carries its unit; money carries its currency**: 20 000 shares, LSL 40 000, LSL 5 a share. A bare number is a defect.
- **Name the company, never the code.** A test file is "company STAGED ISSUANCE R2 0725", never a dossier number; the code rides in `data-key`.
- **Chips carry a verdict, not an inventory; few digits.** "read live, 22 July", not "14 badges · read live, 22 July". Keep counts that ARE the verdict (18 of 19).
- **Marks so the eye sees the result** on final-test scenario lines: ✓ proven · ○ waiting · ✗ failed, with a legend above. A line never run is grey, never red.
- **Progress lines are a few plain words and a date.** Past ~25 words a done line has swallowed its reasoning; the why goes to the technical block. Exception: a loud correction of an earlier wrong claim stays where the claim was made.
- **State the consequence.** A finding that says what happened but not what it cost ("the copy never filled the answer") makes the reader ask why it mattered. Say it: the file could not be submitted at all.

## Verification gate before delivering

Collapsed-by-default sections, the opening summary "Change in short" (`<details id="short">`) included + working index chips (tiny JS opens targets) · **the words checklist above applied section by section** · **every named element carries its link** (the triggers table, the drawing captions and their "open in BPA" chips, the certificates, the databases, the bots, the labels row; verified routes only) · `python3 "9 - System/ui-ux/token-audit.py" <file>` = 0, honestly: the first style block token-pure, BPA quotations in `<style data-specimen>` blocks and `data-specimen` inline, dead grammar deleted not exempted · ONE kit block, imports stripped · every top-level summary the same `<h2>` (a summary in another face or element is a defect) · links `target="_blank"` · no amber, gates and tags quiet grey · open in Frank's browser (`open <file>`) · his verdict line by line, corrections applied the same hour, ripple pass after each.

## Exemplars and references

- **THE reference, finished and approved 2026-07-25** (copy its grammar; every rule in this skill is visible in it): `2 - eR services/countries/Lesotho/services/register-a-business/capital-shares-implementation-plan.html` (+ its legal review in `countries/Lesotho/law/`, + its results report `capital-shares-test-report.html`).
- Plan exemplar: `…/register-a-business/bo-implementation-plan.html`.
- Real-look rendering pilot: `…/register-a-business/specs/capital-shares-real-look.html`.
- Format registry entry: `9 - System/ui-ux/formats/implementation-plan/`.

## Session structure

One topic per service, one SUBTOPIC per change (the topic file carries a `## Subtopics` table; `/pickup <topic> <subtopic>` resumes one thread). Parallel sessions each live in their own subtopic and never collide (Frank, 2026-07-23; exemplar: topics/lesotho-rab.md — shares · bo).

## Knowledge loop

When Frank refines a rule during a review, update memory `feedback-er-implementation-plan-style.md` in the same hour, and this skill when the change is structural. Cross-country lessons go to `2 - eR services/knowledge/patterns.md`.
