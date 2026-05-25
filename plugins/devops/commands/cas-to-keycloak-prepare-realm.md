---
description: Generate a Keycloak realm JSON for a country from the authoritative starter-conf template — substitutes all placeholders + generates client-secret UUIDs. Phase 0b of the CAS→Keycloak chain.
argument-hint: "[env]/[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak-prepare-realm` skill.

Use the Skill tool with:
- skill: "cas-to-keycloak-prepare-realm"
- args: "$ARGUMENTS" (e.g. `LIVE/cuba`)

The skill resolves `scripts/keycloak-realm.template.json` from the `unctad/eregistrations-starter-conf` repo (local clone or remote fetch), substitutes realm code / domain / OAuth client IDs / SMTP, generates a fresh UUID per client secret, and writes the result to `Conf-<ENV>/compose/<country>/keycloak-realm.json`.
