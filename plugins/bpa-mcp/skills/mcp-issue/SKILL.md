---
name: mcp-issue
description: >
  Report a BPA MCP tool that produced wrong results, failed unexpectedly, or behaved
  differently from the BPA web UI. Use when the user says something went wrong, a tool
  gave incorrect output, the result doesn't match the UI, data was corrupted, a mapping
  is wrong, or they want to file a bug against the MCP server. Also triggers on phrases
  like "this is broken", "that's not right", "the tool did the wrong thing", "it should
  have done X instead", or "report this bug".
license: UNCTAD-Internal
compatibility: Works with or without an active BPA MCP server connection.
allowed-tools: Read, Write, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(uvx *), Bash(mcp-eregistrations-bpa *)
metadata:
  version: "1.0.0"
  version-date: "2026-02-25"
  author: "UNCTAD Trade Facilitation Section"
---

# Report a BPA MCP Issue

You will help the user document a functional issue with the BPA MCP server, producing a structured markdown report that an MCP developer can use to reproduce and fix the problem.

**Your role:** Be a patient investigator. The user may be non-technical — guide them through describing what went wrong without jargon.

## Step 1 — Understand what happened

Ask the user to describe the problem in their own words. Helpful prompts:

> What were you trying to do? What happened instead of what you expected?

Listen for:
- Which BPA tool was involved (or what action they were performing)
- What instance and service they were working with
- Whether they saw an error message or just wrong data
- Whether the same action works correctly in the BPA web UI

If the problem is visible in the current conversation (a tool call that returned wrong data, an error), reference it directly — don't make the user repeat what's already in context.

## Step 2 — Gather environment details

Collect these automatically (don't ask the user). Run via Bash:

1. **Server version:**
   ```
   uv tool list 2>/dev/null | grep mcp-eregistrations-bpa | head -1 | awk '{print $2}' | tr -d 'v'
   ```

2. **Latest available version:**
   ```
   curl -sf https://pypi.org/pypi/mcp-eregistrations-bpa/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])" 2>/dev/null
   ```

3. **Today's date:**
   ```
   date +%Y-%m-%d
   ```

4. **Recent server log errors** (if available):
   ```
   find ~/.config/mcp-eregistrations-bpa/instances -name 'server.log' -exec grep -E 'ERROR|CRITICAL' {} \; 2>/dev/null | tail -10
   ```

If the BPA MCP server is loaded, also call:
- `mcp__BPA__instance_list()` to capture registered instances

## Step 3 — Identify the root cause area

Based on what the user described, determine which category applies:

| Category | Symptoms |
|----------|----------|
| **Wrong API call** | Tool sends incorrect HTTP method, path, or parameters |
| **Data transformation** | Response data is mangled, fields missing, wrong format |
| **UI mismatch** | Tool produces different result than the same action in BPA web UI |
| **Missing validation** | Tool accepts invalid input that the UI would reject |
| **Auth/connection** | Token errors, timeouts, wrong instance targeted |
| **Missing capability** | Tool doesn't support an operation that the UI does |

Ask clarifying questions only if you genuinely can't categorize. Don't interrogate the user.

## Step 4 — Capture the technical details

If the failing tool call is in the current conversation, extract:
- **Tool name** and **parameters** used
- **Response** received (or error message)
- **Expected response** (from user description or UI comparison)

If the user can show what the BPA UI does for the same action (screenshot, network tab, or description), capture that as the "expected behavior" baseline.

## Step 5 — Write the report

Create the report directory and file:

```
mkdir -p ~/Desktop/bpa-mcp-reports
```

Write the report to `~/Desktop/bpa-mcp-reports/<date>-<slug>.md` where `<slug>` is a short kebab-case summary (e.g., `effect-create-wrong-format`).

### Report template

```markdown
# BPA MCP Issue: <Short title>

**Date:** <YYYY-MM-DD>
**Reporter:** <user name if known, otherwise "via Claude">
**Severity:** <critical | high | medium | low>

## Environment

- **MCP server version:** <version> (latest: <latest>)
- **Instance:** <name> (<url>)
- **Service ID:** <if applicable>

## Summary

<1-2 sentence description of the problem>

## Steps to Reproduce

1. <step>
2. <step>
3. <step>

## Actual Behavior

<What happened. Include the tool call, parameters, and response.>

```
Tool: mcp__BPA__<tool_name>(param=value, ...)
Response: <summarized or full response>
```

## Expected Behavior

<What should have happened. Reference BPA UI behavior if known.>

## BPA UI Comparison

<If available: what the UI sends/receives for the same operation.
Include API endpoint, method, and payload if captured.>

<If not available: "Not compared — user did not check UI behavior.">

## Server Logs

<Relevant error lines from server.log, or "No errors found in logs.">

## Analysis

<Your assessment of what's likely wrong. Reference specific source files
in the MCP server if you can identify them.>

### Likely affected files

- `src/mcp_eregistrations_bpa/tools/<file>.py`

## Suggested Fix

<Concrete suggestion for the MCP developer, if you have one.>
```

## Step 6 — Confirm with the user

Show the user the report path and a brief summary of what was captured:

> Issue report saved to `~/Desktop/bpa-mcp-reports/<filename>.md`
>
> **Summary:** <one line>
> **Category:** <category>
> **Severity:** <severity>
>
> You can share this file with the MCP development team. Would you like me to adjust anything?

## Guidelines

- **Be patient with non-technical users.** Don't ask for API endpoints or HTTP methods — figure those out yourself from the tool name and context.
- **Don't guess.** If you don't know what the expected behavior should be, say so in the report and mark it for investigation.
- **Severity guide:**
  - **critical** — data loss or corruption, tool destroys/overwrites data
  - **high** — tool produces wrong results silently (user might not notice)
  - **medium** — tool fails with error, but no data damage
  - **low** — cosmetic, formatting, or minor inconvenience
- **Keep the report concise.** Developers skim — put the important stuff first.
