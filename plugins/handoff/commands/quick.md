---
description: Minimal session handoff — auto-detected state plus a one-liner goal
argument-hint: <goal description>
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Quick Session Handoff

Create a minimal handoff document. `$ARGUMENTS`

## Instructions

Parse arguments: all arguments form the goal description. If no arguments provided, ask for a one-liner goal.

Follow the `handoff` skill in this plugin (`skills/handoff/SKILL.md`), using **Mode: Quick**.

## Usage

```
/handoff:quick Fix token refresh endpoint
/handoff:quick Adding field validation to registration form
```
