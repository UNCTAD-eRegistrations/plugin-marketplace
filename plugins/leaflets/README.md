# leaflets

Build **brand-matched applicant leaflets** (explainer pages) for any online or
government service — each with an optional **named voice guide** that narrates the
page (a fixed bubble: auto-scroll, highlight, captions, replay per section).

This is a generalisation of an earlier single-registry leaflet builder. Nothing is
hardcoded to one registry:

- **The look is matched to a site you point at.** Give it a URL (it reads the
  site's bundled CSS for colours/fonts/logo) or screenshots, and it fills a
  `--brand-*` token set so the leaflet looks like that site.
- **The voice guide is yours.** You choose its **name** and a **man or woman voice**;
  the guide can also be turned off for a plain static leaflet.
- **Plumbing is asked, not assumed** — TTS engine, deploy target, and where the
  service content comes from are intake questions.

## Skills

- **service-leaflet** (`/service-leaflet`) — the 8-phase pipeline: intake → acquire
  brand → gather content → build leaflet → narration → voice audio → build guided
  version → deploy. See `skills/service-leaflet/SKILL.md`.
- **service-concept-brief** (`/service-concept-brief`) — upstream: produces a traced,
  conceptual "what each type IS" content map per service branch, by cross-reading the
  **law** and the **live BPA service** and reconciling them. The source of truth the
  leaflet consumes (Phase 2); also feeds manuals, training, and design docs. See
  `skills/service-concept-brief/SKILL.md`.

## Assets

| File | Purpose |
|---|---|
| `assets/document-template.html` | Flowing-document layout, `--brand-*` token-driven |
| `assets/poster-template.html` | Side-by-side comparison/teaching layout (two-category coding) |
| `assets/brand.css` | The `--brand-*` / `--cat-*` token reference |
| `assets/build-guided-leaflet.py` | Injects the voice guide into a finished leaflet |
| `assets/guide-config.example.json` | Worked builder config |
| `assets/avatar-default.webp` | Placeholder guide portrait (swap it) |

## Requirements

- A static-page host (or just take the generated files).
- A text-to-speech engine **only if** you want the voice guide — the skill ships the
  **LuxTTS** recipe we use (endpoint, voices, params, the convert step) plus
  non-English voice-clone fallbacks (ElevenLabs / Meta MMS-TTS); or point at your
  own. The leaflet works without a guide.

## Companions (other plugins/skills, optional)

- **counterpart-intake-page** — collect a native speaker's voice sample / answers
  (useful when sourcing a guide voice in a local language).
- **restore-asset-watcher** — keep a `docker cp`'d page alive across redeploys.
