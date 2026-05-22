---
description: Run the CAS→Keycloak seed pipeline — spins up a throwaway Docker stack, imports the realm JSON, loads cas+partc dumps, runs the migrator, and produces `sql/keycloak.sql` ready to load into a target Keycloak.
argument-hint: "[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak` skill in **seed** mode.

Use the Skill tool with:
- skill: "cas-to-keycloak"
- args: "seed $ARGUMENTS" (country name, e.g. `cuba`)

The skill will:
1. Locate the country's eRegistrations config repo and stage `dump-keycloak-local/` tooling.
2. Verify `sql/cas.sql` and `sql/partc.sql` exist (offer to run fetch first if not).
3. Resolve realm JSON path, realm name, and `INSTITUTION_GROUP_ID` from the repo's Conf-PREVIEW.
4. Execute `dump-keycloak-local/run.sh` with the parameterised env exported.
5. Report `sql/keycloak.sql` stats: file size, line count, per-role assignment counts, and any username-collision warnings.

Operator runs `/devops:cas-to-keycloak-backfill <country>` to apply the same diff in-place against an already-running Keycloak, or ships `sql/keycloak.sql` to the target Postgres for a fresh seed.
