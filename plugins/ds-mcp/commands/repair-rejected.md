---
description: Heal rejected files wrongly shown as "Validated" in Part A for a DS instance (super_mario only, TOBE-17948)
argument-hint: <instance> [process_id]
effort: high
allowed-tools: [mcp__DS__applicant_file_repair_rejected, mcp__DS__ds_health, mcp__DS__instance_list, mcp__DS__ds_auth_login]
---

# DS Repair Rejected — heal files stuck at "Validated"

Fix reject-ends-process race victims (TOBE-17948): files a verifier **rejected** whose canonical
status got stuck at `filevalidated`, so Part A (applicant view) shows **Validated** while Part B
correctly shows **Rejected**. This converges Camunda's canonical status and updates the matching
DS file rows. Restricted to the `super_mario` role. Idempotent — safe to re-run.

Arguments: `$ARGUMENTS` — the instance profile name (e.g. `bhutan-ibls`), and an optional Camunda
`process_id` to repair a single file instead of the whole instance.

## Connecting to DS

Before any tool call:
1. If the instance is unknown, call `instance_list()` to see registered profiles.
2. Check health/auth: `ds_health(instance="<name>")`. If auth fails, call
   `ds_auth_login(instance="<name>")`, wait for success, then retry.

Pass `instance="<name>"` to every `mcp__DS__*` call.

## Instructions

1. Resolve the instance from `$ARGUMENTS[0]`. If it is missing, ask which instance — never guess.
   If `$ARGUMENTS[1]` is present, treat it as a single `process_id` to scope the repair.

2. **Dry run first** (the tool defaults to `dry_run=true`, so this changes nothing):
   ```
   applicant_file_repair_rejected(instance="<name>")            # whole instance
   applicant_file_repair_rejected(instance="<name>", process_id="<id>")   # single file
   ```
   Present the returned `summary`: `camunda_candidates` (rejected files stuck at validated),
   `ds_files_to_heal` (DS rows that would flip to Rejected) — and surface the instance `SYSTEM_CODE`.

3. **Confirm with the user.** State how many files will be corrected and wait for an explicit "yes".

4. **Execute** only after confirmation, passing the `SYSTEM_CODE` from the dry-run summary:
   ```
   applicant_file_repair_rejected(instance="<name>", dry_run=false, confirm="<SYSTEM_CODE>")
   ```
   Report `camunda_repaired` and `ds_files_healed` from the response.

## Notes

- Requires the `super_mario` role; a non-super_mario caller gets HTTP 403.
- The backing endpoint (`POST /backend/admin/repair-rejected-files`) exists only on ds-backend
  builds that include the repair feature (develop / release/2.18+), and it in turn needs a Camunda
  build carrying the `/status/repair-rejected` endpoint. Against older instances a real run fails
  cleanly; the dry run is always safe.
- Scope is the reject-ends-process race (canonical `filevalidated` whose last task is `filereject`).
  A file where a bot task completed *after* the reject is not auto-flagged; it still shows the
  reject correctly in Part B history.

## Usage

```
/ds-mcp:repair-rejected bhutan-ibls                              # dry-run preview, then confirm
/ds-mcp:repair-rejected bhutan-ibls d55c933c-794e-11f1-85f1-...  # single file
```
