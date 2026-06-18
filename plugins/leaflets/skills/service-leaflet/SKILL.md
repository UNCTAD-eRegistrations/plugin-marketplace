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
- `brand.css` — the token reference (the full `--brand-*` / `--cat-*` set).
- `build-guided-leaflet.py` — injects the voice guide into a finished leaflet.
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

**If the service has multiple types/branches, or you want a law-grounded model, run the
`service-concept-brief` skill first** — it produces the per-type traced content map (the
law + the live form, reconciled, every claim sourced) that this phase consumes. For a
simple single-type page, build a lightweight content map inline instead.

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
**distinctive** thing about this service. Add a top-right **Print / PDF** button +
print CSS for a clean branded PDF. Verify headless (no console errors, no overflow
at 1280 and 390).

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
- **Clone a native voice in ElevenLabs** from a real recording of a native speaker
  (model `eleven_v3`), then synthesise the non-English segments with that voice id.
  Reaches "intelligible"; truly native prosody needs a speaker recorded in the
  language. (Keys live in your secrets store, never in the skill.)
- **Meta MMS-TTS** has open voices for many languages (e.g. Sesotho `sot`) — a
  different, non-cloned voice but real language coverage.
- **Collect a native sample first** with the **counterpart-intake-page** companion
  (a branded page that records a local speaker reading your text) — feeds both the
  clone and a native-quality check.
- Bilingual page: keep one language as the base and add the second as per-segment
  overrides + a toggle (Phase 6).

### Conventions (any engine)
- Save clips as `audio/segN.mp3` (the builder lazy-loads them).
- **Re-voice a segment only when a WORD changes** — punctuation/spelling changes are
  inaudible (e.g. "licence"↔"license"), so fix the caption/body without re-voicing.
- **The agent's name is spoken** — changing it later means re-voicing every clip that
  says it (at least the intro). Back up the old clip; confirm the new one is non-silent.
- No LuxTTS access, or a different stack? Any TTS that returns audio for text works —
  produce `audio/segN.mp3` and the rest of the pipeline is unchanged.

## Phase 6 — Build the guided leaflet

Copy `guide-config.example.json` → `guide-config.json`, set `assistant_name`,
`avatar`, `input_html`, `output_html`, `audio_dir`, `audio_mode` ("url" = lazy,
recommended; "inline" = one self-contained file), the `anchors` (inject `id`s onto
the leaflet's section heads — match the exact strings), and the `segments`. Then:
```
python3 assets/build-guided-leaflet.py guide-config.json
```
The widget inherits the brand automatically (its CSS reads the same `--brand-*`
tokens). Verify headless: one replay button per targeted segment, widget
bottom-right, no console errors, `@media print` hides it.

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

## Companions (separate skills, optional)

- **counterpart-intake-page** — a page to collect a native speaker's voice sample /
  answers (useful when sourcing a guide voice in a local language).
- **restore-asset-watcher** — keep a docker-cp'd page alive across redeploys.
