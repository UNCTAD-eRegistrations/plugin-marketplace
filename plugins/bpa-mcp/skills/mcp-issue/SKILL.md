---
name: mcp-issue
effort: medium
description: >
  Report an MCP tool issue (BPA, DS, GDB, or Keycloak) that produced wrong results, failed
  unexpectedly, or behaved differently from the web UI. Use when the user says something went
  wrong, a tool gave incorrect output, the result doesn't match the UI, data was corrupted,
  a mapping is wrong, or they want to file a bug against the MCP server. Also triggers on
  phrases like "this is broken", "that's not right", "the tool did the wrong thing", "it
  should have done X instead", or "report this bug".
license: UNCTAD-Internal
compatibility: Works with or without an active MCP server connection.
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__BPA-local-dev__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
metadata:
  version: "3.0.0"
  version-date: "2026-04-02"
  author: "UNCTAD Trade Facilitation Section"
---

# Report an MCP Issue

You will help the user document a functional issue with an eRegistrations MCP server, producing a structured markdown report that an MCP developer can use to reproduce and fix the problem.

**Your role:** Be a patient but skeptical investigator. The user may be non-technical — guide them through describing what went wrong without jargon. But also verify claims before writing them up — AI agents (including you) can hallucinate issues, misread responses, or confuse expected behavior with actual bugs.

**Core principle:** Every issue report must be _verified_, not just _transcribed_. A wrong bug report wastes more developer time than no report at all.

## Supported MCP servers

| Server | Tool prefix | Config path | Source path |
|--------|------------|-------------|-------------|
| **BPA** | `mcp__BPA__` | `~/.config/mcp-eregistrations-bpa/` | `src/mcp_eregistrations_bpa/tools/` |
| **DS** | `mcp__DS__` | `~/.config/mcp-eregistrations-ds/` | `src/mcp_eregistrations_ds/tools/` |
| **GDB** | `mcp__GDB__` | `~/.config/mcp-eregistrations-gdb/` | `src/mcp_eregistrations_gdb/tools/` |
| **Keycloak** | `mcp__Keycloak__` | `~/.config/mcp-eregistrations-keycloak/` | `src/mcp_eregistrations_keycloak/tools/` |

Throughout this skill, `{SERVER}` refers to the identified server (BPA, DS, GDB, or Keycloak) and `{server}` to its lowercase form (bpa, ds, gdb, keycloak).

## Step 1 — Identify the server & understand what happened

First, determine which MCP server is involved. Look for:
- The tool prefix in the failing call (`mcp__BPA__`, `mcp__DS__`, `mcp__GDB__`, `mcp__Keycloak__`)
- Context clues (forms/determinants → BPA, files/payments → DS, databases/records → GDB, users/realms → Keycloak)
- Ask the user if unclear

Then ask the user to describe the problem in their own words. Helpful prompts:

> What were you trying to do? What happened instead of what you expected?

Listen for:
- Which tool was involved (or what action they were performing)
- What instance they were working with
- Whether they saw an error message or just wrong data
- Whether the same action works correctly in the web UI

If the problem is visible in the current conversation (a tool call that returned wrong data, an error), reference it directly — don't make the user repeat what's already in context.

## Step 2 — Gather environment details

Collect these automatically (don't ask the user):

1. **Server version and instances:** Call `mcp__{SERVER}__connection_status(instance="<name>")` for the affected instance. The response includes `version`, `latest_version`, and `update_available` fields. Also call `mcp__{SERVER}__instance_list()` to capture registered instances.

2. **Today's date:** Run via Bash:
   ```
   date +%Y-%m-%d
   ```

3. **Recent server log errors** (if available). Run via Bash:
   ```
   find ~/.config/mcp-eregistrations-{server}/instances -name 'server.log' -exec grep -E 'ERROR|CRITICAL' {} \; 2>/dev/null | tail -10
   ```

## Step 3 — Identify the root cause area

Based on what the user described, determine which category applies:

| Category | Symptoms |
|----------|----------|
| **Wrong API call** | Tool sends incorrect HTTP method, path, or parameters |
| **Data transformation** | Response data is mangled, fields missing, wrong format |
| **UI mismatch** | Tool produces different result than the same action in the web UI |
| **Missing validation** | Tool accepts invalid input that the UI would reject |
| **Auth/connection** | Token errors, timeouts, wrong instance targeted |
| **Missing capability** | Tool doesn't support an operation that the UI does |

Ask clarifying questions only if you genuinely can't categorize. Don't interrogate the user.

## Step 4 — Reproduce & Verify

**This step is critical. Do NOT skip it.**

Before writing anything up, verify the issue is real and reproducible:

### 4a. Re-run the failing tool call

If the original tool call is in the conversation context, re-run it with the **exact same parameters**. Compare:

| Outcome | Action |
|---------|--------|
| Same error/wrong result | Issue confirmed — proceed to Step 5 |
| Different error | Note both results — may be intermittent or state-dependent |
| Works correctly now | **Stop.** Tell the user: "I re-ran the same call and it succeeded. The original failure may have been transient (auth expiry, network, server restart). Want me to still file it as intermittent?" |

### 4b. Rule out user error

Try variations to isolate whether the issue is the tool or the input:

- **Wrong parameters?** — If the tool expects a service_id and the user passed a registration_id, that's not a bug. Check param types and values.
- **Wrong tool?** — Did the user use `determinant_get` when they meant `determinant_list`? Suggest the correct tool.
- **Stale state?** — Did a prior operation (delete, update) change the data? Re-fetch the resource to check current state.
- **Auth expired?** — Re-authenticate and retry before blaming the tool.

### 4c. Cross-check against source (if accessible)

If the MCP server source code is available locally, check the tool implementation:

```
# Find the tool source
grep -r "def <tool_name>" src/mcp_eregistrations_{server}/tools/ 2>/dev/null
```

Read the relevant function to understand:
- What API endpoint it calls
- What transformations it applies to the response
- Whether the "expected behavior" the user described matches what the tool is designed to do

**If the tool is working as designed but the user expected different behavior, that's a feature request, not a bug.** Note this distinction in the report.

### 4d. Verify "expected behavior" claims

This is where hallucinations hide. Before accepting any claim about what _should_ happen:

- **Check the API reference** if available
- **Check tool docstring**: Does it promise what the user expects?
- **Check the web UI** (if the user can confirm): Does the UI actually do what they claim?

**Never write "Expected: X" in a report unless you have evidence that X is correct.** If you're unsure, write "Expected behavior needs verification" and explain why.

## Step 5 — Capture the technical details

If the failing tool call is in the current conversation, extract:
- **Tool name** and **parameters** used
- **Response** received (or error message)
- **Reproduction result** from Step 4 (confirmed / intermittent / not reproduced)
- **Expected response** (from user description, UI comparison, or API docs — cite which)

If the user can show what the web UI does for the same action (screenshot, network tab, or description), capture that as the "expected behavior" baseline.

## Step 6 — Adversarial Self-Review

Before writing the report, run through this checklist **honestly**. Write your answers down (internally, not in the report) for each question:

### Hallucination check

| Question | If YES → |
|----------|----------|
| Am I claiming the tool "should" do X without evidence? | Remove the claim or mark as "needs verification" |
| Did I read the error message carefully, or am I paraphrasing from memory? | Re-read the actual response |
| Am I conflating two different issues into one? | Split into separate reports |
| Is my "expected behavior" based on how _I think_ the API works, or on actual docs/UI? | Cite your source or downgrade confidence |
| Did the user actually say this, or am I inferring? | Quote the user's words, don't interpret |

### Alternative explanations

Before concluding "this is a bug", consider each alternative:

1. **User error** — Wrong params, wrong tool, misunderstanding of what the tool does
2. **Stale state** — Data changed between operations
3. **Auth/session issue** — Token expired, wrong instance
4. **Known limitation** — Tool docstring says it doesn't support this case
5. **Working as designed** — The behavior is intentional, just not what the user wanted
6. **Environment issue** — Version mismatch, network, server-side problem

For each alternative, note whether you ruled it out and how. If you can't rule out an alternative, mention it in the report.

### Claim classification (First Principles)

Build this table for every factual claim that will appear in the report. This is not optional — it's the structural filter that prevents bad reports from being filed.

| Claim | Type | Evidence |
|-------|------|----------|
| _"Tool returns X"_ | **Hard** (reproduced) | Re-ran call, got same result |
| _"Should return Y"_ | **Assumption** (unverified) | User said so, no UI/doc confirmation |
| _"Field Z is missing"_ | **Hard** (observed) | Compared response against UI screenshot |

Type definitions:
- **Hard** — You observed this directly (tool output, reproduction, source code, UI comparison)
- **Soft** — Reasonable inference from docs or tool docstring, but not directly observed
- **Assumption** — Claim from user report, your inference, or "how you think it should work" — no direct evidence

**Any claim typed as "Assumption" must be marked "needs verification" in the report.** Do not present assumptions as facts.

### Failure lens (Iterative Depth)

Before proceeding, answer this honestly:

> **If this report is wrong, what damage does it cause?** Would a developer waste hours reproducing a non-issue? Would they "fix" something that wasn't broken and introduce a real bug?

If the answer is "significant damage" and you have any Assumption-typed claims, **stop and tell the user** what evidence is needed before proceeding.

### Assign confidence level

Based on your verification work:

| Level | Criteria |
|-------|----------|
| **Verified** | Reproduced the issue, confirmed expected behavior from UI/docs, ruled out alternatives |
| **Likely** | Reproduced or have strong evidence, but couldn't fully verify expected behavior |
| **Suspected** | User report is credible and consistent, but couldn't reproduce or verify independently |
| **Unverified** | Couldn't reproduce, expected behavior is unclear, or significant alternative explanations remain |

**If confidence is "Unverified", tell the user before writing the report.** They may want to gather more evidence first.

## Step 7 — Write the report

Create the report directory and file:

```
mkdir -p ~/Desktop/mcp-issue-reports
```

Write the report to `~/Desktop/mcp-issue-reports/<date>-<server>-<slug>.md` where `<server>` is the lowercase server name and `<slug>` is a short kebab-case summary (e.g., `2026-04-02-bpa-effect-create-wrong-format`).

### Report template

```markdown
# {SERVER} MCP Issue: <Short title>

**Date:** <YYYY-MM-DD>
**Server:** <BPA | DS | GDB | Keycloak>
**Reporter:** <user name if known, otherwise "via Claude">
**Severity:** <critical | high | medium | low>
**Confidence:** <verified | likely | suspected | unverified>

## Environment

- **MCP server version:** <version> (latest: <latest>)
- **Instance:** <name> (<url>)
- **Service ID:** <if applicable>

## Summary

<1-2 sentence description of the problem>

## Reproduction

- **Reproduced:** <yes — consistent | yes — intermittent | no — works on retry | not attempted>
- **Reproduction tool call:**
```
Tool: mcp__{SERVER}__<tool_name>(param=value, ...)
Result: <same error | different result | success>
```

## Steps to Reproduce

1. <step>
2. <step>
3. <step>

## Actual Behavior

<What happened. Include the tool call, parameters, and response.>

```
Tool: mcp__{SERVER}__<tool_name>(param=value, ...)
Response: <summarized or full response>
```

## Expected Behavior

<What should have happened.>

**Evidence source:** <web UI observation | API reference doc | tool docstring | user report only>

## Web UI Comparison

<If available: what the UI sends/receives for the same operation.
Include API endpoint, method, and payload if captured.>

<If not available: "Not compared — user did not check UI behavior.">

## Claim Classification

| Claim | Type | Evidence |
|-------|------|----------|
| <claim> | <Hard / Soft / Assumption> | <evidence or "needs verification"> |

## Alternative Explanations Considered

| Alternative | Ruled out? | How |
|-------------|-----------|-----|
| User error (wrong params) | <yes/no> | <explanation> |
| Stale state | <yes/no> | <explanation> |
| Auth/session issue | <yes/no> | <explanation> |
| Known limitation | <yes/no> | <explanation> |
| Working as designed | <yes/no> | <explanation> |

## Server Logs

<Relevant error lines from server.log, or "No errors found in logs.">

## Analysis

<Your assessment of what's likely wrong. Reference specific source files
in the MCP server if you can identify them.>

### Likely affected files

- `src/mcp_eregistrations_{server}/tools/<file>.py`

## Suggested Fix

<Concrete suggestion for the MCP developer, if you have one.>
```

## Step 8 — Confirm with the user

Show the user the report path and a brief summary of what was captured:

> Issue report saved to `~/Desktop/mcp-issue-reports/<filename>.md`
>
> **Summary:** <one line>
> **Server:** <BPA | DS | GDB | Keycloak>
> **Category:** <category>
> **Severity:** <severity>
> **Confidence:** <level> — <one-line justification>
>
> You can share this file with the MCP development team. Would you like me to adjust anything?

If confidence is below "verified", explicitly tell the user what additional evidence would raise it (e.g., "If you can confirm the web UI behavior for this action, I can upgrade confidence to 'verified'").

## Step 9 — File on GitHub (optional)

After the user confirms the report, offer to file it as a GitHub issue.

### Hard gate — do NOT offer to file if:

- Confidence is below **"likely"**
- Any claim in the "Expected Behavior" section has type **"Assumption"** in the claim classification table
- The report was classified as a **feature request**, not a bug

If any gate fails, tell the user exactly what's blocking it and what evidence would unblock it:

> I can't file this on GitHub yet — the expected behavior is based on your description only (no UI/doc confirmation). If you can verify what the web UI does for this action, I can upgrade the claim and file it.

### Filing

1. **Check prerequisites:**
   ```
   gh auth status
   ```
   If not authenticated, tell the user to run `! gh auth login` and stop.

2. **Map labels** from the report:

   | Report field | GitHub label |
   |---|---|
   | Server: BPA | `bpa` |
   | Server: DS | `ds` |
   | Server: GDB | `gdb` |
   | Server: Keycloak | `keycloak` |
   | Category: Wrong API call | `api` |
   | Category: Data transformation | `data` |
   | Category: UI mismatch | `ui-mismatch` |
   | Category: Missing validation | `validation` |
   | Category: Auth/connection | `auth` |
   | Category: Missing capability | `enhancement` |
   | Confidence: verified | `verified` |
   | Confidence: likely | `likely` |
   | Severity: critical | `critical` |
   | Severity: high | `high` |

3. **Ask the user for confirmation** before filing:

   > Ready to file on **UNCTAD-eRegistrations/MCP_eRegistrations**:
   > - **Title:** <title>
   > - **Labels:** <labels>
   >
   > File it?

4. **Create the issue** (only after explicit user approval):
   ```
   gh issue create --repo UNCTAD-eRegistrations/MCP_eRegistrations \
     --title "<title>" \
     --body-file ~/Desktop/mcp-issue-reports/<filename>.md \
     --label "<label1>,<label2>"
   ```

5. **Show the issue URL** to the user.

If any labels don't exist in the repo, omit them rather than failing. Use `--label` only for labels that exist.

## Guidelines

- **Be patient with non-technical users.** Don't ask for API endpoints or HTTP methods — figure those out yourself from the tool name and context.
- **Don't guess.** If you don't know what the expected behavior should be, say so in the report and mark it for investigation.
- **Don't trust your own memory.** Re-read actual tool responses instead of paraphrasing. AI agents (including you) misread data more often than you'd expect.
- **Prefer "needs verification" over confident-but-wrong.** A report that says "I'm not sure about the expected behavior" is more useful than one that confidently states wrong expectations.
- **Severity guide:**
  - **critical** — data loss or corruption, tool destroys/overwrites data
  - **high** — tool produces wrong results silently (user might not notice)
  - **medium** — tool fails with error, but no data damage
  - **low** — cosmetic, formatting, or minor inconvenience
- **Keep the report concise.** Developers skim — put the important stuff first.
- **Feature request ≠ bug.** If the tool works as designed but the user wants different behavior, label it as a feature request, not an issue.
