---
name: service-leaflet
description: >
  Build an applicant-facing leaflet (explainer page) for any online or government
  service, brand-matched to a target website, with an optional named voice guide
  that narrates the page (a fixed bubble: auto-scroll, highlight, captions, replay
  per section). Use whenever the user wants a public leaflet, explainer, one-pager,
  or guided walkthrough for a service or procedure, or wants to add a voice guide
  to such a page. Produces a self-contained HTML leaflet styled to match a site the
  user points to (URL or screenshots), plus an optional guided version, and can
  deploy both. Generalises an earlier single-registry leaflet builder.
metadata:
  version: 0.3.0
---

# service-leaflet — brand-matched applicant leaflet + voice guide

Builds two artifacts for any service:

1. **The leaflet** — a self-contained, brand-matched HTML page organised around
   *what the thing IS* (an at-a-glance fact box + ordered sections, with the
   application screens redrawn in the brand style).
2. **The guided leaflet** (optional) — the same page with a persistent **voice
   guide**: a fixed bottom-right bubble (you name it) that narrates the whole page
   and lets each section be replayed. On by default, dismissible.

It is brand-agnostic: the look is taken from a **site you point it at** (or
screenshots) in Phase 1, not hardcoded. The voice guide's **name and voice are
chosen by the user**. Everything else (TTS engine, deploy target, content source)
is asked once.

**Bundled assets** (`assets/`):
- `document-template.html`, `poster-template.html` — brand-neutral layouts driven
  by `:root` `--brand-*` tokens.
- `comparison-template.html` — the **comparison / "which-one" mode**: compare N
  forms/types of a service and help the reader choose (hero → "the big difference"
  two-level schema → colour-coded matrix → upsides/watch-outs → "which fits you?"
  → links). Brand-neutral, driven by `--brand-*` + per-category `--cat-{key}-*`.
- `brand.css` — the token reference (the full `--brand-*` / `--cat-*` set).
- `build-guided-leaflet.py` — injects the voice guide into a finished leaflet.
  Inherits the page brand and supports per-language widget labels (Phase 6).
- `guide-config.example.json` — worked example config for the builder.
- `avatar-default.webp` — placeholder guide portrait (swap it).

---

## Phase 0 — Intake (ASK these first, then wait)

Do not start building until you have answers. Ask, as a short numbered list:

1. **Target UI** — a **link to the website** the leaflet must visually match, **or**
   screenshots/images of it. (This is the brand source — Phase 1.)
2. **Voice guide?** — yes/no. If yes:
   - **Agent name** — what the guide is called (used in the narration "Hi, I'm ___"
     and on the bubble). 
   - **Voice** — **man or woman** (or a specific voice id if they have one).
   - **Language** — the language the guide speaks (e.g. English, French, Spanish).
     The leaflet text should normally match it; a second language can be added as a
     toggle (Phase 6).
3. **The service** — what service/procedure the leaflet is about, and where its
   content comes from: a spec/law/page the user provides, or "you draft it from
   what I give you". (This skill does not assume any particular backend.)
4. **Plumbing** (ask once, only what's needed):
   - **TTS engine** — defaults to **LuxTTS** (the engine we use; full recipe in
     Phase 5), or point at your own. Only needed if a guide is wanted; no engine =
     a static leaflet, or supply pre-recorded clips.
   - **Deploy** — where to publish (a host/path), or "just give me the files".

Record the answers; they parameterise every later phase.

## Phase 1 — Acquire the brand from the target

Goal: fill the `:root` `--brand-*` token block (see `brand.css`) so the leaflet
looks like the target.

**From a URL:**
1. Fetch the page. Modern sites are SPAs — the brand lives in a **bundled CSS
   file** (e.g. `/assets/index-*.css`). Fetch that CSS.
2. Grep it for CSS custom properties (`--*color`, `--brand*`, `--primary*`), raw
   hex values, and `font-family`. The most-used non-neutral colour is usually the
   primary; the next is the accent.
3. Grab the **logo / wordmark** (header `<img>`, `og:image`, favicon) and the org
   name (`<title>`, `og:site_name`).
4. Map findings to the tokens: primary → `--brand-primary` (+ derive `-deep`/`-soft`/
   `-wash`), accent → `--brand-accent` (+ a contrast-safe `--brand-accent-bright`
   for accent-on-dark), body colour → `--brand-ink`, font → `--brand-font`.

**From images/screenshots:** read them and extract the dominant brand colour, the
accent, the body ink, and the font character (geometric sans, serif, etc.); pick a
close web font. Capture the logo if visible.

Write the resolved `:root` block. **Show the user the colour/font choices before
building** (a one-line summary + the hexes) so they can correct.

Accessibility: accent-on-dark must hit ~4.5:1 — that's what `--brand-accent-bright`
is for; don't put the light-bg accent on the primary band.

## Phase 2 — Gather the content

**Ground the content first (recommended).** Pick the grounding skill by service shape:
- **Legal-form types to compare** (private / public / non-profit company…) → run
  **`service-concept-brief`** → a per-type traced content map ("what each type IS").
- **A single-path / non-entity-type service** (a permit, certificate, filing) → run
  **`service-journey-brief`** → a journey-shaped traced map (purpose → who it's for →
  what you provide → steps → what you receive → obligations).
Either produces the sourced content map this phase consumes (law + live form, reconciled,
every claim traced). For a trivial page, build a lightweight content map inline instead.

Structure the leaflet around *what the thing IS*, not the form's field order. A
strong default spine (from company registration) is: an at-a-glance fact box, then
ordered parts (the entity · the people · the rules · the output) — but each service
needs its own structure. Trace every factual claim to a source the user gave you
(law section, spec, the live form). **Never invent legal or procedural facts** —
mark "confirm" where a value is unknown. Keep a short content map (claim → source)
as the page's source of truth.

## Phase 3 — Build the leaflet

Copy `document-template.html` (read top-to-bottom content) or `poster-template.html`
(a fixed comparison/teaching graphic — keeps a two-category `--cat-a`/`--cat-b`
split). Fill the `:root` tokens from Phase 1, replace the `{{PLACEHOLDERS}}`, keep
the class names (they carry the styling). Sentence-case titles; left-aligned,
full-width hero (cap only the lede, never the hero block). Lead with the
**distinctive** thing about this service.

**Write the copy NATIVELY in the target language — never adapt a reference page's
sentences.** If your structural model is a leaflet in another language (e.g. an English
reference for a French page), reuse its STRUCTURE only; re-author every sentence from the
content map, as a native speaker of the target language would. Sentence-by-sentence
adaptation produces calques and invented-sounding expressions that read as a translation
(the Comores entreprenant/SAS leaflets had to be fully re-written in French after a first
English-adapted draft). For any non-English target, run a **native-speaker rewrite pass**
(a dedicated subagent in that language) before shipping.

Add a top-right **Print / PDF** button +
print CSS for a clean branded PDF. Verify headless (no console errors, no overflow
at 1280 and 390).

### Comparison / which-one mode (a third template)

When the leaflet's job is **not** "explain one thing" but **"help the reader pick
between N forms/types"** of a service (e.g. sole proprietor vs company; or
*entreprenant* vs SAS vs SARL), use `comparison-template.html` instead of the
document/poster layouts. Its spine, in order:

1. **Hero** — names the choice and lists the options.
2. **"The big difference"** — a **two-level schema** (level 1 = the first fork,
   e.g. alone vs a company; level 2 = the second, e.g. flexible vs framed). Drop
   the second level for a single-fork choice (keep `.split1`, delete `.bd-down` +
   `.split2`).
3. **Side by side** — a **colour-coded matrix**: one column per form, one row per
   compared dimension. **Responsive: columns at desktop, stacked cards ≤820px**
   (the legend hides and each cell shows its form name via `::before` — fill the
   `{{CAT_x_LABEL}}` tokens in those `content:` rules too).
4. **Upsides & watch-outs** — a pros/cons card per form.
5. **"Which one fits you?"** — short **question → leaning-answer** rows (each answer
   leads with a colour-coded badge for the form it points to).
6. **Links banner** — one branded link per form (e.g. to each form's own leaflet).

**Per-category colour coding.** Each compared form gets its own
`--cat-{key}-{accent|line|wash}` set (keys `a`/`b`/`c` in the example — add `d` for
a fourth, delete `c` for only two). Keep `--cat-*` distinct from `--brand-primary`
so the forms read apart. This is the **only** mode that uses `--cat-*`; everything
else is `--brand-*`. **Feed it from `service-concept-brief`** — its optional
**inter-form comparison column** (the N traced differences) is exactly the matrix's
rows, already sourced. Same verification: no console errors, no overflow at 1280
**and** at 390 (confirm the matrix has stacked to cards at 390).

### Ecosystem chrome — shared ribbon + footer across a family of fiches

When you build **a family of leaflets for one country** (e.g. the OHADA legal forms —
entreprenant · commerçant · SARL · SAS · SA — plus a comparison and a chooser-hub), give
every page the **same chrome** so the set reads as one ecosystem rather than seven unrelated
pages. Six conventions, all proven on the Comores ecosystem (7 live pages):

**1. Flag ribbon (`ruban drapeau`).** A thin striped band pinned at the very top — the host
country's flag colours, one `<span>` per stripe — as the shared brand mark across the whole
set. Swap the hexes for the country's flag; keep the structure.
```css
.flagbar { height:5px; display:flex; }
.flagbar span { flex:1; }
.flagbar span:nth-child(1){ background:#0171c0 } /* Comoros flag — swap per country */
.flagbar span:nth-child(2){ background:#009945 }
.flagbar span:nth-child(3){ background:#f2b400 }
.flagbar span:nth-child(4){ background:#e11f1c }
```
```html
<div class="flagbar"><span></span><span></span><span></span><span></span></div>
```

**2. Common footer (citizen pages) — full-bleed `--brand-primary`.** White text at reduced
opacity, a three-column grid: brand (white logo + tagline) · **inter-fiche nav** (every form
in the family; the current page carries `aria-current="page"` and renders bold) · contact +
partner logos. A bottom strip carries the copyright + an "information à valeur indicative"
disclaimer. **Partner logos are whitened in CSS, not pre-edited** — serve the real colour
logos from a dedicated `/logos/` route and apply `filter:brightness(0) invert(1)` so one file
works on any background. Collapses to one column ≤720px; `display:none` in print.
```css
footer { padding:42px 0 30px; background:var(--brand-primary,#0171c0); color:rgba(255,255,255,.85); }
.footer-grid { display:grid; grid-template-columns:1.3fr 1fr 1.1fr; gap:32px; max-width:1080px; margin:0 auto; }
.footer-col a[aria-current="page"] { color:#fff; font-weight:700; }              /* current fiche, bold */
.footer-partners img { height:30px; filter:brightness(0) invert(1); opacity:.92; } /* whiten any logo */
@media (max-width:720px){ .footer-grid{ grid-template-columns:1fr } }
@media print { footer{ display:none } }
```
The nav `<ul>` lists every form + a "Toutes les formes" link to the hub; the partners row
points at `/logos/<partner>.{png,svg}`.

**3. Greffe variant footer (internal / back-office sheets).** A control sheet for an agency
desk is **not** a citizen page: keep its footer **white** (no brand band), give it a one-line
dotted-link inter-sheet nav (current sheet bold, siblings linked, "à venir" greyed), and close
with a **small UN emblem** (`/logos/un-emblem.svg`, ~30px) beside a formal one-sentence
assistance note. Same family, soberer register.
```html
<div class="wrap footer-un">
  <img src="/logos/un-emblem.svg" alt="UN emblem" class="un-emblem" width="30" height="30">
  <p class="un-note">Document établi avec l'assistance du programme … des Nations&nbsp;Unies.</p>
</div>
```

**4. Title conventions.** Distinguish an **explainer of one form** from the **chooser-hub**:
- *Explain one form* → "**Comprendre le statut de** …" (e.g. "Comprendre le statut d'entreprenant").
- *Choose among forms (the hub)* → "**Choisir la forme juridique** de votre entreprise".

Translate the *pattern*, not the words, for other languages: *understand-this-one* vs
*choose-among-many*.

**5. Ecosystem linking rule — the hub and the comparison are two different destinations.**
- The **hub** (`/formes-juridiques`) lists **all** forms — a generic "see all forms" link
  always points here.
- A **comparison** page (`/comparer`) compares **exactly the two named forms** (e.g.
  entreprenant ↔ SARL). A "compare X and Y" link appears **only on the pages where both X and
  Y are in play** — never send an SA or SAS reader to an entreprenant↔SARL comparison.

When in doubt, link to the hub. Wire the inter-fiche footer nav so every sibling is reachable
from every page: a **late-added form must be back-linked into its siblings**, not left
reachable only from the hub.

**6. `text-wrap: balance` on hero titles from the start.** Put it on `h1.hero-title` the
moment you write the CSS, not as a later fix — it balances multi-line headings with no manual
line-break pass (Comores lesson #9).

## Phase 4 — Narration script (only if a guide is wanted)

One segment per section/subsection, written in the **language** chosen in Phase 0.
Each 1–3 sentences, plain and warm, first person, opening with the agent's name
("Hi, I'm <name>…"). Model the segment shape
on `guide-config.example.json`. Keep one line per segment.

## Phase 5 — Voice audio (TTS)

### The engine we use: LuxTTS (the default, working solution)

LuxTTS is the text-to-speech engine behind every voice guide we've shipped. It
exposes `POST /tts` (form params: `text`, `speed`, `t_shift`, `guidance_scale`,
`voice`), `GET /voices`, `GET /health`. Our instance runs at
`http://5.9.49.171:8092` — **reachable only from the deploy host**, so run the
synthesis there. Voices are cloned and **English-phonetic** (there is **no
`language` parameter**): e.g. `grace-…` (female), `celia-…` (female), `pesa-…`
(male) — list them with `GET /voices` and pick one by the **man/woman** choice from
Phase 0. For guide narration use **`speed=0.75`, `t_shift=0.8`** (slightly slower
than the site default 0.85 — clearer for procedural content).

Recipe — one line of narration per segment in `texts.txt`, synthesised ON the host:
```
i=0; while IFS= read -r line; do [ -z "$line" ] && continue; i=$((i+1));
  curl -s -o /tmp/seg$i.wav -X POST http://5.9.49.171:8092/tts \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "text=$line" --data-urlencode "speed=0.75" \
    --data-urlencode "t_shift=0.8" --data-urlencode "voice=<voice-id>";
done < /tmp/texts.txt
```
Then **scp the wavs back and convert to mp3 locally** — `ffmpeg -i seg$i.wav -ac 1
-b:a 64k seg$i.mp3` — into the config's `audio_dir`. ⚠ The host has **no ffmpeg**,
so the wav→mp3 step runs on your machine. To re-do ONE segment, regenerate just
that clip and `docker cp` the single mp3 into the live `…/<slug>/audio/`.

### Non-English / a natural local-language voice

LuxTTS applies English phonetics to any text, so for a **non-English** guide that
must sound natural it isn't enough on its own. The path we used:
- **Clone a native voice in ElevenLabs** from a real recording of a native speaker,
  then synthesise the non-English segments with that voice id. Reaches
  "intelligible"; truly native prosody needs a speaker recorded in the language.
  (Keys live in your secrets store, never in the skill.) **Full recipe below.**
- **Meta MMS-TTS** has open voices for many languages (e.g. Sesotho `sot`) — a
  different, non-cloned voice but real language coverage.
- **Collect a native sample first** with the **counterpart-intake-page** companion
  (a branded page that records a local speaker reading your text) — feeds both the
  clone and a native-quality check.
- Bilingual page: keep one language as the base and add the second as per-segment
  overrides + a toggle (Phase 6).

#### Recipe — clone the site's own agent voice from a video (the path we shipped)

When the target site already has a presenter/agent on video, clone **that** voice so
the guide sounds like the site's own person — and use a **multilingual** model so a
French (or other non-English) guide is spoken natively, not English-phonetically.

1. **Extract the audio** from a video of the agent:
   ```
   ffmpeg -i in.mp4 -vn -ac 1 voice.mp3
   ```
   A clean ~1–3 min mono sample is plenty. Trim to passages where only the agent
   speaks (no music/overlap).
2. **Clone in ElevenLabs (Instant Voice Cloning, IVC)** — `POST /v1/voices/add`
   with the sample and `remove_background_noise=true`. Keep the returned `voice_id`.
   (Key from the secrets store; never in the skill or the page.)
3. **Synthesise with `eleven_multilingual_v2`** — this is the key: it speaks French
   (and other languages) **natively**, unlike LuxTTS's anglo-phonetic output. One
   request per narration segment → `audio/segN.mp3` (same convention as LuxTTS).
4. **Avatar from a video frame** — pull a still of the agent and crop it square for
   the bubble portrait:
   ```
   ffmpeg -ss <T> -i in.mp4 -frames:v 1 frame.png      # T = a good timestamp, e.g. 00:00:12
   ```
   then crop to a square and convert to webp (e.g. `cwebp` or any image tool) →
   `avatar.webp`, referenced from the config.

This is **in addition to LuxTTS** (the English default above), not a replacement —
pick the engine per the guide language.

### Conventions (any engine)
- Save clips as `audio/segN.mp3` (the builder lazy-loads them).
- **Re-voice a segment only when a WORD changes** — punctuation/spelling changes are
  inaudible (e.g. "licence"↔"license"), so fix the caption/body without re-voicing.
- **The agent's name is spoken** — changing it later means re-voicing every clip that
  says it (at least the intro). Back up the old clip; confirm the new one is non-silent.
- No LuxTTS access, or a different stack? Any TTS that returns audio for text works —
  produce `audio/segN.mp3` and the rest of the pipeline is unchanged.

## Phase 6 — Build the guided leaflet

> **⚠ Builder reconciliation — the build must come out brand-correct and in the page
> language, with NO manual post-pass.** The reference builder
> (`build-guided-leaflet.py`) **MUST** integrate (a) **i18n** — the widget chrome
> reads its labels from a config `labels` block (omit = English), and (b) the page's
> **`--brand-*` tokens** — the bubble/CTA/aura/ring inherit the page's own colours and
> font via `--guide-accent` / `--guide-font` (set `--guide-accent-rgb` for the glow).
> A build produced by ≥ 0.2.0 already comes out at the right brand and language.
> **Do NOT hand-edit the output to re-tint or re-translate it.** This is the root
> cause of a recurring bug: the OBFC-era builder hard-coded Lesotho indigo/green +
> English, so every build had to be re-tinted to GENERIC blue + Inter and Frenchified
> by hand — fragile, and a Python quote typo shipped the Comores SARL leaflet in
> Lesotho colours once. If you find yourself search-replacing colour hexes or button
> labels in a built page, STOP: fix the builder/config so the build is correct, don't
> patch the artifact. (Captured: `2 - eR services/knowledge/lessons.md`, Comores
> 2026-06-24 lesson 1 + 2026-06-25 lesson 8.)

Copy `guide-config.example.json` → `guide-config.json`, set `assistant_name`,
`avatar`, `input_html`, `output_html`, `audio_dir`, `audio_mode` ("url" = lazy,
recommended; "inline" = one self-contained file), the `anchors` (inject `id`s onto
the leaflet's section heads — match the exact strings), and the `segments`. Then:
```
python3 assets/build-guided-leaflet.py guide-config.json
```

**Language of the widget chrome (`labels`).** The widget's own buttons/labels —
*Ask*, *Pause*, *Resume*, *Dismiss*, *Re-open*, *"Hear … explain this"* — default
to **English**. On a non-English page they must match the page language (a French
page should not say "Ask Zalia"). Add a `labels` block to the config to override
any of them; omit it for English (back-compatible — a config with no `labels` keeps
the English defaults). Keys: `ask`, `resume`, `pause`, `dismiss`, `reopen`, `hear`
(use `{name}` for the agent name). French example:
```json
"labels": { "ask": "Demander à", "resume": "Reprendre", "pause": "Pause",
            "dismiss": "Fermer", "reopen": "Rouvrir",
            "hear": "Écouter {name} expliquer" }
```

**The widget inherits the brand automatically — no re-tint pass.** Its CSS reads
the page's `--brand-*` tokens (via `--guide-accent` / `--guide-font`), so the
bubble, CTA, aura and ring come out in the **page's own colours and font** with no
manual editing. If you set `--brand-primary` on the page, also set
`--guide-accent-rgb` (the same colour as an `r,g,b` triplet) so the aura/ring glow
matches — otherwise the glow falls back to the slate default. Un-tokenised pages
still get a legible fallback.

Verify headless: one replay button per targeted segment, widget bottom-right, no
console errors, `@media print` hides it, and the chrome reads in the page language.

**Bilingual / clickability gotcha (if you add a language toggle):** the caption
bubble is `pointer-events:none` (so it doesn't block the page); a control placed
inside it inherits that and becomes unclickable — re-enable just that control
(`#...caption.show #lang { pointer-events:auto }`). And test toggles with a **real
hit-tested click** (`document.elementFromPoint`), not `el.click()` — the latter
bypasses hit-testing and gives false greens.

## Phase 7 — Deploy

Per the user's Phase 0 answer. If it's a static-page host, drop a dir with
`index.html` (+ `audio/`). If pages are served from inside a container/app image,
they may be **wiped on redeploy** — the companion `restore-asset-watcher` pattern
keeps a copied-in page alive across restarts (optional). State the change and
confirm before publishing to anything live.

---

## Conventions

- **Version, don't overwrite** a deployed page — ship a new slug/file.
- **Trace every claim** to a source the user gave; never invent facts or legal values.
- **No em dashes** in body or captions unless the user wants them; an em-dash-only
  caption fix is inaudible (no re-voice).
- The bundled `avatar-default.webp` and the default token values are
  just starting points — Phase 1 replaces the look, Phase 0 the name/voice.

## Playbooks / domaines (la substance, séparée de la méthode)

This skill is the **method**; reusable domain substance lives in playbooks it consumes:

- **OHADA company/legal-form leaflets** → `2 - eR services/knowledge/ohada-formes-juridiques-playbook.md`
  (the 5 OHADA forms — entreprenant · commerçant personne physique · SARL · SAS · SA —
  with their articles + the transversal patterns: spouse/matrimonial regime, taxation
  physical-person vs company, and the comparison logic; an "OHADA shared vs national
  overlay" table; the Comores leaflet ecosystem as the worked example). Organised by
  legal system (OHADA), not by country or language — reusable across the 17 OHADA states.

## Companions (separate skills, optional)

- **counterpart-intake-page** — a page to collect a native speaker's voice sample /
  answers (useful when sourcing a guide voice in a local language).
- **restore-asset-watcher** — keep a docker-cp'd page alive across redeploys.

## Changelog

- **0.3.0** (2026-06-29) — Added **Ecosystem chrome** (Phase 3): the shared layout used when
  building a *family* of leaflets for one country, captured from the final Comores ecosystem
  (7 live pages). Six conventions: (1) **flag ribbon** — a thin striped top band in the host
  country's flag colours; (2) **common footer** — full-bleed `--brand-primary`, white text, a
  three-column grid with an **inter-fiche nav** (current page `aria-current`/bold) and partner
  logos **whitened in CSS** (`filter:brightness(0) invert(1)`) from a `/logos/` route; (3) a
  **greffe variant footer** for internal/back-office sheets (white, one-line sibling nav, small
  `un-emblem.svg` + formal note); (4) **title conventions** — "Comprendre le statut de…" for a
  single-form explainer vs "Choisir la forme juridique…" for the chooser-hub; (5) the
  **ecosystem linking rule** — hub (all forms) vs comparison (exactly two named forms) are
  distinct destinations, a generic link goes to the hub, a "compare X and Y" link only where
  both are in play, and a late-added form is back-linked into its siblings; (6) `text-wrap:
  balance` on hero titles from the start.
- **0.2.2** (2026-06-25) — Added an explicit **builder reconciliation** note at the top of
  Phase 6: the reference builder MUST integrate i18n (`labels`) + the page `--brand-*`
  tokens so a build comes out brand-correct and in the page language with **no manual
  post-pass** — never hand-edit a built page to re-tint or re-translate it (root cause of
  a recurring bug; the Comores SARL leaflet shipped once in Lesotho colours after a manual
  pass). Captured from the final Comores campaign (6 leaflets — entreprenant · commerçant
  PP · SARL · SAS · comparison · the `/formes-juridiques` home page — all Zalia-narrated).
- **0.2.1** (2026-06-24) — Added a **Playbooks / domaines** section pointing to the OHADA
  legal-form playbook (`2 - eR services/knowledge/ohada-formes-juridiques-playbook.md`) —
  the reusable substance (5 forms + articles + transversal patterns) that this method
  consumes, with the Comores leaflet ecosystem as the worked example.
- **0.2.0** (2026-06-24) — Four lessons from a real campaign (Comores
  entreprenant/SAS/SARL + the "Zalia" French voice guides):
  1. **i18n widget chrome** — the builder no longer hard-codes English on the bubble
     (Ask / Pause / Resume / Dismiss / Re-open / "Hear … explain this"). A config
     `labels` block overrides them per language; omit it for English (back-compatible).
  2. **Widget inherits the brand** — its CSS now reads `--brand-*` (via `--guide-accent`
     / `--guide-font`) instead of the hard-coded OBFC indigo/green/Poppins, so a build
     comes out in the page's own colours/font with no manual re-tint pass.
  3. **Comparison / which-one mode** — new `comparison-template.html` (hero · two-level
     "big difference" · colour-coded matrix that stacks to cards ≤820px · pros/cons ·
     "which fits you?" · links), brand-neutral, driven by `--brand-*` + `--cat-{key}-*`.
  4. **Voice-clone-from-video recipe** (Phase 5) — extract audio with ffmpeg → clone in
     ElevenLabs (IVC, `remove_background_noise=true`) → synthesise with
     `eleven_multilingual_v2` (native French, vs LuxTTS anglo-phonetic) → avatar from a
     video frame. Added alongside LuxTTS, not replacing it.
- **0.1.0** — Initial generalised brand-matched leaflet + voice-guide builder.
