---
description: Full session handoff with auto-detection and conversational context gathering
argument-hint: "[title]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Create Session Handoff

Create a full session handoff document. `$ARGUMENTS`

## Instructions

Parse arguments: the optional first argument is the handoff title. If omitted, infer from the current branch name or active plan.

Follow the `handoff` skill in this plugin (`skills/handoff/SKILL.md`), using **Mode: Create**.

## Usage

```
/handoff:create
/handoff:create OAuth2 integration
```
