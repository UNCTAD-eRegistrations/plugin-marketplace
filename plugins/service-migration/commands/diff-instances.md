---
description: Compare the same service across two BPA instances to find configuration drift
argument-hint: <service-id> <server-a> <server-b>
allowed-tools: [Read, Write, Bash]
---

# Instance Diff

Compare service `$ARGUMENTS` across two BPA instances.

## Instructions

1. Export service from both instances via `service_to_yaml`
2. Run a structured diff: fields added/removed/changed, determinants, roles, costs
3. Report:

```
Service: Business Registration (ID varies per instance)

Fields:          Source has 24, Target has 22 — 2 removed, 0 added
Determinants:    Source has 15, Target has 17 — 0 removed, 2 added
Roles:           Identical (4 roles)
Costs:           Source: $50 fixed | Target: $45 fixed  ← DIFFERS
Print docs:      Source has 2, Target has 1             ← DIFFERS
```

Use this to track what diverged after a migration, or to audit consistency across deployments.

## Usage

```
/diff-instances 42 BPA-jamaica BPA-lesotho2
```
