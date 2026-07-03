---
name: screens-first-design
description: Define a product's UX screen by screen. An invariant page schema is decided first; then each screen gets one clickable mobile mockup + one spec fiche; parallel agents copy a bundled reference grammar (mobile AND desktop — mobile first, desktop derives after the content review); every mockup is verified in preview before being shown; a regenerable compendium (docs.html), a guided tour and team presentations close the loop; decisions are journaled the same day; every screen passes the pre-verbal check. TRIGGER when the user wants to "define the UX / the screens" of a new product or module ("let's define all the screens", "show me screens", "screens-first"), or to present a designed system to a team. NOT for single static pages or public-facing branded pages.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
metadata:
  version: 0.1.0
  version-date: 2026-07-03T00:00:00Z
  argument-hint: "[design folder]"
changelog: |
  0.1.0 (2026-07-03) - Initial marketplace release, generalized from the original working skill.
---

# Screens-first design

Define a product's UX with **clickable screens as the primary deliverable**. Method proven on a full product design (8 screens + tour + presentations in one day, 2026-07).

## Bundled assets (relative to this SKILL.md)

| Asset | Purpose |
|---|---|
| `../../assets/reference-mockup.html` | THE grammar donor (mobile): a generic starter mockup every screen agent copies from. Each block is commented `grammar: …`. |
| `../../assets/reference-mockup-desktop.html` | The desktop grammar donor: app frame + sidebar + master–detail + right panels + centered modal. Same tokens, same commenting. |
| `../../assets/build-docs.py` | The compendium generator — copy it into the project's design folder and edit the `DOCS` list at the top. |
| `../../docs/design-principles.md` | The pre-verbal principle + the 5-second test + six operational controls. Read before designing the first screen. |
| `../../docs/agent-prompts.md` | Prompt templates for screen agents, in-flight corrections, and the team-presentation agent. |

## The deliverable set (per project)

| Artefact | One per | Purpose |
|---|---|---|
| `ux-pattern.md` | project | The invariant page schema + system map + screens table + freeze/backlog notes |
| `NN-slug.md` + `NN-slug.html` | screen | Spec fiche + clickable mobile mockup (phone frame 390×820, live views) |
| `build-docs.py` → `docs.html` | project | THE single door: every fiche + digests + decisions rendered as one indexed collapsible HTML; **regenerate after ANY .md edit, never hand-edit** |
| `tour.html` | project | All screens chained: overview grid of live iframes + step-by-step guided visit |
| `presentation.html` | project (+1 per module) | Team presentation: screens FIRST, in large live iframes, with 4 factual blocks each — *what you are looking at · the gestures to try · the design choice (D-ref) · to discuss*. No marketing tone, ever. |
| `kb/decisions.md` | project | D-numbered decisions with WHY, written the same day they are made |

## The method, in order

1. **Interview → invariant schema.** Before any screen: what three elements does EVERY page share? (Example from the proving project: a simple workspace + an assistant slider + an external "?" help button on every page.) Write `ux-pattern.md` with the system map (numbered moments) and the screens table. Ask structuring questions one at a time, always with a recommended default.

2. **One screen at a time, mockup + fiche together.** The mockup is the deliverable; the fiche records intent, gestures, design choices (D-refs) and an explicit `## Open questions` section. Every open question later answered gets struck through with the D-ref: `~~question~~ — **settled (Dnn)**`.

3. **Reference grammar for parallel agents.** Build the first 1–2 screens yourself, starting from `../../assets/reference-mockup.html`. Afterwards, spawn one background agent per screen using the template in `../../docs/agent-prompts.md`, giving each agent: the exact files to read (schema, decisions, sibling fiches, THE reference mockup), the concepts to render, the two output paths, the style constraints (OKLch tokens only — never named colors; one font family; SVG stroke icons; one shadow; sentence case; `<details>` + index for docs), and "final message = raw data, ≤12 lines". Agents write ONLY their own files.

4. **Corrections fly in-flight.** When the user reviews mid-build, send the correction as a message to the running agents (or resume completed ones) instead of redoing their work. Record each review fix in the fiche ("review feedback <date>").

5. **Verify EVERYTHING in preview before showing.** Serve the design folder with a static server and drive the mockups programmatically (preview eval / screenshot): click every flow, run the sliders via pointer events on the right element. Known traps, all pre-solved in the reference mockup:
   - the phone frame needs `overflow:clip` — NOT `hidden` (closed translated sheets make `hidden` scrollable);
   - `white-space:nowrap` on floating pills, or they wrap on narrow content;
   - `@media (max-width:440px)` makes the phone fill the viewport on real phones;
   - add deep-link support (`?view=v-x`) to multi-view mockups — it enables per-view embedding in presentations.

6. **Single voice.** Card/tour subtitles = the mockup's own subtitle, verbatim — never two explanations for one title. One persona per product, consistent across all screens (grep for invented names after agent deliveries).

7. **Consign decisions same-day**, D-numbered with WHY, in `kb/decisions.md` — including the user's choices AGAINST your recommendation (note both).

8. **Compendium discipline.** `docs.html` is the only door: tour, presentations, module artefacts, digests all linked from its nav; mockups auto-discovered (`[0-9][0-9]-*.html`, excluding `-desktop` drafts). Copy `../../assets/build-docs.py` into the design folder, edit the `DOCS` list, and regenerate after any .md edit. Version the design folder as its own git root at every coherent milestone.

9. **The pre-verbal check (a.k.a. the Teletubbies principle — see `../../docs/design-principles.md`).** Before showing any screen or page: cover the words — it must still say *what this is*, *what to do*, *whether all is well*, through layout, state colors, one-symbol-per-concept and meaningful gestures. Plain-language questions instead of domain vocabulary; one-breath sentences; numbers with visual mass. If a screen needs its help sheet to be understood, the screen is not done. **Register guard-rail:** the principle means DEEP, simple, full of meaning — never childish, never twee; simple ≠ simplistic. The tone stays adult and dignified; it is the depth that must arrive pre-verbally.

## Desktop derivation

**Mobile first, desktop derives.** The phone screens carry the design; the desktop is deduced from them — and only AFTER the content review of the mobile screens is done, otherwise every correction is paid twice. Same subtitles verbatim, same data, same state colors and badges, same JS behaviors.

**The desktop grammar** (all pre-built in `../../assets/reference-mockup-desktop.html`):

- **App frame** `.app` 1280×800 centered, `overflow:clip` — the desktop equivalent of the phone frame, same single shadow.
- **Left sidebar** ~232px carrying the system map as navigation: entries are REAL relative links to the sibling `NN-slug-desktop.html` files, with the current screen marked active — so reviewers walk the whole system by clicking.
- **Content area = master–detail** that actually uses the width: the mobile list becomes a persistent master column (~380px, selected row marked), the mobile detail view becomes the wide detail pane (content capped ~620px).
- **Assistant / help / edit fiches = RIGHT sliding panels** ~380px (`translateX` + backdrop + Escape) — the desktop counterpart of mobile bottom sheets.
- **EXCEPTION — solemn confirmations** (slide-to-confirm) use a **centered modal**, never a side panel: the gesture keeps its gravity.

**Naming and discovery convention:** desktop mockups are `NN-slug-desktop.html` next to their mobile siblings. `build-docs.py` excludes `-desktop` files from mockup auto-discovery while they are drafts — flip them in only once verified.

**Desktop deliverables:** once derived, each `docs.html` section links both formats (mobile + desktop), and a `tour-desktop.html` chains the desktop screens exactly as `tour.html` chains the mobile ones.

## Rhythm with the user

Numbered options + recommended default at every transition; execute directives without re-arguing; when the user challenges a structure ("why two pages?"), check honestly whether the challenge is right — on the proving project, two screens were merged because such a challenge was correct. Freeze work mid-review on request (write the resume plan into `ux-pattern.md`, never lose pending fixes). i18n and desktop derivation come AFTER the content review, never before.

## Module extraction (the modularity proof pattern)

To present one part of the system standalone for an external audience: new mockup in the target folder, target language, WITHOUT the parent product's brand or extras; a written service design as annex (screens remain the centerpiece); its own `presentation.html` with per-view deep-links (`?view=v-x`); log it in the audience's own hub document, not in the parent's docs.
