---
name: ereg-issue
effort: medium
description: >
  Standardize and pre-qualify an eRegistrations runtime/deployment issue report
  into a verified qualified-ticket (symptom, instance, version, IDs, candidate
  repo/version, claims) ready for the maintainer/autopilot triage.
  TRIGGER when: a human reports an eRegistrations platform issue on a deployment
  instance ("X is broken on jamaica", "file won't reach desk Y", "registration
  fails on <instance>", "service Z returns 500"), or asks to file/standardize an
  eRegistrations issue report.
  DO NOT TRIGGER when: the defect is in an MCP TOOL itself (use bpa-mcp:mcp-issue);
  it is a pure how-to / domain question (answer directly); or the user is editing
  service config interactively (just do it).
license: UNCTAD-Internal
compatibility: Works with or without active MCP connections; degrades gracefully when a source is blocked.
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
metadata:
  version: "0.1.0"
  version-date: "2026-06-24"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "0.1.0 (2026-06-24): initial scaffold — packaging only; body added in Task 4."
---

# eRegistrations Issue Reporting (ereg-issue)

> SKELETON — body authored in Task 4. Do not invoke yet.

This skill standardizes and pre-qualifies an eRegistrations issue report.
See the design spec: `issues/docs/superpowers/specs/2026-06-24-ereg-issue-design.md`.
