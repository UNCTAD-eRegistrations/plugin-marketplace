---
description: Create a Conf-PREVIEW draft (UAT) instance from an existing Conf-LIVE Keycloak instance and patch the LIVE side to wire UAT cross-references back to the draft.
argument-hint: "[live-instance-name] [draft-prefix]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the create-draft-instance skill to generate a Conf-PREVIEW draft instance configuration from an existing Conf-LIVE Keycloak instance and wire LIVE for UAT.

Use the Skill tool with:
- skill: "create-draft-instance"
- args: "$ARGUMENTS" (instance name, then optional draft-prefix override; defaults: prefix=draft)
