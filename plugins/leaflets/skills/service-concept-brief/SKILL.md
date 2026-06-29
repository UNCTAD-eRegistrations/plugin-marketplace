---
name: service-concept-brief
description: >
  For a service that has several types/branches (e.g. private vs public vs non-profit
  company, or any application-type branch), produce a clear, conceptual, plain-language
  "what each type IS" brief — derived by cross-reading the LAW (Act + Regulations) and
  the LIVE BPA service form branch, reconciling the two, and tracing every claim to a
  law section or a form component. Use before writing leaflets, manuals, training, or
  design docs for a multi-type service, or whenever you need a grounded conceptual model
  of each branch. Output is a per-type traced content map (the source of truth those
  artifacts consume). Generalises the OBFC leaflet method.
metadata:
  version: 0.3.0
---

# service-concept-brief — conceptual "what each type IS", from law + the live service

Produces, per type/branch of a service, a **content map**: an at-a-glance fact box plus
the type explained **conceptually ("what it IS")**, with **every claim traced to a law
section OR a `form_component_get`**, law-vs-system differences flagged, and over-claims
legally vetted/softened. It renders nothing public — it produces the **grounded source
of truth** that `service-leaflet`, manuals, training, and design docs consume.

This generalises the method previously embedded in the OBFC leaflet builder (its
ground-in-law → cited-legal-facts → pull-the-form-branch → traced-content-map phases),
made country/service-agnostic and callable on its own.

## What it reuses (don't re-derive)

- **`legal-brief-for-company`** — the **law half**: section-cited, conceptually-organised
  legal facts per type. Call it (or run its cited-extraction subagent).
- **`service-manual`** branch detection (`service_branches`) + **`service-review`**
  determinant→branch matrix — to **enumerate the types** and pull each one's gated branch.
- **`service-coherence-method`** tracing discipline — **every claim cites** an MCP tool
  result or a law section; nothing asserted from memory.
- **`assets/content-map-template.md`** — the output layout (the OBFC `governance-content-map`
  generalised).

Downstream/siblings: `service-leaflet` & `obfc-company-leaflet` **consume** the map this
produces; `new-company-type` is the **build sibling** (it creates the branch this explains).

## Connecting to BPA

Before any tool call:
1. If the instance is unknown, `mcp__BPA__instance_list()`.
2. Check auth: `mcp__BPA__connection_status(instance="{name}")`.
3. If not authenticated → `mcp__BPA__auth_login(instance="{name}")`, wait for success.

Pass `instance="{name}"` to every `mcp__BPA__*` call.

## Intake (ask, then wait)

1. **Service** — id + instance, and which **types/branches** (or "all of them").
2. **Law** — the Act + Regulations (files, or existing digests in the project's `law/`
   folder). If none exist, produce them first (`legal-brief-for-company`).
3. **Language** of the brief, and where to write the output.

## Phase 1 — Enumerate the types + their gates

Call `mcp__BPA__service_branches` (and inspect the type classification + its determinants,
as `service-review` does) to list each type and the **determinant that gates it**. Confirm
the classification values; note any "catch-all"/negative-gated branch. This is the index
of briefs to produce.

**Law-only mode (no live service).** If a type is not built in BPA yet (no form branch to
pull), **skip Phases 1 and 3 entirely** and build the map from the law half alone — mark
every would-be form line as `NO LIVE FORM`. Phase 4 then reconciles **law against law**
(Act vs Regulations vs national texts) instead of law against form. This is the normal mode
when the brief drives a leaflet for a status the country has not yet digitised (e.g. an
OHADA status like the *entreprenant* or *SAS* that no live service implements).

## Phase 2 — Law half, per type  *(subagent)*

For each type, get from the Act + Regulations, **with section citations**: legal status
(separate person? perpetual succession?), **liability**, **minimum capital**, **min/max
members/shareholders**, **min directors**, what makes it *this* type, **name rules/suffix**,
**registered office**, and the **governance thresholds**. Read EVERY relevant law file —
surveys accumulate; reading one of several re-derives (worse) analysis that exists. Never
invent a legal value — mark **"NOT FOUND"**.

**Scanned sources — read with vision, never trust a failed OCR.** If a law / decree / arrêté
is a scanned image and OCR comes back empty or garbled, **read it page-by-page with the
vision-capable Read tool before concluding anything**. A tooling failure (bad OCR) must NEVER
harden into a content claim — "not found", "no national procedure", "OCR best-guess". Decrees
and arrêtés are short (a few pages); read them all. (Comores: the *entreprenant*'s entire
national procedure was nearly missed because a 5-page scanned arrêté was dismissed as "OCR
poor" instead of being read by eye.)

**Read the primary source page-by-page — never rely on a summary or one umbrella text.**
A national text often *adds* or *organises* something the umbrella law would make you
think is absent. Read the actual Act/decree/arrêté in full, not a digest of it, before
asserting "the law does not provide X". (Comores: a national **arrêté** on **SARL capital**
explicitly organised the **apport en industrie** — which a reading of the OHADA **AUSCGIE
alone** would have wrongly reported as "not provided for". The umbrella text was silent;
the national text was not.) When two texts speak to the same point, read both and reconcile
(Phase 4) rather than trusting the more general one.

## Phase 3 — Service half, per type  *(subagent)*

Pull the **determinant-gated form branch** via `form_component_get` → what the service
actually captures/shows for this type: the entity block, the owners/members tab, the
directors tab, the governance tabs, the articles tab, and the **result/print documents**.
Return verbatim, each item traced to its **component key**.

## Phase 4 — Reconcile (the net-new core)

Cross-read the law against the live branch:
- **Confirm** each conceptual claim against BOTH sources.
- **Flag law-vs-system differences** ("the law says X; the form does Y").
- **Separate presentation from law** — don't state a designer's framing as if it were
  statute (e.g. "members = shareholders renamed" is a presentation choice, not pure law).
- **Skeptically vet + soften** over-claimed or locally-provocative lines against the
  **primary** Act/Regs, and cite the correct source.
- **"What you receive" = read the actual print documents**, not bot mappings or memory.
- **Reason from consequence, not just statutory text.** When two legal facts interact, carry
  the interaction through to its practical result for the applicant — don't list both raw and
  stop. Canonical trap: a type with **no minimum capital** (e.g. OHADA SAS, art.853-5) **voids
  the SA-style capital machinery** — no mandatory blocked deposit, no subscription/payment
  declaration (DNSV), no ¼-release proof as a condition of formation. Writing "no minimum
  capital" AND "capital must be paid up / DNSV required" side by side, unreconciled, is the
  failure mode; once the first holds, the second is moot (a textual residue applies only *if*
  there are cash contributions, and even then is not a structural hurdle). State the "so, for
  the applicant, this means…".
- **Never import one type's formality onto another.** A document or step taken from one
  branch's dossier (e.g. the SARL/SA deposit + DNSV) must be **re-verified against the target
  type** before it appears in that type's map. Cross-type contamination is a top source of
  false requirements.

## Phase 5 — Write the content map, per type

One file per type from `assets/content-map-template.md`. Organise by **what the type IS**
— an at-a-glance fact box + ordered conceptual parts — **NOT** by law order and **NOT** by
form field order. End **every line** with its source: `LAW §…` or `FORM <component key>`.
Add a short **"law vs system"** section for the reconciliation notes. This file is the
deliverable and the source of truth any downstream artifact (leaflet, manual, training)
consumes.

### Optional deliverable — the inter-type comparison column

When the brief covers **several types** and a **comparison leaflet** is planned (the
`service-leaflet` "which-one mode"), also produce a small **comparison matrix**: one
**row per dimension** that actually differs across the types (legal personality,
liability, minimum capital, min/max members, min directors, name suffix, governance
threshold, what you receive), one **column per type**, each cell still ending with its
`LAW §…` / `FORM …` source. This is the **N traced differences** distilled — it drops
straight into the comparison template's matrix rows, already sourced, so the leaflet
never re-derives (or invents) a difference. Only include rows where the types genuinely
diverge; identical rows belong in each per-type map, not the comparison.

## Conventions

- **Trace or mark-confirm — confirmed discipline.** Every single claim ends with its source
  (`LAW §…` or `FORM <key>`); anything you can't source is marked **"not found / to confirm"**,
  never filled from intuition or a plausible-sounding default. A leaflet built on this map
  inherits the trace, so an un-sourced line here becomes an invented fact downstream. This is
  the non-negotiable spine of the skill (validated on the Comores leaflets — every entreprenant /
  SAS / SARL claim traced back to an article or a form component before it shipped).
- **Conceptual order beats source order.**
- **Legal-vet bold claims; presentation ≠ law.**
- **Read primary sources page-by-page; don't trust a summary or one umbrella text** (Phase 2).
- **Delegate the big reads** (law files, form branches) to subagents; keep the main context
  for the reconciliation and the writing.

## Changelog

- **0.3.0** (2026-06-24) — Three additions from the Comores entreprenant/SAS/SARL campaign:
  (a) **confirmed the trace-or-mark discipline** as the skill's non-negotiable spine (every
  claim sourced; un-sourced → "to confirm", never invented — an un-sourced line becomes an
  invented downstream fact). (b) Phase 2 rule — **read primary sources page-by-page, never
  rely on a summary or one umbrella text**: a national arrêté on SARL capital organised the
  *apport en industrie* that the OHADA AUSCGIE alone would have wrongly reported as "not
  provided for". (c) **Optional inter-type comparison column** (Phase 5) — the N traced
  differences as a matrix (row per differing dimension, column per type, each cell sourced),
  which feeds the `service-leaflet` comparison / which-one mode directly.
- **0.2.0** (2026-06-22) — Added **law-only mode** (Phase 1) for types with no live BPA form
  (build the map from the law alone, reconcile law-vs-law). Added two Phase 4 rules:
  **reason from consequence** (interacting legal facts must be carried to their practical
  result — e.g. "no minimum capital" voids the SA-style deposit / DNSV / subscription
  machinery) and **never import one type's formality onto another** without re-verifying.
  Born from the Comores *entreprenant* + *SAS* leaflets (a literal statutory reading had
  wrongly presented DNSV / ¼-release as blanket SAS requirements). Also added a Phase 2 rule —
  **read scanned sources with vision** — after a 5-page scanned arrêté was wrongly dismissed as
  "OCR poor", nearly losing the entreprenant's national procedure.
- **0.1.0** — Initial: conceptual "what each type IS" brief from law + live form, generalised
  from the OBFC leaflet method.
