---
description: Flip a country's app services from CAS to Keycloak — removes CAS/PARTC services + haproxy rules, updates KEYCLOAK_*/AUTH_SERVICE_*/OAUTH_* env vars on every remaining service. Phase 4 of the CAS→Keycloak chain.
argument-hint: "[env]/[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak-migrate-apps` skill.

Use the Skill tool with:
- skill: "cas-to-keycloak-migrate-apps"
- args: "$ARGUMENTS" (e.g. `LIVE/cuba`)

Prerequisites:
- The keycloak service must already be in the compose (run `/devops:cas-to-keycloak-add-service` first if not).
- A populated realm.json must be alongside (run `/devops:cas-to-keycloak-prepare-realm` first if not).

The skill diffs the target country against `Conf-LIVE/compose/kenya/docker-stack.yml` (canonical KC reference) and brings it to parity. Resolves `KEYCLOAK_INSTITUTIONS_GROUP_ID` + `KEYCLOAK_CLIENT_SCOPE_ID` from realm.json — never hardcoded.

Apps still need a manual `docker compose up -d --force-recreate <services>` on the deploy host after this lands to pick up the new env vars.
