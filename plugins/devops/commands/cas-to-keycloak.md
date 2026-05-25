---
description: End-to-end CAS→Keycloak cutover orchestrator. Walks all 8 phases (verify, add-service, prepare-realm, fetch, seed, deploy, migrate-apps, backfill) with operator gates before any mutation.
argument-hint: "[country] [resume-from-phase]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak-orchestrator` skill.

Use the Skill tool with:
- skill: "cas-to-keycloak-orchestrator"
- args: "$ARGUMENTS" (country name + optional phase to resume from, e.g. `cuba` or `cuba deploy`)

The orchestrator drives the full chain, threading context between phases so the operator is prompted once for ssh hosts, secrets, etc. Sub-skills can still be invoked directly via their individual slash commands for partial runs.

Read `LESSONS.md` alongside the cas-to-keycloak skill before mutating production.
