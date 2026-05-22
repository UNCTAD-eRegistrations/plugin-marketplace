---
description: Backfill missing realm roles and role mappings into an already-running Keycloak. Idempotent — applies only the diff against the target realm, recommended when the previous seed missed roles or new custom roles need promotion.
argument-hint: "[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak` skill in **backfill** mode.

Use the Skill tool with:
- skill: "cas-to-keycloak"
- args: "backfill $ARGUMENTS" (country name, e.g. `cuba`)

The skill will:
1. Locate the country's eRegistrations config repo and stage `dump-keycloak-local/` tooling.
2. Verify `migrator-workdir/{users,user-roles}.json` exist (these are produced by seed; aborts with instructions if missing).
3. Prompt for target Keycloak: `AUTH_URL`, `AUTH_REALM_NAME`, admin username + password.
4. Confirm the target before any mutation.
5. Execute `dump-keycloak-local/backfill.sh` — creates missing realm roles, then diffs and applies missing realm- and client-role mappings per user.
6. Report counts: roles created, users matched, users not found, assignments added vs already-present, failures.

`NODE_TLS_REJECT_UNAUTHORIZED=0` is set by default (eRegistrations internal certs drift expired); export `NODE_TLS_REJECT_UNAUTHORIZED=1` before running for strict TLS.
