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
  version: 0.1.0
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

## Phase 2 — Law half, per type  *(subagent)*

For each type, get from the Act + Regulations, **with section citations**: legal status
(separate person? perpetual succession?), **liability**, **minimum capital**, **min/max
members/shareholders**, **min directors**, what makes it *this* type, **name rules/suffix**,
**registered office**, and the **governance thresholds**. Read EVERY relevant law file —
surveys accumulate; reading one of several re-derives (worse) analysis that exists. Never
invent a legal value — mark **"NOT FOUND"**.

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

## Phase 5 — Write the content map, per type

One file per type from `assets/content-map-template.md`. Organise by **what the type IS**
— an at-a-glance fact box + ordered conceptual parts — **NOT** by law order and **NOT** by
form field order. End **every line** with its source: `LAW §…` or `FORM <component key>`.
Add a short **"law vs system"** section for the reconciliation notes. This file is the
deliverable and the source of truth any downstream artifact (leaflet, manual, training)
consumes.

## Conventions

- **Trace or mark-confirm.** Every claim cites a source; unknowns are "confirm", never invented.
- **Conceptual order beats source order.**
- **Legal-vet bold claims; presentation ≠ law.**
- **Delegate the big reads** (law files, form branches) to subagents; keep the main context
  for the reconciliation and the writing.
