---
description: Produce a traced, journey-shaped "what this service IS / how it works" brief from the law + the live BPA service
argument-hint: [service-id] [instance]
allowed-tools: [Read, Write, Bash]
---

# Service journey brief

Produce a journey-shaped conceptual content map for service `$ARGUMENTS` — a service
with **no legal-form types to compare** (a permit, certificate, filing, registration) —
by cross-reading the **law** and the **live BPA service** and reconciling them.

Follow the `service-journey-brief` skill in this plugin
(`skills/service-journey-brief/SKILL.md`): map the flow/steps (Phase 1), pull what the
citizen provides (Phase 2) and what is issued (Phase 3), **reconcile law vs the live
service** (Phase 4), and write one traced journey map from the template (Phase 5),
organised purpose → who it's for → what you provide → the steps → what you receive →
obligations after.

For a service whose branches ARE legal forms (company types), use `service-concept-brief`
instead. Output feeds `service-leaflet` (and manuals/training); it renders nothing public.
