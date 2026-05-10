---
name: mcp-issue
effort: medium
description: >
  Report an MCP tool issue or feature request (BPA, DS, GDB, or Keycloak).
  TRIGGER when: an MCP tool returns an error, wrong data, or results inconsistent with what
  the user expected — including when Claude observes a suspicious MCP tool response during
  normal work (proactive). Also triggers on "this is broken", "that's not right", "the tool
  did the wrong thing", "it should have done X instead", "report this bug", "the MCP is
  missing X", "we need a tool for X", "expose this backend endpoint as a tool", "request a
  feature".
  DO NOT TRIGGER when: the error is clearly a user input mistake (wrong params, wrong tool),
  auth is expired (suggest re-login instead), or the user is asking about MCP server
  development/code (not tool usage).
license: UNCTAD-Internal
compatibility: Works with or without an active MCP server connection.
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__BPA-local-dev__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
metadata:
  version: "3.5.0"
  version-date: "2026-05-10"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "3.5.0 (2026-05-10): Feature requests are now filable when they pass the same evidence bar as bugs. Replaced the blanket 'no feature requests' gate in Step 9b with three evidence-specific sub-conditions: cited backend capability, Hard-typed evidence, and observable-behavior phrasing. Resolves the internal contradiction between the 'Missing capability' category (Step 3) and the old gate (Step 9b). TRIGGER description and Guidelines updated to match. Per-server wrapper command descriptions broadened from 'issue or unexpected behavior' to 'issue or feature request'."
    - "3.4.1 (2026-04-14): Clarified consumer-project routing — consumers (e.g. SmartRules / SR) may integrate with eRegistrations directly via REST (not via MCP). The earlier wording 'a consumer project that calls the MCP' wrongly excluded SR, which is the actual origin of #58/#68/#69. Added the SR alias everywhere, listed SR's concrete internal surfaces (procedures-api, gdb-sync.js, hash files) as examples."
    - "3.4.0 (2026-04-14): Added the 'Production repositories (routing reference)' table listing the exact GitHub repo names under `UNCTAD-eRegistrations` for MCP, the BPA/DS/GDB/Keycloak backends, and consumer projects (SmartRules). Step 5.5c now references these by exact name instead of asking the user to recall them. The rule 'do not invent a repo name; verify with `gh repo view` and do not fall back to the MCP repo' is explicit."
    - "3.3.0 (2026-04-14): Step 5.5c reframed as a ROUTING decision, not a phrasing rule. Issues whose fix lives in the backend (GDB/BPA/DS/Keycloak) must be filed in that backend's repository, not the MCP repo. MCP-repo tickets are reserved for MCP-tool-layer bugs: wrong API call, response transformation, validation, auth handling, or exposing a backend capability that already exists. Backend source citations remain welcome as EVIDENCE in whichever repo the ticket lands in — the distinction is evidence (allowed) vs. prescription in the wrong repo (not allowed). Step 9 now branches by filing destination."
    - "3.2.0 (2026-04-14): Added Step 5.5 — Scope & Sanitization gate. Reports must not cite local filesystem paths or couple to out-of-scope caller projects (e.g. SmartRules/procedures-api). New confidence dimension 'Scope hygiene'."
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

## Production repositories (routing reference)

The MCP repo and every backend it wraps live under the **`UNCTAD-eRegistrations`** GitHub organization. Use this table when making the routing decision in Step 5.5c.

| Layer | Project | GitHub repository | What belongs here |
|-------|---------|------------------|-------------------|
| MCP tools | MCP server suite | `UNCTAD-eRegistrations/MCP_eRegistrations` | MCP-tool-layer bugs: wrong API call, response transformation, validation, auth handling, exposing an already-supported backend capability |
| Backend (BPA) | BPA backend (Spring Boot / Java) | `UNCTAD-eRegistrations/BPA-backend` | New endpoints, fields, validations, or persistence changes in BPA itself |
| Backend (BPA, frontend) | BPA admin UI (legacy) | `UNCTAD-eRegistrations/BPA-frontend` | BPA admin-UI-side changes (rarely a target for MCP-originated tickets) |
| Backend (BPA, frontend) | BPA admin UI (next) | `UNCTAD-eRegistrations/BPA-frontend-Next` | Same as above for the next-gen admin UI |
| Backend (DS) | DS backend (Django) | `UNCTAD-eRegistrations/DS-Backend` | New endpoints/fields, file lifecycle logic, payments, KYC, process-state in DS |
| Backend (DS, frontend) | DS frontend (Angular) | `UNCTAD-eRegistrations/DS-Frontend` | DS public-facing UI changes |
| Backend (GDB) | GDB backend (Django / DRF) | `UNCTAD-eRegistrations/GDB` | New/changed Django models, serializers, views, versioning, dedup, metadata columns |
| Backend (Keycloak) | Keycloak customizations | `UNCTAD-eRegistrations/Keycloak` | Custom providers, themes, SPI extensions; upstream Keycloak issues go upstream, not here |
| Backend (Keycloak, MCP-side server) | Keycloak MCP server | `UNCTAD-eRegistrations/keycloak-mcp-server` | The MCP bridge for Keycloak (when the issue is specifically in this MCP bridge, not in core Keycloak) |
| Consumer | SmartRules (a.k.a. **SR**) — visual rules editor, integrates directly with the GDB REST API (not via MCP) | `UNCTAD-eRegistrations/SmartRules` | Changes inside SR itself: `procedures-api`, `gdb-sync.js`, hash-file logic, UI. **Do not** surface SR internals inside MCP or backend tickets beyond a one-sentence acknowledgment that a known consumer hit the issue. |

Additional adjacent repos that can be ticket destinations depending on scope: `SmartLink` (API gateway), `GovBridge` (integration platform), `Camunda`, `Cashier`, `Publisher`, `Graylog`, `Translation-Service`. If the routing decision points to one of these, the same rule applies — file there, not in MCP.

**Verifying a repo before filing:** run `gh repo view <org>/<name>` or browse to `https://github.com/UNCTAD-eRegistrations/<name>`. If the repo doesn't exist or you're unsure, stop and ask the user — do not invent a repo name and do not fall back to the MCP repo.

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

**If the tool is working as designed but the user expected different behavior, classify the report as a feature request (category: "Missing capability") rather than a bug.** Feature requests follow the same evidence and routing rules as bugs — see Step 9b for the additional gates that apply.

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

## Step 5.5 — Scope & Sanitization

**This step prevents the single most common failure mode of this skill: dumping unreachable or out-of-scope context into a ticket.** The receiving maintainer only has access to the public MCP repository. Anything that references the reporter's local machine, a separate consumer project, or prescribes changes to a production backend codebase is either unusable or out-of-scope.

Run these filters **before** writing the report. Each one has a concrete rewrite rule.

### 5.5a — Strip local filesystem references

No path beginning with `/Users/`, `/home/`, `~/`, `C:\`, or any host-specific directory may appear in the report. Common offenders this skill has produced in the past:

- Handover notes (`5 - Handovers/*.md`, `~/Desktop/*.md`)
- Spec documents on the reporter's laptop (`/Users/<name>/Claude/...`, `/Users/<name>/OpenGov/...`)
- Session-feedback logs (`gdb-mcp-session-feedback-*.md`)

**Rewrite rule:** replace the path with a *description of what the document contains* only if that description is itself useful. Otherwise, delete the reference. Example:

| Before | After |
|--------|-------|
| `See /Users/unctad/Claude/0 - OpenGov/specs/gdb-integration/04-sr-gdb-ui-spec.md` | _(deleted — receiver can't access it)_ |
| `Full batch context: gdb-mcp-session-feedback-2026-04-11-ui-spec-complement.md` | _(deleted)_ |
| `Per the UI spec's "reviewer check #1"` | `An external consumer that writes to GDB and maintains its own local sync log can drift if the consumer crashes between the GDB write and the local log write.` |

If the evidence only exists in a local file, it is **not evidence the receiver can verify**. Either re-express it as a reproducible MCP-tool observation, or drop the claim.

### 5.5b — Decouple from caller / out-of-scope projects

The MCP repository's concern is the MCP tool surface. Other eRegistrations projects that *use* MCP tools (SmartRules, procedures-api, bot runners, migration scripts) are **out-of-scope** as context providers. Their internal file names, hash-file locations, and implementation quirks must not drive the ticket narrative.

**Rewrite rule:** re-frame the motivation at the MCP-tool level.

| Anti-pattern | Correct frame |
|--------------|---------------|
| "The SR↔GDB sync (`procedures-api/gdb-sync.js`) ships a SHA-256 hash file (`/data/gdb-sync-hashes.json`) to avoid duplicates." | "Any MCP client that calls `gdb_database_modify` repeatedly with an identical schema creates duplicate versions unless it implements its own hashing. This forces every client to re-invent the same logic." |
| "The SR Registry UI spec proposes writing `/data/gdb-sync-log/{procedureId}.json`." | _(deleted — describe the generic problem of missing structured provenance on write)_ |

You may *mention* that "one known consumer encountered this" in a single neutral sentence, but do not quote file paths, internal variable names, or spec-document paragraphs from that consumer project.

### 5.5c — Routing decision: which repository is this ticket for?

This is the **single most important filter** in the skill. Every issue must be routed to the repository that owns the fix. GDB, BPA, DS, and Keycloak are production eRegistrations backends with their **own repositories and release trains** — separate from the MCP repo. The MCP repo only owns the MCP tool layer.

Decide the destination **before** drafting the ticket:

| The fix requires… | File in | Representative examples |
|---|---|---|
| A change to how the MCP tool calls the backend (wrong endpoint, wrong params, bad response transformation, missing validation, auth handling) | **MCP repo** (`UNCTAD-eRegistrations/MCP_eRegistrations`) | Tool maps `service_id` to the wrong URL segment; tool drops a field the backend did return; tool accepts inputs the backend rejects |
| A change to the MCP tool to expose a backend capability **that already exists** in the backend | **MCP repo** | Backend's REST response already includes `created_at`; MCP tool's output shape omits it |
| A new field, column, endpoint, dedup guard, serializer change, migration, or any other modification **inside** the backend itself | **Backend repo** (see the "Production repositories" table above — e.g. `UNCTAD-eRegistrations/GDB`, `.../BPA-backend`, `.../DS-Backend`, `.../Keycloak`) | "Backend should accept a `metadata` JSONB column on write"; "backend should dedup no-op versions"; "backend should add `created_by_user_id`" |
| A change in a consumer project that integrates with an eRegistrations system (directly via REST, or via the MCP) — e.g. `UNCTAD-eRegistrations/SmartRules` (a.k.a. **SR**), migration scripts, bot runners | **That consumer's repo** | SR's `gdb-sync.js` / `procedures-api` sync logic; a migration script's retry policy; a bot runner's field-mapping shim |

**If the fix lives in a backend or consumer repo, do NOT file it in the MCP repo.** Pause and tell the user:

> The fix you're describing requires a change in the {SERVER} backend itself — not in the MCP tool. MCP repo issues can't drive backend changes, and the MCP tool can't expose the capability until the backend supports it. I'll draft the report so it's useful to the {SERVER} team, and you should file it in the {SERVER} repository. Do you want to share the repo URL, or should I save the report locally and skip the filing step?

**Backend source citations are welcome as evidence**, independent of destination. A well-grounded backend-repo ticket benefits from file/line references — that's the maintainer's starting point. The distinction is:

| ✅ Evidence (any repo) | ❌ Prescription in the wrong repo |
|---|---|
| "The `Database` model already has `auto_now_add=True` on a `created_at` column (`models.py:438`), but the serializer (`serializers.py:199`) does not expose it." → fine in an MCP-repo ticket (explaining why the tool can't return it today) AND fine in a backend-repo ticket (pointing at the one-line fix). | "Add `'created_at'` to `DatabaseSerializer.Meta.fields` at `serializers.py:199`" inside an **MCP-repo** ticket — wrong repo for a prescription of a backend change. |

Same file/line, different legitimacy, depending on (a) whether it's framed as evidence vs. prescription and (b) which repo the ticket is filed in.

**Applied to the currently-open examples (#58, #68, #69):** all three ask for Django-layer changes (new metadata column, server-side dedup, new `created_at`/`created_by_user_id` exposure). None of them can be satisfied by changing MCP tool code alone. The correct destination for all three is the backend repository that owns GDB — they are mis-filed today and should be re-opened there (with the sanitization from 5.5a and 5.5b applied in the process).

### 5.5d — Scope checklist (must all pass before Step 6)

Run through this list explicitly. Answer each one:

- [ ] **Filing destination is decided and written into the draft** (MCP repo, specific backend repo, or specific consumer repo).
- [ ] If destination is MCP repo: the fix is plausibly implementable by changing MCP tool code alone (no backend model/endpoint change required).
- [ ] No path beginning with `/Users/`, `/home/`, `~/`, `C:\` anywhere in the draft.
- [ ] No reference to consumer-project files (`procedures-api/...`, `gdb-sync.js`, `gdb-sync-hashes.json`, SR spec documents, etc.) unless the destination *is* that consumer's repo.
- [ ] Backend source citations, if any, are framed as **evidence** (what the code currently does) rather than **prescription** if the destination is the MCP repo.

If any row is unchecked, rewrite or re-route before continuing to Step 6. Mis-routing costs more than two extra minutes of reframing.

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

### Dimensional confidence breakdown (pushback against overconfidence)

A single global confidence score hides weak spots. When asked "how confident are you?", the natural instinct is to reach for the strongest dimension and round up. The dimensional breakdown exists specifically to stop that.

**You MUST build this table before assigning an overall confidence level.** Do not skip it because the earlier sub-sections "already covered it" — hallucination checks, alternative explanations, and claim classification still let weak rows hide under strong ones. Breaking confidence apart axis-by-axis is what surfaces them.

Assign a percentage (0–100%) to every dimension that applies. For each row, the justification must cite evidence or explicitly admit the gap.

| Dimension | What to assess |
|-----------|----------------|
| Tool call reproduction | Did I actually re-run the failing call with the same parameters and observe the same result? |
| Response interpretation | Did I read the actual tool response, or am I paraphrasing from memory? |
| "Expected behavior" claim | Is this backed by the web UI, API docs, or just the user's description? |
| Source code analysis | Did I read the tool implementation file, or am I guessing how it's written? |
| Alternative explanations | Did I actually test each alternative, or did I only list them? |
| Category assignment | Am I certain this is a bug vs a feature request vs user error? |
| Severity assessment | Is the severity backed by what I observed (data loss, silent wrong result, error)? |
| User intent | Do I actually understand what the user was trying to do? |
| Server/instance identification | Am I sure which MCP server and which instance are involved? |
| Scope hygiene | Is the report free of local filesystem paths, consumer-project context, and backend-code prescriptions? (Step 5.5) |

Only include dimensions that apply. Add case-specific rows if the situation demands it (e.g., "classification field mapping" for a GDB issue, "token claim interpretation" for a Keycloak issue).

**Format** — write this down before continuing:

```
| Dimension                     | Confidence | Justification                                                    |
|-------------------------------|-----------:|------------------------------------------------------------------|
| Tool call reproduction        |       95%  | Re-ran the call in this session, got identical error            |
| Response interpretation       |       90%  | Read the raw JSON in context line-by-line                        |
| "Expected behavior" claim     |       55%  | User said "it should return X", no UI screenshot, no docs cited  |
| Source code analysis          |       40%  | Grepped for the function name but did not read the file         |
| Alternative explanations      |       70%  | Ruled out auth and stale state; did not test a different instance|
| Category assignment           |       80%  | Likely "wrong API call" but could also be "data transformation"  |
| Severity assessment           |       75%  | User said "wrong data returned silently" → high                  |
| User intent                   |       85%  | User explained clearly and confirmed                             |
```

**Hard rules:**

1. **The weakest dimension caps the overall confidence level.** Do not average — a 40% row is not erased by a 95% row. See the level table below for exact thresholds.
2. **For each dimension below 80%, you MUST do one of these before writing the report:**
   - **Verify it now** — re-run the call, read the file, ask the user, consult the docs. Bump the percentage only after actual verification.
   - **Downgrade the related claim** to "Assumption — needs verification" in the Claim Classification table, and carry that downgrade through to the Expected Behavior section of the report.
3. **If you cannot estimate a percentage, assign 50%.** Not knowing how confident you are IS low confidence. Do not skip the row.
4. **Every follow-up that can be done right now must be done before Step 7.** Re-running a tool call or reading a source file takes seconds. List the follow-ups explicitly:

   > **What I'd verify before filing:**
   > 1. <concrete action>
   > 2. <concrete action>
   > 3. <concrete action>

**Rationalizations to reject:**

| Rationalization | Reality |
|-----------------|---------|
| "The earlier sub-sections already covered this" | They let weak spots hide under strong ones. The breakdown is what surfaces them. |
| "My overall confidence feels high" | That's exactly the overconfidence pattern. Break it down anyway. |
| "I don't know the exact percentages" | Assign 50% and explain. Not knowing IS low confidence. |
| "This is tedious" | 5 minutes here saves hours of developer time chasing a phantom bug. |
| "The report will flag the weak parts implicitly" | Flagging only happens if you see the gap. The table is what makes you see it. |
| "Step 6 is already long enough" | The length of the checklist is not the bar. An honest confidence floor is. |

If any of those thoughts appear, stop and build the table.

**Carry the breakdown into the report.** The dimensional table must appear in the final report under a "Confidence Breakdown" section (see the template in Step 7). The reviewer benefits from seeing exactly where you were confident and where you were guessing — it tells them where to start investigating.

### Assign confidence level

Derive the overall level from the dimensional breakdown above — specifically from the **weakest dimension**.

| Level | Criteria |
|-------|----------|
| **Verified** | Every dimension ≥ 80%, issue reproduced, expected behavior confirmed from UI/docs, alternatives ruled out |
| **Likely** | Weakest dimension ≥ 70%, reproduced or strong evidence, couldn't fully verify expected behavior |
| **Suspected** | Weakest dimension ≥ 50%, user report is credible but couldn't reproduce or verify independently |
| **Unverified** | Any dimension below 50%, couldn't reproduce, or significant alternative explanations remain |

**Do not assign a level higher than what the weakest dimension allows.** A single 40% row caps the report at "Unverified" regardless of how strong the other dimensions are.

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

<Relevant error lines from server.log, or "No errors found in logs.">

## Analysis

<Your assessment of what's likely wrong. Reference specific source files
in the MCP server if you can identify them.>

### Likely affected files

- `src/mcp_eregistrations_{server}/tools/<file>.py`

## Filing Destination

- **Target repository:** <UNCTAD-eRegistrations/MCP_eRegistrations | backend repo (name to be confirmed) | consumer repo (name to be confirmed)>
- **Why this repo:** <which layer owns the fix — MCP tool layer, backend, or consumer>

## Requested Outcome

<Describe the observable behavior that should change, phrased for the chosen destination:

- **If MCP repo:** describe the tool's input/output/behavior that needs to change. The backend capability needed must already exist — if it doesn't, this ticket belongs in the backend repo instead.
- **If backend repo:** describe the capability the backend should expose (field, endpoint, guard, response shape). File and line references are welcome as evidence; the backend team owns the implementation choice.
- **If consumer repo:** describe what the caller should do differently.

Do not prescribe implementation details across repository boundaries. Evidence from another repo (e.g. citing a backend source line in a ticket about the MCP tool) is welcome when it explains the current state — just don't ask the wrong repo's maintainers to change it.>
```

### Scope rules for the report body

- Do NOT include paths beginning with `/Users/`, `/home/`, `~/`, `C:\` or any host-local directory. If the only source of a claim is a local document, rewrite the claim into a reproducible observation or drop it.
- Do NOT cite files or spec documents from consumer projects (e.g. `procedures-api/gdb-sync.js`, SmartRules specs, migration scripts) unless the destination **is** that consumer's repo. One neutral sentence acknowledging "a known consumer hit this" is the ceiling otherwise.
- Backend source citations (`views.py`, `models.py`, `serializers.py`, line numbers) are **allowed** as evidence — they help the reader locate the current behavior. They are **not allowed** as prescriptions when the destination is the MCP repo, because the MCP repo's maintainers don't merge into the backend.

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

### 9a — Resolve the filing destination first

From Step 5.5c's routing decision:

- **MCP-repo ticket** → continue to 9b and file in `UNCTAD-eRegistrations/MCP_eRegistrations`.
- **Backend-repo ticket** → do **not** use the MCP repo. Ask the user:

  > This ticket belongs in the backend repository for {SERVER}, not the MCP repo. What's the repo (e.g. `UNCTAD-eRegistrations/<name>`)? I can file it there, or save the report locally if you'd prefer to file it manually.

  If the user confirms a backend repo, substitute it into the `gh issue create --repo` call. If they don't know it, save the report and stop — filing in the wrong repo is worse than not filing.

- **Consumer-repo ticket** → same pattern. Ask for the repo; file there or save locally.

Never auto-select the MCP repo as a fallback.

### 9b — Hard gate — do NOT offer to file if:

- Confidence is below **"likely"**
- Any claim in the "Expected Behavior" section has type **"Assumption"** in the claim classification table
- The report is a **feature request** (category: "Missing capability") AND any of the following is true:
    - The "Requested Outcome" cites **no** backend endpoint, field, or capability that already exists OR is in active backend development
    - The "Filing Destination" is the MCP repo but the backend capability that the request relies on is NOT cited as **Hard** evidence in the Claim Classification table
    - The "Requested Outcome" is phrased as a preference ("would be nice", "should consider", "ideally") rather than an observable behavior the maintainer can verify against
- The **Scope hygiene** confidence dimension is below 90%
- The filing destination is unresolved, or the target repo is not the one the routing decision selected

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

4. **Create the issue** (only after explicit user approval — use the repo from 9a, not a hardcoded default):
   ```
   gh issue create --repo <destination-repo-from-9a> \
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
- **Feature request ≠ bug.** If the tool works as designed but the user wants different behavior, classify it as a feature request (category: "Missing capability", label: `enhancement`). Feature requests are filable, but the bar is *evidence the addition is implementable in the chosen repo* — see Step 9b. A feature request that cannot cite a backend capability or a concrete observable outcome is noise, regardless of which side of the bug/feature line it falls.
