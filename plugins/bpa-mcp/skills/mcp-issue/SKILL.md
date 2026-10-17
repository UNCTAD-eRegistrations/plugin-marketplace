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
  feature". Also triggers when the user asks to open any issue on the MCP repo, including a
  request that needs no code change (repo access, a question, an operations task). The skill
  declines that request, or files it with the auto:skip label if the user insists.
  DO NOT TRIGGER when: the error is clearly a user input mistake (wrong params, wrong tool),
  auth is expired (suggest re-login instead), or the user is asking about MCP server
  development/code (not tool usage).
license: UNCTAD-Internal
compatibility: Works with or without an active MCP server connection.
allowed-tools: Read, Write, Grep, Glob, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), mcp__BPA__*, mcp__BPA-local-dev__*, mcp__DS__*, mcp__GDB__*, mcp__Keycloak__*
metadata:
  version: "3.8.0"
  version-date: "2026-10-18"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "3.8.0 (2026-10-18): Added Step 5.5f — Size. The skill lists the files that the Requested Outcome must change. Above 10 files it decomposes the change into at most 6 ordered slices of 10 files or fewer, and files them as an epic in the bot's own split protocol (auto:split-parent, auto:split-child, auto:split-depth:1, auto:split-blocked, manifest comment). The bot's split-chainer then runs the slices in order. A change that does not decompose goes to one design ticket with auto:skip. Reason: the bot's size gate counts files but its splitter divides tasks, so a cross-cutting ticket stalls for days (MCP #481: estimated at 34 files, split twice, the last child still changed 34 files). The scope checklist moves from 5.5f to 5.5g and gains a size row. New Step 9b gate and split-label rows in the label map."
    - "3.7.0 (2026-10-17): Added Step 5.5d — Out of scope. A request that no file change can deliver (repo access, a question, an operations task) gets no ticket: the skill tells the user why and where the request goes instead. If the user insists, the skill files the issue with the auto:skip label in the same gh call, plus a first body line that names the person who must act. Reason: the MCP repo's automation bot treats every issue as a code change. On MCP #834 it closed an access request as 'Shipped' after it merged a tests-only PR, and no person saw the request. New 5.5f checklist row, a Step 9b gate, and an auto:skip row in the label map that is never omitted."
    - "3.6.0 (2026-07-31): Added Step 5.5e — Atomicity. One ticket, one observable behavior change: count the distinct observable changes in Requested Outcome and offer to file N linked tickets when there is more than one. Deliberately a scope-SHAPE rule, not a length rule — measured evidence shows ticket length does not predict how much work a ticket becomes (of six oversized plans on record the smallest originating ticket was 60% below median length, and one was already a split-off child). New Atomicity confidence dimension, a Step 9b blocking condition, a Step 5.5f checklist row, and an explicit note in the Requested Outcome template. Subsumes the weaker 'conflating two issues' line in Step 6, which asked about merged bugs rather than merged asks."
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

### 5.5d — Out of scope: no file change can deliver the request

Some requests do not ask for a change to any file in any repository. Examples:

| Request | Why no file change delivers it | Where the request goes instead |
|---|---|---|
| "Give @user read access to repo X." | Repo access is a GitHub org or repo setting. | A maintainer or an org admin, directly. |
| "How do I configure tool Y?" | It is a question. Nothing is broken. | Answer it in this session, or ask the maintainers in chat. |
| "Deploy, restart or upgrade instance Z." | It is an operations task on a server. | The team that operates instance Z. |
| "Create an account, reset a password or add a role on instance Z." | It is an admin action in a live system. | The instance admin. |

**Test:** name one file in the destination repo that must change to deliver the Requested Outcome. If you cannot name one, the request is out of scope.

**Why this step exists:** an automation bot triages every new issue on the MCP repo. It tries to deliver each issue as a code change. For an out-of-scope request, the bot writes a change that does nothing, merges it, and closes the issue as "Shipped". No person sees the request. This occurred on MCP issue #834 (2026-10-17): the bot closed an access request after it merged a PR that only added tests.

**If all of the request is out of scope:** do not draft a ticket. Tell the user:

> This request does not need a change to any repository file: {reason}. A GitHub issue is the wrong channel for it. The automation bot would try to deliver it as a code change and close it, and no person would act on it. Instead: {where the request goes}.

**If the user still wants an issue:** file it only with the `auto:skip` label. The bot does not triage an issue that has `auto:skip`, and it does not pick that issue up. Put this line first in the issue body:

> **Out of scope for automation — no code change requested.** A person must act: {who, and the action}.

Set the label in the same `gh issue create` call that creates the issue. Do not add the label after the issue exists: the bot can triage the issue between the two calls. Skip Steps 6–7 for this issue. The body is the out-of-scope line plus the user's request in their words.

**If only part of the request is out of scope:** apply 5.5e. File the in-scope part as a normal ticket. Use the rules above for the out-of-scope part.

### 5.5e — Atomicity: one ticket, one observable behavior change

A ticket that asks for several things at once cannot be reviewed, estimated, or shipped as one unit. It also loses the reporter's leverage: a maintainer who disagrees with *one* of the three asks has to reject or renegotiate the whole ticket.

**This is a scope-shape rule, not a length rule.** Do not gate on how long the report is. Short tickets are routinely the broadest ones — a single sentence can name a change that touches thirty files, while a long report is often long because it is thoroughly *evidenced* about one narrow thing. Length tells you nothing; the count of requested behavior changes tells you a lot.

**How to count.** Read only the **Requested Outcome** section and count the distinct *observable* changes — each one a thing a user or caller could see happen differently afterwards. Ignore the supporting narrative; evidence, reproduction, and analysis do not count.

| Requested Outcome | Count | Why |
|---|---|---|
| "`service_publish` should return a publish id instead of an empty body." | 1 | One observable change. **File it.** |
| "Hold the page while writing, **and** refuse the write when a human holds it." | 2 | Two behaviors, independently shippable and independently arguable. **Split.** |
| "Expose `created_at` on the read tools, **and** add a `--since` filter, **and** fix the timezone." | 3 | Three. **Split.** |
| "Return the audit id, so callers can correlate the write with the audit log." | 1 | The clause after "so" is *motivation*, not a second change. **File it.** |

Two traps in counting:

- **"and" is not the signal — a second verifiable outcome is.** "Validate the payload and return 400" is one change described in two clauses. "Validate the payload and add a retry" is two.
- **A conjunction hidden in the title still counts.** Read the title as part of the Requested Outcome.

**If the count is > 1:** do not file one ticket. Tell the user:

> This report asks for {N} separate changes: {list them}. Filed as one ticket they can't be reviewed or shipped independently — and if the maintainer disagrees with one, the others stall with it. I'd file {N} linked tickets instead, each with the evidence that belongs to it. Want me to split it that way? (Say "file as one" if they genuinely must ship together — e.g. the change is meaningless in halves.)

If the user says they must ship together, file one ticket and say so explicitly in the Requested Outcome: *"These {N} changes are inseparable because …"*. A stated reason is reviewable; an unstated merge is not.

**What this does and does not buy you.** It makes tickets reviewable and independently shippable. It does **not** guarantee the resulting work is small: a single-behavior ticket can still require a large change, and measured evidence says so plainly — of six oversized plans on record, the *smallest* originating ticket was 60% below the median ticket length, and one was itself already a split-off child of an earlier split. Size is decided by how much code the change touches, which the reporter often cannot see. Split for reviewability here; Step 5.5f handles size.

This subsumes the weaker "Am I conflating two different issues into one?" line in Step 6's hallucination table — that one asks whether you merged two *bugs*; this one asks whether you merged two *asks*, which is the more common failure.

### 5.5f — Size: decompose a big change into ordered issues

The bot cannot deliver a big change in one PR. Its size gate counts the files that a change touches. On the MCP repo the gate is 25 files, and an early check runs during the bot's spec phase. When a ticket is over the gate, the bot splits it by task. A task split often does not lower the file count, because the tasks change the same files. The ticket then stalls for days. Example: the bot estimated MCP #481 at 34 files and split it twice. The last child still changed 34 files.

You can see the files before the bot does. Decompose the change at filing time.

**1. List the files.** List each file that the Requested Outcome must change. Use the source tree (Step 4c). If you cannot read the source, estimate from the tools and packages that the request names. Typical sizes on the MCP repo:

| Change | Typical files |
|---|---|
| Fix in one existing tool | 2: the tool module and its test |
| New read tool in an existing module | 3: the module, the registration, the test |
| New write tool | 5: the module, `tools/__init__.py`, `server.py`, `rollback/manager.py`, the test |
| One rule for every write tool, or for every package | 1 per module plus tests, often more than 20 |

**2. If the list has 10 files or fewer,** file one ticket. Go to 5.5g. The limit is 10, not 25, because a filing-time list usually misses docs and tests that the bot must also change.

**3. If the list has more than 10 files,** decompose the change into slices. Each slice must obey these rules:

- The slice changes 10 files or fewer.
- The slice delivers one observable behavior change (5.5e), and a maintainer can verify it alone.
- The slice needs only the slices before it. Put shared code first: a helper or a client method that later slices use goes in slice 1.
- Two slices can change the same registration file, for example `server.py`. If most slices need most of the same files, the change does not decompose. Go to step 5.
- Make 6 slices or fewer. If the change needs more than 6, go to step 5.

**4. File the slices as an epic.** Use the bot's split protocol. The bot then runs the slices in order without help.

1. Create the parent issue with the label `auto:split-parent`. The body states the full problem and lists the slices. The bot does not triage or pick up a parent.
2. Create slice 1 with the labels `auto:split-child,auto:split-depth:1`.
3. Create each later slice with the labels `auto:split-child,auto:split-depth:1,auto:split-blocked`. The bot does not work on a blocked slice.
4. Post this comment on the parent. Write the slice numbers in order: `<!-- autopilot:split children=#A,#B,#C depth=1 -->`

Set the labels in each `gh issue create` call, not after it. Without its labels, a later slice can get triaged before its turn.

The bot works on slice 1 first. When a slice closes, the bot removes `auto:split-blocked` from the next slice. When all slices are closed, the bot closes the parent. If an estimate is wrong, `auto:split-depth:1` lets the bot split one slice once more.

Keep each slice body short. Write the slice's tasks, its files, and the line `Part {N} of #{parent}`. Do not copy the full parent text into each slice. Put this line last: *"Before you start, compare each task with `main`. Remove each task that an earlier slice already delivered."* A blocked slice waits while earlier slices change `main`.

**5. If the change does not decompose,** file one design ticket with the label `auto:skip`. The body states the problem, the file list, and why the change does not decompose. A person plans the slices, then files them with step 4.

Show the user the slice plan before you file anything (Step 9, item 3).

### 5.5g — Scope checklist (must all pass before Step 6)

Run through this list explicitly. Answer each one:

- [ ] **At least one file in the destination repo must change to deliver the Requested Outcome** (5.5d). If no file must change, use the out-of-scope path in 5.5d.
- [ ] **The file list has 10 files or fewer** (5.5f). If not: the change is decomposed into an epic of slices, or filed as one design ticket with `auto:skip`.
- [ ] **Requested Outcome names exactly ONE observable behavior change** (5.5e) — or the user explicitly chose to keep them together and the reason is written into the ticket.
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
| Atomicity | Does the Requested Outcome name exactly ONE observable behavior change? (Step 5.5e) |

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
| Atomicity                     |       60%  | Outcome asks for a new field AND a new filter — 2 changes        |
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

<ONE observable behavior change (Step 5.5e). If several were deliberately kept together, say so here and state why they are inseparable.

Describe the observable behavior that should change, phrased for the chosen destination:

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
- The **Requested Outcome names more than one observable behavior change** (Step 5.5e) and the user has not explicitly chosen to keep them together with a stated reason
- The **file list has more than 10 files** (Step 5.5f) and the report is not decomposed into slices or filed as a design ticket with `auto:skip`
- The filing destination is unresolved, or the target repo is not the one the routing decision selected
- The request is out of scope (Step 5.5d). Exception: the user insists. Then file it only as 5.5d says, with the `auto:skip` label and the out-of-scope first line.

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
   | Out of scope (Step 5.5d) | `auto:skip` |
   | Design ticket for a change that does not decompose (Step 5.5f) | `auto:skip` |
   | Epic parent (Step 5.5f) | `auto:split-parent` |
   | Slice 1 (Step 5.5f) | `auto:split-child`, `auto:split-depth:1` |
   | Each later slice (Step 5.5f) | `auto:split-child`, `auto:split-depth:1`, `auto:split-blocked` |

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

**Exception: never omit a split label from an epic or a slice on the MCP repo.** If one of those labels does not exist there, do not file any part of the epic. File the change as one design ticket with `auto:skip` instead.

**Exception: never omit `auto:skip` from an out-of-scope issue on the MCP repo.** If that label does not exist there, do not file. Save the report and tell the user to send the request to the person named in Step 5.5d. On a repo that the bot does not watch, use `auto:skip` only if the label exists.

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
