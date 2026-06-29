---
name: service-journey-brief
description: >
  For a single (non-entity-type) service, produce a clear, conceptual, plain-language
  "what this service IS and how it works" brief — organised by the citizen journey
  (purpose → who it's for → what you provide → the steps → what you receive →
  obligations after) — derived by cross-reading the LAW/regulation and the LIVE BPA
  service and reconciling them, every claim traced to a law section or a form/flow
  component. Use before writing a leaflet, manual, or training for a service that has
  NO legal-form types to compare (a permit, a certificate, a filing, a registration).
  The journey counterpart to service-concept-brief. Output is a traced journey map (the
  source of truth those artifacts consume).
metadata:
  version: 0.1.0
---

# service-journey-brief — conceptual "what this service IS / how it works", from law + the live service

Use this when a service has **no entity-type variants** to compare (use
`service-concept-brief` for services whose branches are legal forms). It produces a
**journey-shaped content map** — purpose → who it's for → what you provide → the steps →
what you receive → obligations after — with **every claim traced to a law section OR a
form/flow component**, law-vs-system differences flagged, over-claims softened. It
renders nothing public — it's the **grounded source of truth** a leaflet/manual/training
consumes.

Sibling of `service-concept-brief`: same tracing discipline and template family; the
only difference is the spine — **journey, not type**.

## What it reuses (don't re-derive)

- **`service-coherence-method`** tracing discipline — every claim cites an MCP result or a law section.
- **`service-review`** + `workflow_graph` — the **ordered flow** of desks/registrations (the "steps").
- **`form_component_get`** + **`documentrequirement_list`** — what the citizen must **provide**.
- **`print_document_list`** + the result registrations — what's **issued** ("what you receive").
- **`legal-brief-for-company`** (or a plain law digest) — the **governing regulation** (eligibility, obligations).
- **`assets/journey-map-template.md`** — the output layout.

Downstream: `service-leaflet`, manuals, and training consume the map. Sibling:
`service-concept-brief` (the entity-type version).

## Connecting to BPA

Before any tool call:
1. If the instance is unknown, `mcp__BPA__instance_list()`.
2. Check auth: `mcp__BPA__connection_status(instance="{name}")`.
3. If not authenticated → `mcp__BPA__auth_login(instance="{name}")`, wait for success.

Pass `instance="{name}"` to every `mcp__BPA__*` call.

## Intake (ask, then wait)

1. **Service** — id + instance.
2. **Governing law/regulation** — the file or an existing digest, if one governs the service.
3. **Language** of the brief, and where to write the output.

## Phase 1 — Map the journey (the steps)

Pull the service flow (`workflow_graph` / the registrations + roles in order, as
`service-review` does): the desks/stages the file passes through, the applicant tabs, and
who acts at each. This ordered flow is the spine of the brief.

## Phase 2 — What you provide (requirements)  *(subagent)*

`form_component_get` + `documentrequirement_list` → the **fields, documents, and
eligibility determinants** the citizen must satisfy; cross-check conditions against the
law. Trace each to its component key or law section. Never invent — mark **"confirm"**.

## Phase 3 — What you receive  *(subagent)*

`print_document_list` + the result registrations → the **certificates / records issued**.
Read the **actual print documents**, not bot mappings or memory.

## Phase 4 — Reconcile (the net-new core)

Cross-read the law against the live service:
- **Confirm** each claim against BOTH sources.
- **Flag differences** ("the law requires X; the form asks Y" / "the law sets a deadline the service doesn't enforce").
- **Separate presentation from law** — don't state a service-design choice as if it were statute.
- **Soften over-claims** against the primary regulation, citing the right source.
- **Obligations-after** come from the law (renewals, displays, reporting).

## Phase 5 — Write the journey map

One file from `assets/journey-map-template.md`, organised as: **what it's for** (purpose)
→ **who it's for** (eligibility) → **what you provide** (requirements) → **the journey**
(steps in order) → **what you receive** → **obligations after**. End **every line** with
its source: `LAW §…`, `FORM <component key>`, or `FLOW <desk/registration>`. This file is
the deliverable and the source of truth any downstream artifact consumes.

## Conventions

- **Trace or mark-confirm.** Every claim cites a source; unknowns are "confirm", never invented.
- **Journey order, plain language.** Organise by the citizen's path, not the form's field order.
- **Presentation ≠ law.** Flag, don't assert.
- **Delegate the big reads** (law files, form, flow) to subagents; keep the main context for reconciliation and writing.
