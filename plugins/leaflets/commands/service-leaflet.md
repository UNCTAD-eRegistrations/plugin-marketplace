---
description: Build a brand-matched applicant leaflet (+ optional voice guide) for a service
argument-hint: [service name or target site]
allowed-tools: [Read, Write, Bash, WebFetch]
---

# Service leaflet builder

Build a brand-matched applicant leaflet for `$ARGUMENTS`.

Follow the `service-leaflet` skill in this plugin (`skills/service-leaflet/SKILL.md`).

Begin with **Phase 0 intake** — ask the user and wait for:
1. the **target site** to match the look of (a link, or screenshots/images);
2. whether to include a **voice guide**, and if so its **name**, a **man or woman voice**, and the **language** it speaks;
3. the **service** the leaflet is about and where its content comes from;
4. **plumbing** (TTS engine, deploy target) — only what's needed.

Then proceed through Phases 1–7 in the skill.
