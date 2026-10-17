---
name: mcp-issue
effort: medium
description: >
  Report a problem with an MCP tool, or request a feature (BPA, DS, GDB or Keycloak).
  TRIGGER when: an MCP tool returns an error, wrong data, or a result that is different from
  what the user expected. This includes a suspicious MCP tool response that Claude sees during
  normal work (proactive). Also triggers on "this is broken", "that's not right", "the tool
  did the wrong thing", "it should have done X instead", "report this bug", "the MCP is
  missing X", "we need a tool for X", "expose this backend endpoint as a tool", "request a
  feature". Also triggers when the user asks to open any GitHub issue on the MCP repo. This
  includes a request that needs no code change (repo access, a question, an operations task).
  The skill declines that request, or files it with the auto:skip label if the user insists.
  DO NOT TRIGGER when: the error is clearly a user input mistake (wrong parameters, wrong
  tool), the session is expired (suggest a new login), or the user asks about MCP server
  development or code (not tool usage).
license: UNCTAD-Internal
compatibility: Works with or without an active MCP server connection.
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__BPA-local-dev__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
metadata:
  version: "3.9.0"
  version-date: "2026-10-18"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "3.9.0 (2026-10-18): Rewrite in Simplified Technical English (ASD-STE100, Strict mode for agent instructions). No rule, gate, threshold or label changes. New Terms table: problem (what went wrong), report (the markdown file), GitHub issue (what the skill files), maintainer (the person who owns the destination repo). The word 'ticket' is gone, and 'issue' alone always means a GitHub issue. Long sentences, semicolons and em-dash run-ons are split. The report template output and the trigger phrases are unchanged."
    - "3.8.0 (2026-10-18): Added Step 5.5f — Size. The skill lists the files that the Requested Outcome must change. Above 10 files it decomposes the change into at most 6 ordered slices of 10 files or fewer, and files them as an epic in the bot's own split protocol (auto:split-parent, auto:split-child, auto:split-depth:1, auto:split-blocked, manifest comment). The bot's split-chainer then runs the slices in order. A change that does not decompose goes to one design ticket with auto:skip. Reason: the bot's size gate counts files but its splitter divides tasks, so a cross-cutting ticket stalls for days (MCP #481: estimated at 34 files, split twice, the last child still changed 34 files). The scope checklist moves from 5.5f to 5.5g and gains a size row. New Step 9b gate and split-label rows in the label map."
    - "3.7.0 (2026-10-17): Added Step 5.5d — Out of scope. A request that no file change can deliver (repo access, a question, an operations task) gets no ticket: the skill tells the user why and where the request goes instead. If the user insists, the skill files the issue with the auto:skip label in the same gh call, plus a first body line that names the person who must act. Reason: the MCP repo's automation bot treats every issue as a code change. On MCP #834 it closed an access request as 'Shipped' after it merged a tests-only PR, and no person saw the request. New 5.5f checklist row, a Step 9b gate, and an auto:skip row in the label map that is never omitted."
    - "3.6.0 (2026-07-31): Added Step 5.5e — Atomicity. One ticket, one observable behavior change: count the distinct observable changes in Requested Outcome and offer to file N linked tickets when there is more than one. Deliberately a scope-SHAPE rule, not a length rule — measured evidence shows ticket length does not predict how much work a ticket becomes (of six oversized plans on record the smallest originating ticket was 60% below median length, and one was already a split-off child). New Atomicity confidence dimension, a Step 9b blocking condition, a Step 5.5f checklist row, and an explicit note in the Requested Outcome template. Subsumes the weaker 'conflating two issues' line in Step 6, which asked about merged bugs rather than merged asks."
    - "3.5.0 (2026-05-10): Feature requests are now filable when they pass the same evidence bar as bugs. Replaced the blanket 'no feature requests' gate in Step 9b with three evidence-specific sub-conditions: cited backend capability, Hard-typed evidence, and observable-behavior phrasing. Resolves the internal contradiction between the 'Missing capability' category (Step 3) and the old gate (Step 9b). TRIGGER description and Guidelines updated to match. Per-server wrapper command descriptions broadened from 'issue or unexpected behavior' to 'issue or feature request'."
    - "3.4.1 (2026-04-14): Clarified consumer-project routing — consumers (e.g. SmartRules / SR) may integrate with eRegistrations directly via REST (not via MCP). The earlier wording 'a consumer project that calls the MCP' wrongly excluded SR, which is the actual origin of #58/#68/#69. Added the SR alias everywhere, listed SR's concrete internal surfaces (procedures-api, gdb-sync.js, hash files) as examples."
    - "3.4.0 (2026-04-14): Added the 'Production repositories (routing reference)' table listing the exact GitHub repo names under `UNCTAD-eRegistrations` for MCP, the BPA/DS/GDB/Keycloak backends, and consumer projects (SmartRules). Step 5.5c now references these by exact name instead of asking the user to recall them. The rule 'do not invent a repo name; verify with `gh repo view` and do not fall back to the MCP repo' is explicit."
    - "3.3.0 (2026-04-14): Step 5.5c reframed as a ROUTING decision, not a phrasing rule. Issues whose fix lives in the backend (GDB/BPA/DS/Keycloak) must be filed in that backend's repository, not the MCP repo. MCP-repo tickets are reserved for MCP-tool-layer bugs: wrong API call, response transformation, validation, auth handling, or exposing a backend capability that already exists. Backend source citations remain welcome as EVIDENCE in whichever repo the ticket lands in — the distinction is evidence (allowed) vs. prescription in the wrong repo (not allowed). Step 9 now branches by filing destination."
    - "3.2.0 (2026-04-14): Added Step 5.5 — Scope & Sanitization gate. Reports must not cite local filesystem paths or couple to out-of-scope caller projects (e.g. SmartRules/procedures-api). New confidence dimension 'Scope hygiene'."
---

# Report an MCP problem

You help the user document a functional problem with an eRegistrations MCP server. You produce a structured markdown report. A maintainer uses the report to reproduce the problem and fix it.

**Your role:** be a patient but skeptical investigator. The user may be non-technical. Help them describe what went wrong, and do not use jargon. Verify each claim before you write it down. AI agents, you included, can invent problems, misread responses, or confuse expected behavior with a real bug.

**Core principle:** verify each report. Do not only transcribe what the user says. A wrong bug report costs a maintainer more time than no report.

## Terms

This skill uses each term below with one meaning only.

| Term | Meaning |
|---|---|
| **problem** | What went wrong, or what the user asks for. |
| **report** | The markdown file that this skill writes in Step 7. |
| **GitHub issue** | The item that this skill files on GitHub in Step 9. "Issue" alone always means a GitHub issue. |
| **maintainer** | The person who owns the destination repo and reads the GitHub issue. |
| **destination repo** | The repo that owns the fix, from the routing decision in Step 5.5c. |
| **Requested Outcome** | The report section that names the change the user asks for. |
| **the bot** | The automation bot on the MCP repo. It triages each new GitHub issue and tries to deliver it as a code change. |
| **slice**, **epic** | Step 5.5f: one part of a big change, and the parent GitHub issue that holds the slices in order. |

Exception: the title of the report template (Step 7) and the Step 8 message use "Issue" for the report. That use does not mean a GitHub issue.

## Supported MCP servers

| Server | Tool prefix | Config path | Source path |
|--------|------------|-------------|-------------|
| **BPA** | `mcp__BPA__` | `~/.config/mcp-eregistrations-bpa/` | `src/mcp_eregistrations_bpa/tools/` |
| **DS** | `mcp__DS__` | `~/.config/mcp-eregistrations-ds/` | `src/mcp_eregistrations_ds/tools/` |
| **GDB** | `mcp__GDB__` | `~/.config/mcp-eregistrations-gdb/` | `src/mcp_eregistrations_gdb/tools/` |
| **Keycloak** | `mcp__Keycloak__` | `~/.config/mcp-eregistrations-keycloak/` | `src/mcp_eregistrations_keycloak/tools/` |

In this skill, `{SERVER}` is the server that you identify (BPA, DS, GDB or Keycloak). `{server}` is the same name in lowercase (bpa, ds, gdb, keycloak).

## Production repositories (routing reference)

The MCP repo and each backend that it wraps are in the **`UNCTAD-eRegistrations`** GitHub organization. Use this table for the routing decision in Step 5.5c.

| Layer | Project | GitHub repository | What belongs here |
|-------|---------|------------------|-------------------|
| MCP tools | MCP server suite | `UNCTAD-eRegistrations/MCP_eRegistrations` | MCP-tool-layer bugs: wrong API call, response transformation, validation, auth handling, exposure of a backend capability that already exists |
| Backend (BPA) | BPA backend (Spring Boot / Java) | `UNCTAD-eRegistrations/BPA-backend` | New endpoints, fields, validations or persistence changes in BPA itself |
| Backend (BPA, frontend) | BPA admin UI (legacy) | `UNCTAD-eRegistrations/BPA-frontend` | Changes in the BPA admin UI (rarely the destination for a problem found through MCP) |
| Backend (BPA, frontend) | BPA admin UI (next) | `UNCTAD-eRegistrations/BPA-frontend-Next` | The same, for the next-generation admin UI |
| Backend (DS) | DS backend (Django) | `UNCTAD-eRegistrations/DS-Backend` | New endpoints or fields, file lifecycle logic, payments, KYC, process state in DS |
| Backend (DS, frontend) | DS frontend (Angular) | `UNCTAD-eRegistrations/DS-Frontend` | Changes in the public DS UI |
| Backend (GDB) | GDB backend (Django / DRF) | `UNCTAD-eRegistrations/GDB` | New or changed Django models, serializers, views, versioning, dedup, metadata columns |
| Backend (Keycloak) | Keycloak customizations | `UNCTAD-eRegistrations/Keycloak` | Custom providers, themes, SPI extensions. Problems in upstream Keycloak go upstream, not here. |
| Backend (Keycloak, MCP-side server) | Keycloak MCP server | `UNCTAD-eRegistrations/keycloak-mcp-server` | The MCP bridge for Keycloak, when the problem is in this bridge and not in core Keycloak |
| Consumer | SmartRules (also called **SR**): a visual rules editor. It calls the GDB REST API directly, not through MCP. | `UNCTAD-eRegistrations/SmartRules` | Changes inside SR itself: `procedures-api`, `gdb-sync.js`, hash-file logic, UI. **Do not** put SR internals in an MCP or backend GitHub issue. One sentence that says a known consumer hit the problem is the limit. |

Other repos can also be the destination repo, depending on scope: `SmartLink` (API gateway), `GovBridge` (integration platform), `Camunda`, `Cashier`, `Publisher`, `Graylog`, `Translation-Service`. If the routing decision selects one of these repos, the same rule applies: file there, not in the MCP repo.

**Verify a repo before you file:** run `gh repo view <org>/<name>`, or open `https://github.com/UNCTAD-eRegistrations/<name>`. If the repo does not exist, or you are not sure, stop and ask the user. Do not invent a repo name. Do not use the MCP repo as a fallback.

## Step 1 — Identify the server and understand what happened

First, identify the MCP server. Look for:
- The tool prefix in the failed call (`mcp__BPA__`, `mcp__DS__`, `mcp__GDB__`, `mcp__Keycloak__`).
- Clues in the context: forms or determinants → BPA, files or payments → DS, databases or records → GDB, users or realms → Keycloak.
- If it is not clear, ask the user.

Then ask the user to describe the problem in their own words. A good question:

> What were you trying to do? What happened instead of what you expected?

Listen for:
- The tool, or the action that the user tried.
- The instance.
- An error message, or only wrong data.
- Whether the same action works correctly in the web UI.

If the problem is in the current conversation (for example, a tool call that returned wrong data or an error), refer to it directly. Do not make the user repeat what is already in context.

## Step 2 — Collect environment details

Collect these details yourself. Do not ask the user for them.

1. **Server version and instances:** call `mcp__{SERVER}__connection_status(instance="<name>")` for the affected instance. The response has the fields `version`, `latest_version` and `update_available`. Also call `mcp__{SERVER}__instance_list()` to record the registered instances.

2. **Today's date:** run this with Bash:
   ```
   date +%Y-%m-%d
   ```

3. **Recent server log errors** (if available): run this with Bash:
   ```
   find ~/.config/mcp-eregistrations-{server}/instances -name 'server.log' -exec grep -E 'ERROR|CRITICAL' {} \; 2>/dev/null | tail -10
   ```

## Step 3 — Identify the root cause area

Use what the user described to select one category:

| Category | Symptoms |
|----------|----------|
| **Wrong API call** | The tool sends an incorrect HTTP method, path or parameters. |
| **Data transformation** | The response data is damaged, has missing fields, or has the wrong format. |
| **UI mismatch** | The tool gives a different result from the same action in the web UI. |
| **Missing validation** | The tool accepts input that the UI rejects. |
| **Auth/connection** | Token errors, timeouts, or the wrong instance. |
| **Missing capability** | The tool does not support an operation that the UI supports. |

Ask a clarifying question only if you cannot select a category. Do not interrogate the user.

## Step 4 — Reproduce and verify

**This step is critical. Do NOT skip it.**

Before you write anything, verify that the problem is real and that you can reproduce it.

### 4a. Run the failed tool call again

If the original tool call is in the conversation, run it again with the **exact same parameters**. Compare the results:

| Outcome | Action |
|---------|--------|
| Same error or same wrong result | The problem is confirmed. Go to Step 5. |
| Different error | Record both results. The problem can be intermittent or depend on state. |
| Works correctly now | **Stop.** Tell the user: "I ran the same call again and it succeeded. The first failure was possibly temporary (an expired session, the network, a server restart). Do you still want me to file it as intermittent?" |

### 4b. Rule out user error

Try variations. Find out if the cause is the tool or the input.

- **Wrong parameters?** If the tool expects a service_id and the user gave a registration_id, that is not a bug. Check the parameter types and values.
- **Wrong tool?** For example, the user called `determinant_get` but meant `determinant_list`. Suggest the correct tool.
- **Stale state?** An earlier operation (a delete or an update) can change the data. Read the resource again to see its current state.
- **Expired session?** Log in again and try again before you blame the tool.

### 4c. Compare with the source (if available)

If the MCP server source code is available on this machine, examine the tool implementation:

```
# Find the tool source
grep -r "def <tool_name>" src/mcp_eregistrations_{server}/tools/ 2>/dev/null
```

Read the function to learn:
- Which API endpoint it calls.
- Which transformations it applies to the response.
- Whether the "expected behavior" that the user described is what the tool is designed to do.

**If the tool works as designed but the user expected a different behavior, the report is a feature request (category: "Missing capability"), not a bug.** A feature request follows the same evidence and routing rules as a bug. Step 9b adds more gates for feature requests.

### 4d. Verify "expected behavior" claims

Invented claims usually hide here. Before you accept a claim about what _should_ happen:

- **Read the API reference**, if it is available.
- **Read the tool docstring:** does it promise what the user expects?
- **Compare with the web UI** (if the user can confirm): does the UI really do what the user says?

**Never write "Expected: X" in a report without evidence that X is correct.** If you are not sure, write "Expected behavior needs verification" and give the reason.

## Step 5 — Record the technical details

If the failed tool call is in the current conversation, record:
- The **tool name** and the **parameters**.
- The **response** (or the error message).
- The **reproduction result** from Step 4: confirmed, intermittent or not reproduced.
- The **expected response**, and its source: the user's description, a UI comparison or the API docs.

The user can possibly show what the web UI does for the same action: a screenshot, the network tab or a description. If so, record that as the baseline for "expected behavior".

## Step 5.5 — Scope and sanitization

**This step prevents the most common failure of this skill.** That failure is a report full of context that the maintainer cannot reach, or that is out of scope. The maintainer can see only the public MCP repository. The maintainer cannot use these references:

- A reference to the user's own machine.
- A reference to a separate consumer project.
- A prescription of a change to a production backend codebase.

Apply these filters **before** you write the report. Each filter has a rewrite rule.

### 5.5a — Remove local filesystem references

The report must not contain a path that starts with `/Users/`, `/home/`, `~/` or `C:\`, or any other directory on one host. This skill produced these offenders in the past:

- Handover notes (`5 - Handovers/*.md`, `~/Desktop/*.md`).
- Specification documents on the user's laptop (`/Users/<name>/Claude/...`, `/Users/<name>/OpenGov/...`).
- Session-feedback logs (`gdb-mcp-session-feedback-*.md`).

**Rewrite rule:** replace the path with a *description of what the document contains*, but only if that description is useful. If it is not useful, delete the reference. Examples:

| Before | After |
|--------|-------|
| `See /Users/unctad/Claude/0 - OpenGov/specs/gdb-integration/04-sr-gdb-ui-spec.md` | _(deleted: the maintainer cannot open it)_ |
| `Full batch context: gdb-mcp-session-feedback-2026-04-11-ui-spec-complement.md` | _(deleted)_ |
| `Per the UI spec's "reviewer check #1"` | `An external consumer that writes to GDB and keeps its own local sync log can drift if the consumer crashes between the GDB write and the local log write.` |

If the evidence exists only in a local file, the maintainer **cannot verify it**. Write it again as an MCP-tool observation that the maintainer can reproduce, or remove the claim.

### 5.5b — Separate the report from caller projects and out-of-scope projects

The MCP repository is about the MCP tool surface. Other eRegistrations projects *use* MCP tools: SmartRules, procedures-api, bot runners, migration scripts. These projects are **out of scope** as sources of context. Their internal file names, hash-file locations and implementation details must not drive the report.

**Rewrite rule:** state the motivation at the level of the MCP tool.

| Anti-pattern | Correct frame |
|--------------|---------------|
| "The SR↔GDB sync (`procedures-api/gdb-sync.js`) ships a SHA-256 hash file (`/data/gdb-sync-hashes.json`) to avoid duplicates." | "Any MCP client that calls `gdb_database_modify` repeatedly with an identical schema creates duplicate versions unless it implements its own hashing. This forces every client to re-invent the same logic." |
| "The SR Registry UI spec proposes writing `/data/gdb-sync-log/{procedureId}.json`." | _(deleted: describe the general problem, which is the missing structured provenance on write)_ |

You can *mention* in one neutral sentence that "one known consumer encountered this". Do not quote file paths, internal variable names or specification paragraphs from that consumer project.

### 5.5c — Routing decision: which repository owns the fix?

This is the **most important filter** in the skill. Each report must go to the repository that owns the fix. GDB, BPA, DS and Keycloak are production eRegistrations backends. Each one has its **own repository and its own release train**, separate from the MCP repo. The MCP repo owns only the MCP tool layer.

Select the destination repo **before** you draft the report:

| The fix requires… | File in | Representative examples |
|---|---|---|
| A change to how the MCP tool calls the backend (wrong endpoint, wrong parameters, bad response transformation, missing validation, auth handling) | **MCP repo** (`UNCTAD-eRegistrations/MCP_eRegistrations`) | The tool maps `service_id` to the wrong URL segment. The tool drops a field that the backend returned. The tool accepts input that the backend rejects. |
| A change to the MCP tool to expose a backend capability **that already exists** in the backend | **MCP repo** | The backend REST response already includes `created_at`, but the MCP tool output omits it. |
| A new field, column, endpoint, dedup guard, serializer change, migration, or any other change **inside** the backend | **Backend repo** (see the "Production repositories" table, for example `UNCTAD-eRegistrations/GDB`, `.../BPA-backend`, `.../DS-Backend`, `.../Keycloak`) | "Backend should accept a `metadata` JSONB column on write". "Backend should dedup no-op versions". "Backend should add `created_by_user_id`". |
| A change in a consumer project. A consumer project calls an eRegistrations system directly through REST, or through the MCP. Examples: `UNCTAD-eRegistrations/SmartRules` (**SR**), migration scripts, bot runners. | **That consumer's repo** | The sync logic in SR's `gdb-sync.js` or `procedures-api`. The retry policy of a migration script. The field-mapping shim of a bot runner. |

**If the fix is in a backend repo or a consumer repo, do NOT file it in the MCP repo.** Stop and tell the user:

> The fix you describe needs a change in the {SERVER} backend itself, not in the MCP tool. A GitHub issue in the MCP repo cannot change the backend. The MCP tool cannot expose the capability until the backend supports it. I'll write the report so that it is useful to the {SERVER} team, and you file it in the {SERVER} repository. Can you give me the repo URL? Or should I save the report locally and skip the filing step?

**Backend source citations are welcome as evidence**, in any destination repo. A backend GitHub issue with file and line references gives the maintainer a starting point. The difference is this:

| ✅ Evidence (any repo) | ❌ Prescription in the wrong repo |
|---|---|
| "The `Database` model already has `auto_now_add=True` on a `created_at` column (`models.py:438`), but the serializer (`serializers.py:199`) does not expose it." This is correct in an MCP-repo GitHub issue (it explains why the tool cannot return the field today). It is also correct in a backend-repo GitHub issue (it points at the one-line fix). | "Add `'created_at'` to `DatabaseSerializer.Meta.fields` at `serializers.py:199`" in an **MCP-repo** GitHub issue. This prescribes a backend change in the wrong repo. |

The same file and line can be correct or incorrect. That depends on two things: (a) whether the text is evidence or a prescription, and (b) which repo receives the GitHub issue.

**Examples #58, #68 and #69:** all three ask for changes in the Django layer (a new metadata column, server-side dedup, exposure of `created_at` and `created_by_user_id`). A change to MCP tool code alone cannot deliver any of them. Their correct destination repo is the backend repository that owns GDB. They were filed in the wrong repo. They should be opened again there, with the sanitization from 5.5a and 5.5b.

### 5.5d — Out of scope: no file change can deliver the request

Some requests do not ask for a change to any file in any repository. Examples:

| Request | Why no file change delivers it | Where the request goes instead |
|---|---|---|
| "Give @user read access to repo X." | Repo access is a GitHub org or repo setting. | A maintainer or an org admin, directly. |
| "How do I configure tool Y?" | It is a question. Nothing is broken. | Answer it in this session, or ask the maintainers in chat. |
| "Deploy, restart or upgrade instance Z." | It is an operations task on a server. | The team that operates instance Z. |
| "Create an account, reset a password or add a role on instance Z." | It is an admin action in a live system. | The instance admin. |

**Test:** name one file in the destination repo that must change to deliver the Requested Outcome. If you cannot name one, the request is out of scope.

**Why this step exists:** the bot triages each new GitHub issue on the MCP repo. It tries to deliver each one as a code change. For an out-of-scope request, the bot writes a change that does nothing, merges it, and closes the GitHub issue as "Shipped". No person sees the request. This occurred on MCP #834 (2026-10-17): the bot closed an access request after it merged a PR that only added tests.

**If all of the request is out of scope:** do not draft a GitHub issue. Tell the user:

> This request does not need a change to any repository file: {reason}. A GitHub issue is the wrong channel for it. The bot would try to deliver it as a code change and close it, and no person would act on it. Instead: {where the request goes}.

**If the user still wants a GitHub issue:** file it only with the `auto:skip` label. The bot does not triage a GitHub issue that has `auto:skip`, and it does not pick that issue up. Put this line first in the issue body:

> **Out of scope for automation — no code change requested.** A person must act: {who, and the action}.

Set the label in the same `gh issue create` call that creates the GitHub issue. Do not add the label after the issue exists, because the bot can triage the issue between the two calls. Skip Steps 6–7 for this issue. The body is the out-of-scope line plus the user's request in their own words.

**If only part of the request is out of scope:** apply 5.5e. File the in-scope part as a normal GitHub issue. Use the rules above for the out-of-scope part.

### 5.5e — Atomicity: one GitHub issue, one observable behavior change

A GitHub issue that asks for several things at once cannot be reviewed, estimated or shipped as one unit. It also weakens the user's position. If a maintainer disagrees with *one* of three asks, the maintainer must reject or renegotiate the whole issue.

**This is a rule about the shape of the scope, not about length.** Do not use the length of the report as a gate. Short reports are often the broadest ones. One sentence can name a change that touches thirty files. A long report is often long because it gives much *evidence* about one narrow change. Length tells you nothing. The number of requested behavior changes tells you a lot.

**How to count.** Read only the **Requested Outcome** section. Count the different *observable* changes. An observable change is one thing that a user or a caller can see happen differently afterwards. Do not count the supporting text: evidence, reproduction and analysis do not count.

| Requested Outcome | Count | Why |
|---|---|---|
| "`service_publish` should return a publish id instead of an empty body." | 1 | One observable change. **File it.** |
| "Hold the page while writing, **and** refuse the write when a human holds it." | 2 | Two behaviors. Each one can ship alone, and each one can be argued alone. **Split.** |
| "Expose `created_at` on the read tools, **and** add a `--since` filter, **and** fix the timezone." | 3 | Three. **Split.** |
| "Return the audit id, so callers can correlate the write with the audit log." | 1 | The clause after "so" is the *motivation*, not a second change. **File it.** |

Two traps when you count:

- **The word "and" is not the signal. A second outcome that a maintainer can verify is the signal.** "Validate the payload and return 400" is one change in two clauses. "Validate the payload and add a retry" is two changes.
- **A conjunction in the title also counts.** Read the title as part of the Requested Outcome.

**If the count is more than 1:** do not file one GitHub issue. Tell the user:

> This report asks for {N} separate changes: {list them}. In one GitHub issue, they can't be reviewed or shipped separately. If the maintainer disagrees with one of them, the others stall too. I suggest {N} linked GitHub issues, each with its own evidence. Do you want me to split it that way? (Say "file as one" if they really must ship together, for example because half of the change is useless alone.)

If the user says that the changes must ship together, file one GitHub issue. State this in the Requested Outcome: *"These {N} changes are inseparable because …"*. A maintainer can review a stated reason. A maintainer cannot review an unstated merge.

**What this rule does and does not give you.** It makes each GitHub issue reviewable, and each one can ship alone. It does **not** make the work small. A GitHub issue with one behavior change can still need a large change. The measured evidence is clear: of six oversized plans on record, the *smallest* original report was 60% shorter than the median report. One of the six was already a child of an earlier split. The size of the work depends on how much code the change touches. The user often cannot see that code. Use this rule to split for reviewability. Step 5.5f handles size.

This rule covers more than the question "Do I merge two different problems into one?" in the Step 6 hallucination table. That question stays in Step 6. It asks if you merged two *bugs*. This rule asks if you merged two *asks*, which is the more common failure.

### 5.5f — Size: decompose a big change into ordered GitHub issues

The bot cannot deliver a big change in one PR. Its size gate counts the files that a change touches. On the MCP repo, the gate is 25 files, and an early check runs during the bot's spec phase. When a GitHub issue is over the gate, the bot splits it by task. A task split often does not lower the file count, because the tasks change the same files. The issue then stalls for days. Example: the bot estimated MCP #481 at 34 files and split it twice. The last child still changed 34 files.

You can see the files before the bot does. Decompose the change when you file it.

**1. List the files.** List each file that the Requested Outcome must change. Use the source tree (Step 4c). If you cannot read the source, estimate from the tools and the packages that the request names. Typical sizes on the MCP repo:

| Change | Typical files |
|---|---|
| Fix in one existing tool | 2: the tool module and its test |
| New read tool in an existing module | 3: the module, the registration, the test |
| New write tool | 5: the module, `tools/__init__.py`, `server.py`, `rollback/manager.py`, the test |
| One rule for every write tool, or for every package | 1 per module plus tests, often more than 20 |

**2. If the list has 10 files or fewer,** file one GitHub issue. Go to 5.5g. The limit is 10, not 25, because a list made at filing time usually misses docs and tests that the bot must also change.

**3. If the list has more than 10 files,** decompose the change into slices. Each slice must obey these rules:

- The slice changes 10 files or fewer.
- The slice delivers one observable behavior change (5.5e), and a maintainer can verify it alone.
- The slice needs only the slices before it. Put shared code first: a helper or a client method that later slices use goes in slice 1.
- Two slices can change the same registration file, for example `server.py`. If most slices need most of the same files, the change does not decompose. Go to item 5.
- Make 6 slices or fewer. If the change needs more than 6, go to item 5.

**4. File the slices as an epic.** Use the bot's split protocol. The bot then runs the slices in order without help.

1. Create the parent GitHub issue with the label `auto:split-parent`. The body states the full problem and lists the slices. The bot does not triage a parent and does not pick it up.
2. Create slice 1 with the labels `auto:split-child,auto:split-depth:1`.
3. Create each later slice with the labels `auto:split-child,auto:split-depth:1,auto:split-blocked`. The bot does not work on a blocked slice.
4. Post this comment on the parent. Write the slice numbers in order: `<!-- autopilot:split children=#A,#B,#C depth=1 -->`

Set the labels in each `gh issue create` call, not after it. Without its labels, a later slice can get triaged before its turn.

The bot works on slice 1 first. When a slice closes, the bot removes `auto:split-blocked` from the next slice. When all slices are closed, the bot closes the parent. If an estimate is wrong, `auto:split-depth:1` lets the bot split one slice once more.

Keep each slice body short. Write the slice's tasks, its files, and the line `Part {N} of #{parent}`. Do not copy the full parent text into each slice. Put this line last: *"Before you start, compare each task with `main`. Remove each task that an earlier slice already delivered."* A blocked slice waits while earlier slices change `main`.

**5. If the change does not decompose,** file one design GitHub issue with the label `auto:skip`. The body states the problem, the file list, and why the change does not decompose. A person plans the slices, then files them with item 4.

Show the user the slice plan before you file anything (Step 9, Filing, item 3).

### 5.5g — Scope checklist (all items must pass before Step 6)

Answer each item explicitly:

- [ ] **At least one file in the destination repo must change to deliver the Requested Outcome** (5.5d). If no file must change, use the out-of-scope path in 5.5d.
- [ ] **The file list has 10 files or fewer** (5.5f). If not, the change is decomposed into an epic of slices, or filed as one design GitHub issue with `auto:skip`.
- [ ] **The Requested Outcome names exactly ONE observable behavior change** (5.5e). The exception: the user explicitly chose to keep several changes together, and the report states the reason.
- [ ] **The destination repo is decided and written in the draft** (the MCP repo, a specific backend repo or a specific consumer repo).
- [ ] If the destination repo is the MCP repo: a change to MCP tool code alone can plausibly deliver the fix. No backend model or endpoint change is necessary.
- [ ] The draft contains no path that starts with `/Users/`, `/home/`, `~/` or `C:\`.
- [ ] The draft contains no reference to consumer-project files (`procedures-api/...`, `gdb-sync.js`, `gdb-sync-hashes.json`, SR specification documents, and similar). The exception: the destination repo *is* that consumer's repo.
- [ ] If the destination repo is the MCP repo, each backend source citation is **evidence** (what the code does now), not a **prescription**.

If an item is not checked, rewrite or re-route the report before you go to Step 6. Wrong routing costs more than two extra minutes of rewriting.

## Step 6 — Adversarial self-review

Before you write the report, answer each question below **honestly**. Write down each answer for yourself, not in the report.

### Hallucination check

| Question | If YES → |
|----------|----------|
| Do I claim that the tool "should" do X without evidence? | Remove the claim, or mark it "needs verification". |
| Did I read the error message carefully, or do I paraphrase it from memory? | Read the actual response again. |
| Do I merge two different problems into one? | Split them into separate reports. |
| Is my "expected behavior" based on how _I think_ the API works, or on real docs or the UI? | Cite your source, or lower the confidence. |
| Did the user really say this, or do I infer it? | Quote the user's words. Do not interpret them. |

### Alternative explanations

Before you conclude "this is a bug", examine each alternative:

1. **User error:** wrong parameters, wrong tool, or a misunderstanding of what the tool does.
2. **Stale state:** the data changed between operations.
3. **Auth or session problem:** an expired token, or the wrong instance.
4. **Known limitation:** the tool docstring says that the tool does not support this case.
5. **Working as designed:** the behavior is intentional, but it is not what the user wanted.
6. **Environment problem:** a version mismatch, the network, or a problem on the server.

For each alternative, record whether you ruled it out and how. If you cannot rule out an alternative, mention it in the report.

### Claim classification (First Principles)

Make this table for each factual claim that the report will contain. This table is not optional. It is the structural filter that stops bad reports from being filed.

| Claim | Type | Evidence |
|-------|------|----------|
| _"Tool returns X"_ | **Hard** (reproduced) | Ran the call again, got the same result |
| _"Should return Y"_ | **Assumption** (not verified) | The user said so, no UI or doc confirmation |
| _"Field Z is missing"_ | **Hard** (observed) | Compared the response with a UI screenshot |

Type definitions:
- **Hard:** you observed this directly (tool output, reproduction, source code, UI comparison).
- **Soft:** a reasonable inference from the docs or the tool docstring, but not observed directly.
- **Assumption:** a claim from the user, your own inference, or "how you think it should work". There is no direct evidence.

**Mark each claim of type "Assumption" as "needs verification" in the report.** Do not present an assumption as a fact.

### Failure lens (Iterative Depth)

Before you continue, answer this question honestly:

> **If this report is wrong, what damage does it cause?** Will a maintainer spend hours trying to reproduce a problem that does not exist? Will a maintainer "fix" something that was not broken, and add a real bug?

If the answer is "significant damage" and the report has Assumption-type claims, **stop and tell the user** which evidence you need before you continue.

### Confidence breakdown by dimension (protection against overconfidence)

One global confidence score hides weak areas. When someone asks "how confident are you?", the natural reaction is to use the strongest dimension and round up. This breakdown exists to stop that reaction.

**You MUST make this table before you assign an overall confidence level.** Do not skip it because the earlier sub-sections "already covered it". The hallucination check, the alternative explanations and the claim classification still let weak rows hide behind strong ones. A breakdown by dimension shows them.

Give a percentage (0–100%) to each dimension that applies. For each row, the justification must cite evidence or state the gap.

| Dimension | What to assess |
|-----------|----------------|
| Tool call reproduction | Did I really run the failed call again with the same parameters and see the same result? |
| Response interpretation | Did I read the actual tool response, or do I paraphrase it from memory? |
| "Expected behavior" claim | Does the web UI, the API docs or only the user's description support it? |
| Source code analysis | Did I read the tool implementation file, or do I guess how it is written? |
| Alternative explanations | Did I test each alternative, or did I only list them? |
| Category assignment | Am I certain of the category: a bug, a feature request or a user error? |
| Severity assessment | Does what I observed support the severity (data loss, silent wrong result, error)? |
| User intent | Do I really understand what the user tried to do? |
| Server/instance identification | Am I sure which MCP server and which instance are involved? |
| Scope hygiene | Is the report free of local filesystem paths, consumer-project context and backend-code prescriptions? (Step 5.5) |
| Atomicity | Does the Requested Outcome name exactly ONE observable behavior change? (Step 5.5e) |

Include only the dimensions that apply. Add rows for the specific case if necessary, for example "classification field mapping" for a GDB problem, or "token claim interpretation" for a Keycloak problem.

**Format.** Write this table down before you continue:

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
| Atomicity                     |       60%  | Outcome asks for a new field AND a new filter — 2 changes        |
```

**Hard rules:**

1. **The weakest dimension sets the maximum overall confidence level.** Do not calculate an average. A 95% row does not cancel a 40% row. The level table below gives the exact thresholds.
2. **For each dimension below 80%, you MUST do one of these before you write the report:**
   - **Verify it now:** run the call again, read the file, ask the user or read the docs. Raise the percentage only after the verification.
   - **Lower the related claim** to "Assumption — needs verification" in the claim classification table. Carry that change into the Expected Behavior section of the report.
3. **If you cannot estimate a percentage, use 50%.** Not knowing how confident you are IS low confidence. Do not skip the row.
4. **Do each follow-up that you can do now before Step 7.** A new run of a tool call, or a read of a source file, takes seconds. List the follow-ups explicitly:

   > **What I'd verify before filing:**
   > 1. <concrete action>
   > 2. <concrete action>
   > 3. <concrete action>

**Rationalizations to reject:**

| Rationalization | Reality |
|-----------------|---------|
| "The earlier sub-sections already covered this" | They let weak areas hide behind strong ones. The breakdown shows them. |
| "My overall confidence feels high" | That is exactly the overconfidence pattern. Make the breakdown anyway. |
| "I don't know the exact percentages" | Use 50% and give the reason. Not knowing IS low confidence. |
| "This is tedious" | 5 minutes here save a maintainer hours on a bug that does not exist. |
| "The report will flag the weak parts implicitly" | You flag a gap only if you see it. The table makes you see it. |
| "Step 6 is already long enough" | The length of the checklist is not the standard. An honest confidence floor is. |

If you have one of these thoughts, stop and make the table.

**Put the breakdown in the report.** The table must be in the final report, in the "Confidence Breakdown" section (see the template in Step 7). The maintainer sees exactly where you were confident and where you guessed. This tells the maintainer where to start.

### Assign the confidence level

Use the dimension table above to find the overall level. The **weakest dimension** decides it.

| Level | Criteria |
|-------|----------|
| **Verified** | Each dimension ≥ 80%, the problem is reproduced, the expected behavior is confirmed from the UI or docs, the alternatives are ruled out |
| **Likely** | Weakest dimension ≥ 70%, the problem is reproduced or the evidence is strong, the expected behavior is not fully verified |
| **Suspected** | Weakest dimension ≥ 50%, the user's description is credible, but you could not reproduce or verify it yourself |
| **Unverified** | A dimension is below 50%, you could not reproduce the problem, or important alternative explanations remain |

**Do not assign a level higher than the weakest dimension allows.** One 40% row sets the report to "Unverified", whatever the other dimensions are.

**If the confidence is "Unverified", tell the user before you write the report.** The user may want to collect more evidence first.

## Step 7 — Write the report

Create the report directory:

```
mkdir -p ~/Desktop/mcp-issue-reports
```

Write the report to `~/Desktop/mcp-issue-reports/<date>-<server>-<slug>.md`. `<server>` is the server name in lowercase. `<slug>` is a short kebab-case summary, for example `2026-04-02-bpa-effect-create-wrong-format`.

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

<ONE observable behavior change (Step 5.5e). If several were deliberately kept together, say so here and state why they are inseparable.

Describe the observable behavior that should change, phrased for the chosen destination:

- **If MCP repo:** describe the tool's input/output/behavior that needs to change. The backend capability needed must already exist — if it doesn't, this ticket belongs in the backend repo instead.
- **If backend repo:** describe the capability the backend should expose (field, endpoint, guard, response shape). File and line references are welcome as evidence; the backend team owns the implementation choice.
- **If consumer repo:** describe what the caller should do differently.

Do not prescribe implementation details across repository boundaries. Evidence from another repo (e.g. citing a backend source line in a ticket about the MCP tool) is welcome when it explains the current state — just don't ask the wrong repo's maintainers to change it.>
```

### Scope rules for the report body

- Do NOT include a path that starts with `/Users/`, `/home/`, `~/` or `C:\`, or any other directory on one host. If a claim comes only from a local document, write the claim again as an observation that the maintainer can reproduce, or remove it.
- Do NOT cite files or specification documents from consumer projects (for example `procedures-api/gdb-sync.js`, SmartRules specifications, migration scripts). The exception: the destination repo **is** that consumer's repo. Otherwise, the limit is one neutral sentence that says "a known consumer hit this".
- Backend source citations (`views.py`, `models.py`, `serializers.py`, line numbers) are **permitted** as evidence. They help the maintainer find the current behavior. They are **not permitted** as prescriptions when the destination repo is the MCP repo, because the MCP maintainers do not merge into the backend.

## Step 8 — Confirm with the user

Show the user the report path and a short summary of what you recorded:

> Issue report saved to `~/Desktop/mcp-issue-reports/<filename>.md`
>
> **Summary:** <one line>
> **Server:** <BPA | DS | GDB | Keycloak>
> **Category:** <category>
> **Severity:** <severity>
> **Confidence:** <level> — <one-line justification>
>
> You can share this file with the MCP development team. Do you want me to change anything?

If the confidence is below "verified", tell the user which additional evidence would raise it. Example: "If you can confirm what the web UI does for this action, I can raise the confidence to 'verified'."

## Step 9 — File on GitHub (optional)

After the user confirms the report, offer to file it as a GitHub issue.

### 9a — Resolve the destination repo first

Use the routing decision from Step 5.5c:

- **MCP repo** → go to 9b and file in `UNCTAD-eRegistrations/MCP_eRegistrations`.
- **Backend repo** → do **not** use the MCP repo. Ask the user:

  > This report belongs in the backend repository for {SERVER}, not the MCP repo. Which repo is it (for example `UNCTAD-eRegistrations/<name>`)? I can file it there, or save the report locally if you prefer to file it yourself.

  If the user confirms a backend repo, use it in the `gh issue create --repo` call. If the user does not know the repo, save the report and stop. A GitHub issue in the wrong repo is worse than no GitHub issue.

- **Consumer repo** → do the same. Ask for the repo. File there, or save the report locally.

Never select the MCP repo automatically as a fallback.

### 9b — Hard gate: do NOT offer to file if any of these is true

- The confidence is below **"likely"**.
- A claim in the "Expected Behavior" section has the type **"Assumption"** in the claim classification table.
- The report is a **feature request** (category: "Missing capability"), AND one of these is true:
    - The "Requested Outcome" cites **no** backend endpoint, field or capability that already exists or that is in active backend development.
    - The "Filing Destination" is the MCP repo, but the claim classification table does NOT cite the necessary backend capability as **Hard** evidence.
    - The "Requested Outcome" is a preference ("would be nice", "should consider", "ideally"), not an observable behavior that the maintainer can verify.
- The **Scope hygiene** confidence dimension is below 90%.
- The **Requested Outcome names more than one observable behavior change** (Step 5.5e). The exception: the user explicitly chose to keep the changes together, and the report states the reason.
- The **file list has more than 10 files** (Step 5.5f). The exception: the report is decomposed into slices, or filed as a design GitHub issue with `auto:skip`.
- The destination repo is not resolved, or the target repo is not the one that the routing decision selected.
- The request is out of scope (Step 5.5d). The exception: the user insists. Then file it only as 5.5d says, with the `auto:skip` label and the out-of-scope first line.

If a gate fails, tell the user exactly what blocks the filing and which evidence would unblock it:

> I can't file this on GitHub yet. The expected behavior comes only from your description, with no UI or doc confirmation. If you can confirm what the web UI does for this action, I can upgrade the claim and file it.

### Filing

1. **Check the prerequisites:**
   ```
   gh auth status
   ```
   If you are not authenticated, tell the user to run `! gh auth login`, and stop.

2. **Map the labels** from the report:

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
   | Out of scope (Step 5.5d) | `auto:skip` |
   | Design GitHub issue for a change that does not decompose (Step 5.5f) | `auto:skip` |
   | Epic parent (Step 5.5f) | `auto:split-parent` |
   | Slice 1 (Step 5.5f) | `auto:split-child`, `auto:split-depth:1` |
   | Each later slice (Step 5.5f) | `auto:split-child`, `auto:split-depth:1`, `auto:split-blocked` |

3. **Ask the user for confirmation** before you file:

   > Ready to file on **UNCTAD-eRegistrations/MCP_eRegistrations**:
   > - **Title:** <title>
   > - **Labels:** <labels>
   >
   > File it?

4. **Create the GitHub issue** only after the user approves explicitly. Use the repo from 9a, not a fixed default:
   ```
   gh issue create --repo <destination-repo-from-9a> \
     --title "<title>" \
     --body-file ~/Desktop/mcp-issue-reports/<filename>.md \
     --label "<label1>,<label2>"
   ```

5. **Show the issue URL** to the user.

If a label does not exist in the repo, omit it. Do not let the call fail. Use `--label` only for labels that exist.

**Exception: never omit a split label from an epic or a slice on the MCP repo.** If one of those labels does not exist there, do not file any part of the epic. File the change as one design GitHub issue with `auto:skip` instead.

**Exception: never omit `auto:skip` from an out-of-scope GitHub issue on the MCP repo.** If that label does not exist there, do not file. Save the report, and tell the user to send the request to the person named in Step 5.5d. On a repo that the bot does not watch, use `auto:skip` only if the label exists.

## Guidelines

- **Be patient with non-technical users.** Do not ask them for API endpoints or HTTP methods. Find those yourself from the tool name and the context.
- **Do not guess.** If you do not know what the expected behavior is, say so in the report and mark it for investigation.
- **Do not trust your own memory.** Read the actual tool responses again. Do not paraphrase them. AI agents, you included, misread data more often than you expect.
- **Prefer "needs verification" to a confident but wrong claim.** A report that says "I'm not sure about the expected behavior" is more useful than a report that states a wrong expectation with confidence.
- **Severity guide:**
  - **critical:** data loss or corruption. The tool destroys or overwrites data.
  - **high:** the tool gives wrong results silently. The user may not notice.
  - **medium:** the tool fails with an error, but no data is damaged.
  - **low:** a cosmetic problem, a format problem or a small inconvenience.
- **Keep the report short.** Maintainers skim. Put the important information first.
- **A feature request is not a bug.** If the tool works as designed but the user wants a different behavior, classify it as a feature request (category: "Missing capability", label: `enhancement`). You can file a feature request, but it needs *evidence that the destination repo can implement the addition* (see Step 9b). A feature request that cannot cite a backend capability or a concrete observable outcome is noise, whether it is a bug or a feature.
