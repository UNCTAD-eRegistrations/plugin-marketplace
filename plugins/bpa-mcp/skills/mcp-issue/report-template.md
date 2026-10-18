# mcp-issue report template

Step 7 of `SKILL.md` uses this template. Fill in each placeholder.

```markdown
# {SERVER} MCP Issue: <Short title>

**Date:** <YYYY-MM-DD>
**Server:** <BPA | DS | GDB | Keycloak | Graylog | Translations>
**Reporter:** <user name if known, otherwise "via Claude">
**Severity:** <critical | high | medium | low>
**Confidence:** <verified | likely | suspected | unverified>

## Environment

- **MCP server version:** <version, or "not reported"> (latest: <latest, or "not reported">) — source: <status tool field | BPA server_info>
- **Backend version:** <the backend version field named in the Step 2 table, or "not reported">
- **Instance:** <name> (<url>)
- **Service ID:** <if applicable>

## Summary

<1-2 sentence description of the problem>

## Reproduction

- **Reproduced:** <yes — consistent | yes — intermittent | no — works on retry | not attempted>
- **Reproduction tool call:**
```
Tool: <full tool name as called>(param=value, ...)
Result: <same error | different result | success>
```

## Steps to Reproduce

1. <step>
2. <step>
3. <step>

## Actual Behavior

<What happened. Include the tool call, parameters, and response.>

```
Tool: <full tool name as called>(param=value, ...)
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

## Confidence Breakdown

| Dimension | Confidence | Justification |
|-----------|-----------:|---------------|
| <dimension> | <%> | <evidence or admitted gap> |

**Weakest dimension:** <name> at <%> — <what would need to be verified to raise it>

**Overall confidence ceiling (set by the weakest dimension):** <verified | likely | suspected | unverified>

## Alternative Explanations Considered

| Alternative | Ruled out? | How |
|-------------|-----------|-----|
| User error (wrong params) | <yes/no> | <explanation> |
| Stale state | <yes/no> | <explanation> |
| Auth/session issue | <yes/no> | <explanation> |
| Known limitation | <yes/no> | <explanation> |
| Working as designed | <yes/no> | <explanation> |

## Server Logs

<BPA: relevant error lines from server.log, or "No errors found in logs.". Other servers: "No local log file for {SERVER}.">

## Analysis

<Your assessment of what's likely wrong. Reference specific source files
in the MCP server if you can identify them.>

### Likely affected files

- `src/mcp_eregistrations_{server}/tools/<file>.py`

## Filing Destination

- **Target repository:** <UNCTAD-eRegistrations/MCP_eRegistrations | backend repo (name to be confirmed) | consumer repo (name to be confirmed)>
- **Why this repo:** <which layer owns the fix — MCP tool layer, backend, or consumer>

## Requested Outcome

<ONE observable behavior change (Step 5.5e). If several were deliberately kept together, say so here and state why they are inseparable.

Describe the observable behavior that should change, phrased for the chosen destination:

- **If MCP repo:** describe the tool's input/output/behavior that needs to change. The backend capability needed must already exist — if it doesn't, this ticket belongs in the backend repo instead.
- **If backend repo:** describe the capability the backend should expose (field, endpoint, guard, response shape). File and line references are welcome as evidence; the backend team owns the implementation choice.
- **If consumer repo:** describe what the caller should do differently.

Do not prescribe implementation details across repository boundaries. Evidence from another repo (e.g. citing a backend source line in a ticket about the MCP tool) is welcome when it explains the current state — just don't ask the wrong repo's maintainers to change it.>
```
