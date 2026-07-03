# screens-first-design

A complete method for defining a product's UX **screen by screen** — with clickable mobile mockups as the primary deliverable, not wireframes or written specs.

The method was proven on a full product design: 8 screens + guided tour + team presentations produced in one day (2026-07).

## Who it is for

Anyone who needs to take a product idea (or a module of an existing product) from "we know roughly what it should do" to a **reviewable, presentable, clickable set of screens** — service designers, product owners, and developers preparing a build.

## What it contains

| Path | What it is |
|------|------------|
| `skills/screens-first-design/SKILL.md` | The full method: invariant schema → mockup + fiche per screen → parallel agents → preview verification → single voice → compendium → decisions journal → pre-verbal check |
| `assets/reference-mockup.html` | A generic, self-contained MOBILE starter mockup that embodies the CSS/JS grammar agents copy from — every block commented `grammar: …` |
| `assets/reference-mockup-desktop.html` | The DESKTOP starter: app frame 1280×800, sidebar navigation, master–detail, right sliding panels, centered modal for solemn confirmations — same tokens, same commenting |
| `assets/build-docs.py` | The compendium generator: renders every fiche + the decisions journal into ONE indexed, collapsible `docs.html` |
| `docs/design-principles.md` | The pre-verbal principle (a.k.a. the Teletubbies principle): definition, register guard-rail, the 5-second test, six operational controls |
| `docs/agent-prompts.md` | Prompt templates: the per-screen agent, the in-flight correction, the team-presentation agent, the desktop conversion agent |

## Quickstart

1. Ask Claude: "let's define the screens for [product]" — the skill triggers.
2. Answer the interview questions; the invariant page schema is written first (`ux-pattern.md`).
3. Review the first mockup + fiche; then parallel agents produce the remaining screens from the bundled reference grammar.
4. Run `python3 build-docs.py` in your design folder to regenerate `docs.html` — the single door to everything.
5. Before any screen is shown, it passes the pre-verbal check (`docs/design-principles.md`).

Mobile first, desktop derives: after the mobile content review, the desktop versions (`NN-slug-desktop.html`) are derived from the reviewed mobile screens using the bundled desktop grammar — see the skill's "Desktop derivation" section.

## Requirements

- `python3` + the `markdown` package (`pip install markdown`) for `build-docs.py`
- No MCP servers required — this plugin is method + assets only
