---
description: Wipe ALL applicant files + Camunda processes for a DS instance (super_mario only, destructive)
argument-hint: <instance>
effort: high
allowed-tools: [mcp__DS__applicant_file_cleanup, mcp__DS__ds_health, mcp__DS__instance_list, mcp__DS__ds_auth_login]
---

# DS Cleanup — wipe applicant files

Wipe **ALL** applicant `File` data and the matching Camunda processes for a DS instance.
**Destructive and irreversible.** Removes every File plus its PaymentTransactions, Certificates
and Documents (incl. their MinIO blobs) and linked BusinessEntities, and deletes the matching
Camunda process instances + history. Restricted to the `super_mario` role.

Arguments: `$ARGUMENTS` — the instance profile name (e.g. `jamaica`).

## Connecting to DS

Before any tool call:
1. If the instance is unknown, call `instance_list()` to see registered profiles.
2. Check health/auth: `ds_health(instance="<name>")`. If auth fails, call
   `ds_auth_login(instance="<name>")`, wait for success, then retry.

Pass `instance="<name>"` to every `mcp__DS__*` call.

## Instructions

1. Resolve the instance from `$ARGUMENTS[0]`. If it is missing, ask which instance — never guess
   for a destructive wipe.

2. **Dry run first** (the tool defaults to `dry_run=true`, so this changes nothing):
   ```
   applicant_file_cleanup(instance="<name>")
   ```
   Present the returned `summary` as a table: Files, Camunda processes, PaymentTransactions,
   Certificates, Documents, BusinessEntities — and surface the instance `SYSTEM_CODE`.

3. **Confirm with the user.** Restate that this is irreversible, recommend a DB backup, and wait
   for an explicit "yes". Do not proceed otherwise.

4. **Execute** only after confirmation, passing the `SYSTEM_CODE` from the dry-run summary:
   ```
   applicant_file_cleanup(instance="<name>", dry_run=false, confirm="<SYSTEM_CODE>")
   ```
   Report the `camunda` (ok/failed) and `deleted` (per-model) counts from the response.

5. Optional flags the user may request:
   - `camunda_only=true` — delete only the Camunda processes (verify access before the DB wipe).
   - `skip_camunda=true` — wipe the database only; leave Camunda untouched.
   - `keep_business_entities=true` — keep the BusinessEntity rows linked to the wiped files.

## Notes

- Requires the `super_mario` role; a non-super_mario caller gets HTTP 403.
- The backing endpoint (`POST /backend/admin/cleanup-applicant-files`) exists only on ds-backend
  builds that include the cleanup feature (develop / release/2.18+). Older instances return 404 —
  the ds-backend build must be deployed there first.
- Never pass `dry_run=false` without first showing the dry-run summary and getting explicit
  confirmation.

## Usage

```
/ds-mcp:cleanup jamaica      # dry-run preview, then confirm to wipe
```
