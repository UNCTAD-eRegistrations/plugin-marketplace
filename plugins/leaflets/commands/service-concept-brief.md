---
description: Produce a traced, conceptual "what each type IS" brief from the law + the live BPA service
argument-hint: [service-id] [instance]
allowed-tools: [Read, Write, Bash]
---

# Service concept brief

Produce a per-type conceptual content map for service `$ARGUMENTS`, derived by
cross-reading the **law** and the **live BPA service** and reconciling them.

Follow the `service-concept-brief` skill in this plugin
(`skills/service-concept-brief/SKILL.md`): enumerate the types/branches, get the
section-cited legal facts (Phase 2), pull each type's determinant-gated form branch
(Phase 3), **reconcile law vs the live form** (Phase 4), and write one traced content
map per type from the template (Phase 5).

Output feeds `service-leaflet` (and manuals/training/design docs). It produces the
source-of-truth content map; it does not render anything public.
