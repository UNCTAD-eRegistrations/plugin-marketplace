---
description: Diagnose and repair a country instance that is out of sync with the Global Translation Service
argument-hint: [instance]
effort: low
allowed-tools: [mcp__Translations__translation_global_status, mcp__Translations__translation_global_reload, mcp__BPA__auth_login]
---

# Translations Fix

Operator-friendly shortcut that replaces the old SSH + curl recovery runbook. Diagnoses whether the target instance needs a Global Translation pull, then — with operator confirmation — runs the reload.

Arguments: `$ARGUMENTS`

## Instructions

1. Resolve the target instance from `$ARGUMENTS`. If none provided, ask the operator which instance to fix.

2. Call `translation_global_status(instance="<name>")`.

3. **If `reload_recommended=false`:**
   - Report: *"Instance is already in sync with the Global Translation Service. No action needed."*
   - Show the `sample_resolved` values as proof.
   - Stop.

4. **If `reload_recommended=true`:**
   - Show the missing keys and the recommendation.
   - Ask the operator: *"Run translation_global_reload on `<instance>`? This pulls from the Global Translation Service and takes 10–30 seconds. (yes/no)"*
   - On `yes`, call `translation_global_reload(instance="<name>")`.
   - On `no`, report that no changes were made.

5. After reload, report `created`, `updated`, `duration_ms`, and `audit_id`. Suggest running `/translations-mcp:status <instance>` to verify.

## Usage

```
/translations-mcp:fix lesotho2
/translations-mcp:fix              # prompts for instance
```

## Notes

- `translation_global_reload` is an **audited write**. The audit record ties the reload to the authenticated operator.
- The operator must have the translation admin role in the instance's Keycloak realm (e.g. `LS` for Lesotho).
- Reload iterates every active language and reconciles BPA, DS, and STATISTICS translation domains in one backend call. The cache is reloaded automatically — no separate `reload_cache` is required.
- `Created 0 / updated 0` is a normal success on an already-synced instance; the backend merges inline during the sweep. Re-run `/translations-mcp:status` to confirm the UI probe keys now resolve.
