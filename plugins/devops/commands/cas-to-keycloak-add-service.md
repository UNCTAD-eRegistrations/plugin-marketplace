---
description: Add the Keycloak service block + haproxy ACLs to a country's eRegistrations stack. Phase 0a of the CAS→Keycloak chain.
argument-hint: "[env]/[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak-add-service` skill.

Use the Skill tool with:
- skill: "cas-to-keycloak-add-service"
- args: "$ARGUMENTS" (e.g. `LIVE/cuba`)

The skill inserts the keycloak service definition into `Conf-<ENV>/compose/<country>/docker-{compose,stack}.yml` and the keycloak ACLs + backend into `Conf-<ENV>/haproxy/<country>/haproxy.cfg`. Idempotent.
