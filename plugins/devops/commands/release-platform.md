---
description: Cut a new platform release across all 27 eRegistrations repositories. Creates release branches and bumps develop versions. Supports --dry-run.
argument-hint: "[version] [--dry-run] [repo1 repo2 ...]"
allowed-tools: Skill, Bash, Read, Write, Edit, AskUserQuestion, TodoWrite
---

Invoke the release-platform skill to cut a new platform release across the 27 eRegistrations repositories.

Use the Skill tool with:
- skill: "release-platform"
- args: "$ARGUMENTS" (forward any provided arguments — version, `--dry-run`, repo filter)
