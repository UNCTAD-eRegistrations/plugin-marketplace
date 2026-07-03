# Agent prompt templates

Four templates used by the screens-first method. Fill the `{placeholders}`; keep the structure. Agents run in the background, one per screen, after the first 1–2 screens have been built by hand.

---

## (a) The screen agent

One background agent per remaining screen. It copies the grammar, never invents it.

```
You are building screen {NN} — "{screen title}" of {product}.

FILES TO READ FIRST (in this order):
1. {design folder}/ux-pattern.md            — the invariant page schema; every page MUST have its three shared elements
2. {design folder}/kb/decisions.md          — D-numbered decisions; respect every D-ref that touches your screen
3. {design folder}/{NN'}-{sibling-slug}.md  — one or two sibling fiches, to copy the fiche structure
4. {reference mockup path}                  — THE grammar donor; copy its CSS/JS blocks (each is commented "grammar: …"), do not restyle

CONCEPTS TO RENDER on this screen:
- {concept 1 — one line}
- {concept 2 — one line}
- {concept 3 — one line}

OUTPUTS (write ONLY these two files, nothing else):
- {design folder}/{NN}-{slug}.html  — clickable mobile mockup: phone frame 390×820 overflow:clip, title bar + "?" help,
  bottom sheets + backdrop + Escape, legend aside for the reviewer, media queries 860/440px, ?view= deep links if multi-view
- {design folder}/{NN}-{slug}.md    — spec fiche: intent, the views, the gestures, design choices (with D-refs),
  and an explicit "## Open questions" section

STYLE CONSTRAINTS (non-negotiable):
- OKLch tokens from the reference mockup's :root only — never named CSS colors, never new hex values
- One font family (the reference's); SVG stroke icons (stroke-width 2) only — no emoji, no icon fonts
- One shadow (the phone frame's); sentence case everywhere (capitalize first word + proper nouns only)
- Status colors keep the product-wide meaning: amber = draft/attention, green = done/confirmed, primary = to do
- Subtitles: one breath, one idea — the mockup's own subtitle will be reused verbatim in tour and presentation cards
- One persona for the whole product: use {persona name and business} in all sample data — do not invent new names

BEFORE FINISHING: run the 5-second test (cover the words — the screen must still say what this is,
what to do, whether all is well). If it fails, redesign before polishing copy.

FINAL MESSAGE = raw data, ≤12 lines: files written, views built, gestures implemented,
D-refs applied, open questions left in the fiche. No prose, no summary of the method.
```

---

## (b) The in-flight correction

When the user reviews mid-build, send the correction to the running agent (or resume the completed one) instead of redoing its work.

```
Review feedback on screen {NN} ({date}) — apply now, then continue your task:

1. {correction 1 — exact, observable: "the badge on row X must read 'Confirmed · {date}', not 'Done'"}
2. {correction 2}

Also record each fix in {NN}-{slug}.md under a "Review feedback {date}" line.
Everything else in your instructions is unchanged. Same final-message format.
```

---

## (c) The team-presentation agent

One agent for `presentation.html` (and one per module presentation). Screens first, facts only.

```
You are building presentation.html for {product} in {design folder}.

READ FIRST: ux-pattern.md, kb/decisions.md, every {NN}-{slug}.md fiche, docs.html for the linked artefacts.

FORMAT — screens FIRST, one section per screen, in system-map order:
- The screen in a LARGE live iframe (the real {NN}-{slug}.html, deep-linked with ?view= where relevant)
- Exactly 4 factual blocks beside/below it:
  1. What you are looking at   — one breath, from the fiche's intent
  2. The gestures to try        — the 2-3 clickable things, imperative voice
  3. The design choice          — the main decision with its D-ref, one sentence of WHY
  4. To discuss                 — the open questions still in the fiche, verbatim

TONE: factual only — no marketing language, no superlatives, no "delightful/seamless/powerful".
Card subtitles = each mockup's own subtitle, verbatim (single voice).
STYLE: same OKLch tokens as the mockups; sentence case; collapsible <details> for any long annex.

FINAL MESSAGE = raw data, ≤12 lines: file written, sections built, iframes wired, D-refs cited.
```

---

## (d) The desktop conversion agent

One background agent per screen, spawned AFTER the mobile content review is closed (mobile first, desktop derives — never before, or every correction is paid twice).

```
You are deriving the DESKTOP version of screen {NN} — "{screen title}" of {product}.

FILES TO READ FIRST (in this order):
1. {design folder}/{NN}-{slug}.html          — the reviewed MOBILE mockup: the source of truth for data, copy, states, behaviors
2. {design folder}/{NN}-{slug}.md            — the fiche; respect every D-ref
3. {desktop reference mockup path}           — THE desktop grammar donor; copy its blocks (each commented "grammar: …"), do not restyle
4. {design folder}/ux-pattern.md             — the screens table, for the sidebar entries and their order

OUTPUT (write ONLY this file):
- {design folder}/{NN}-{slug}-desktop.html

CONVERSION RULES:
- App frame 1280×800 centered, overflow:clip; SAME OKLch tokens, font, icons and status colors as the mobile mockup
- Left sidebar ~232px = the system map: one entry per screen, REAL relative links to the sibling
  {NN'}-{slug'}-desktop.html files in system-map order, this screen marked active (class "on")
- The mobile list view becomes the master column (~380px, selected row marked); the mobile detail
  view becomes the wide detail pane (content max-width ~620px)
- Mobile bottom sheets become RIGHT sliding panels ~380px (translateX + backdrop + Escape)
- EXCEPTION: solemn confirmations (slide-to-confirm) become a CENTERED MODAL, same slider, same pointer events
- SAME data, SAME subtitles verbatim, SAME state flips and JS behaviors as the mobile mockup — nothing new, nothing dropped
- Keep ?view= deep links working for the detail views

FINAL MESSAGE = raw data, ≤12 lines: file written, sidebar links wired, views converted, behaviors ported.
```
