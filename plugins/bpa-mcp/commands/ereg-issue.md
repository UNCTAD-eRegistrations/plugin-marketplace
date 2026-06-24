---
description: Standardize and pre-qualify an eRegistrations runtime/deployment issue report
argument-hint: [symptom and instance]
effort: medium
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
---

Invoke the `ereg-issue` skill to standardize and pre-qualify an eRegistrations
issue report. If the user supplied details, pass them as the initial report:

$ARGUMENTS
