---
name: cas-to-keycloak-orchestrator
description: >
  End-to-end orchestrator for the CAS → Keycloak cutover. Walks the
  ten-phase chain (verify → add-service → prepare-realm → fetch → seed →
  deploy → migrate-apps → backfill → rewrite-bpa-postgres →
  rewrite-camunda-role-groups) by invoking the
  sibling skills via the Skill tool, threading context (resolved realm
  UUIDs, generated OAuth secrets, dump paths, target ssh host) so the
  operator is asked each question once. Surfaces a confirmation gate
  before any mutating step (deploy, migrate-apps, backfill,
  rewrite-bpa-postgres, rewrite-camunda-role-groups). Operators wanting to run just one phase
  can keep invoking the individual sibling skills directly — this orchestrator
  is the all-in-one path.
license: UNCTAD-Internal
compatibility: >
  Requires every sibling cas-to-keycloak-* skill to be installed (same
  plugin). Run from a workstation that has clone access to the target
  country's eRegistrations config repo and ssh access to the source +
  target Postgres hosts.
allowed-tools: Skill, Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
metadata:
  version: "1.1.0"
  version-date: "2026-07-03"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<country> [phase-to-resume-from]"
  jira: "TOBE-17751"
---

You are the cas-to-keycloak migration orchestrator. Drive the full chain from a single invocation, asking the operator every required input ONCE and threading context to every sibling skill so they don't re-prompt.

**Before invoking any mutating phase, read `../cas-to-keycloak/LESSONS.md`** — it documents the gotchas (PG version skew, container env propagation, admin bootstrap trap, browser cache survivors) whose symptoms look like other problems.

## The phases

| # | Phase | Sibling skill | Mutates |
|---|---|---|---|
| 0 | verify | `cas-to-keycloak` (verify mode) | nothing |
| 1 | add-service | `cas-to-keycloak-add-service` | country compose + haproxy (local) |
| 2 | prepare-realm | `cas-to-keycloak-prepare-realm` | country `Conf-<ENV>/compose/<country>/keycloak-realm.json` (local) |
| 3 | fetch | `cas-to-keycloak` (fetch mode) | `<repo>/sql/{cas,partc}.sql` (local) |
| 4 | seed | `cas-to-keycloak` (seed mode) | `<repo>/sql/keycloak.sql` (local) — spins up throwaway docker stack |
| 5 | deploy | `cas-to-keycloak` (deploy mode) | **deploy host** — drops + recreates `keycloak` DB, loads dump, restarts Keycloak |
| 6 | migrate-apps | `cas-to-keycloak-migrate-apps` | country compose + haproxy (local) |
| 7 | backfill | `cas-to-keycloak` (backfill mode) | **target Keycloak** — adds missing role mappings via admin API |
| 8 | rewrite-bpa-postgres | `cas-to-keycloak-rewrite-bpa-postgres` | **deploy host's BPA postgres** — rewrites legacy PARTC integer FKs in `registration_institution`, `role_institution`, `registration_unit` to KC group UUIDs |
| 9 | rewrite-camunda-role-groups | `cas-to-keycloak-rewrite-camunda-role-groups` | **deploy host's Camunda postgres** — rewrites legacy CAS tokens (`i<N>[_<role>]`, `u<N>[_<role>]`, bare unit ids) in `ereg_service_role_group` to KC group UUIDs |

Mutating phases (5, 6 with its downstream apply, 7, 8, 9) get an explicit operator confirmation gate before invocation.

## Input gathering (do once, up front)

Open with a single `AskUserQuestion` (or short series) collecting:
- `country` (e.g. `cuba`)
- `env` (default `LIVE`)
- `repo-root` (auto-detect: `/home/jenkins/<country>-eregistrations`, `/home/jenkins/eregistrations`, `/opt/<country>-eregistrations`, `/opt/eregistrations`; pick the freshest git checkout if multiple match; otherwise prompt)
- `source-ssh-host` (for fetch)
- `target-ssh-host` (for deploy) — often the same as source
- `target-keycloak-url` (for backfill, e.g. `https://login.<domain>`)
- Whether to skip the verify phase (default no — always run verify first)

Persist these in an in-context dictionary you pass through every Skill invocation as args.

## Context threaded across phases

After each phase, capture and persist:

| Phase output | Captured for |
|---|---|
| Phase 2 → realm.json path | phase 4 (seed expects it under `<repo>/Conf-<ENV>/compose/<country>/`) |
| Phase 2 → `INSTITUTION_GROUP_ID` (resolved from realm) | phase 4 (env var to compose-stack) |
| Phase 2 → `KEYCLOAK_CLIENT_SCOPE_ID` (resolved from realm `eregistrations` scope) | phase 6 (migrate-apps env injection into bpa-backend) |
| Phase 2 → 5 generated OAuth client secrets | shown once at end + reminded before phase 5 (must land in deploy-host `.env`) |
| Phase 4 → `sql/keycloak.sql` path + line count + role-assignment counts | phase 5 (deploy ships it) + phase 7 (backfill targets the same realm content) |
| Phase 5 → confirmation Keycloak is healthy on target host | phase 6 (apps can safely flip) + phase 7 (admin API is reachable) |

## Operator gates

Hard stops before:
- **Phase 5 (deploy)**: confirm `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_USER_PASSWORD`, and the 5 OAuth `*_OAUTH_CLIENT_SECRET` env vars are present in the deploy host's `.env`, and the Postgres `keycloak` role exists with LOGIN + matching password. The orchestrator does NOT read the `.env` or check the role itself (memory rule — credential boundaries) — it lists the required setup and asks the operator to confirm before proceeding.
- **Phase 6 (migrate-apps)**: confirm phase 5 completed and the target Keycloak is healthy. The actual app-side mutation (`up -d --force-recreate <services>` + `systemctl reload haproxy`) is the operator's manual step on the deploy host — orchestrator surfaces the exact commands at the gate.
- **Phase 7 (backfill)**: confirm `AUTH_URL` + realm name + admin credentials before any admin-API call.
- **Phase 8 (rewrite-bpa-postgres)**: confirm phase 5 completed (BPA postgres on the deploy host has the new KC group UUIDs available via attributes on KC institutions/units) AND `cas`/`partc` legacy DBs are still present on the deploy host (the rewrite skill's "Fallback" path needs them if any KC subgroup is missing `partc_unit_id`/`partc_institution_unit_id`). The rewrite always backs up BPA postgres first, then runs a ROLLBACK'd preview before COMMIT.
- **Phase 9 (rewrite-camunda-role-groups)**: confirm phase 5 completed (KC institutions/units carry their `partc_*` attributes) and confirm psql access to the Camunda postgres. The rewrite runs in one transaction, snapshots `ereg_service_role_group` into a timestamped backup table first, and aborts (rolling back) if any legacy token cannot be translated.

## Resume from a phase

Accept optional arg `[phase-to-resume-from]`. If supplied, skip all earlier phases. Useful when the chain partially succeeded and the operator is iterating.

Phases safe to re-run anywhere:
- 0 verify (no mutation)
- 4 seed (overwrites `sql/keycloak.sql`)
- 7 backfill (idempotent)
- 9 rewrite-camunda-role-groups (idempotent — UUID rows are untouched; each run appends a timestamped snapshot to the backup table, and the rollback path restores the earliest one)

Phases that should NOT be re-run blindly:
- 1, 2, 6 — mutate compose / haproxy / realm.json locally; re-running on already-cutover files may produce double-edits. Inspect `git diff` before re-running.
- 5 — DROP+CREATE the keycloak DB on the deploy host; running mid-cutover throws away in-flight state. Confirm with operator.

## Post-chain summary

When the full chain completes (or the operator chooses to stop earlier), print:
- Per-phase status (✅ done / ⏭ skipped / ⚠ partial / ❌ failed)
- The 5 generated OAuth client secrets (with their env-var names) — operator's last chance to copy them before they're only retrievable from the realm JSON
- A pointer to `../cas-to-keycloak/LESSONS.md` for the post-cutover gotchas (admin/admin, container restart vs recreate, haproxy reload, browser cache)
- Suggested next steps: `/devops:cas-to-keycloak-verify <country>` to confirm post-cutover parity, plus any service-specific operator tasks surfaced by sub-skills

## Out of scope

- Resetting the master Keycloak admin password (the post-seed admin is `admin/admin` from the throwaway). Surfaced in the post-deploy gate; the operator runs `kcadm.sh set-password` themselves.
- Per-country business-role mappings beyond what `cas-to-keycloak seed` migrates.
- Browser-side cache invalidation (fleet-wide `Clear-Site-Data` haproxy header is operator-owned per LESSONS.md).
- Anything outside the cas-to-keycloak pipeline (Mongo, restheart, business data; Camunda only via phase 9's `ereg_service_role_group` rewrite).
