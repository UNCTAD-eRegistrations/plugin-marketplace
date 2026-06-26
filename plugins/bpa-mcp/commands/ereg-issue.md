---
description: Report an eRegistrations runtime/deployment issue (standardized & pre-qualified into a qualified-ticket)
argument-hint: [symptom and instance]
effort: medium
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
---

Invoke the `ereg-issue` skill to report an eRegistrations runtime/deployment
issue — it standardizes and pre-qualifies the report into a qualified-ticket.
If the user supplied details, pass them as the initial report:

$ARGUMENTS
