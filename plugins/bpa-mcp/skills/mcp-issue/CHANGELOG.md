# mcp-issue changelog

Newest first. The skill version and date are in the `metadata` block of `SKILL.md`.

## 3.9.0 (2026-10-18)

Rewrite in Simplified Technical English (ASD-STE100, Strict mode for agent instructions). No rule, gate, threshold or label changes. New Terms table: problem (what went wrong), report (the markdown file), GitHub issue (what the skill files), maintainer (the person who owns the destination repo). The word 'ticket' is gone, and 'issue' alone always means a GitHub issue. Long sentences, semicolons and em-dash run-ons are split. The report template output and the trigger phrases are unchanged. The changelog moves from the SKILL.md frontmatter to this file, because the frontmatter loads each time the skill triggers and the agent does not use the history.

## 3.8.0 (2026-10-18)

Added Step 5.5f — Size. The skill lists the files that the Requested Outcome must change. Above 10 files it decomposes the change into at most 6 ordered slices of 10 files or fewer, and files them as an epic in the bot's own split protocol (auto:split-parent, auto:split-child, auto:split-depth:1, auto:split-blocked, manifest comment). The bot's split-chainer then runs the slices in order. A change that does not decompose goes to one design ticket with auto:skip. Reason: the bot's size gate counts files but its splitter divides tasks, so a cross-cutting ticket stalls for days (MCP #481: estimated at 34 files, split twice, the last child still changed 34 files). The scope checklist moves from 5.5f to 5.5g and gains a size row. New Step 9b gate and split-label rows in the label map.

## 3.7.0 (2026-10-17)

Added Step 5.5d — Out of scope. A request that no file change can deliver (repo access, a question, an operations task) gets no ticket: the skill tells the user why and where the request goes instead. If the user insists, the skill files the issue with the auto:skip label in the same gh call, plus a first body line that names the person who must act. Reason: the MCP repo's automation bot treats every issue as a code change. On MCP #834 it closed an access request as 'Shipped' after it merged a tests-only PR, and no person saw the request. New 5.5f checklist row, a Step 9b gate, and an auto:skip row in the label map that is never omitted.

## 3.6.0 (2026-07-31)

Added Step 5.5e — Atomicity. One ticket, one observable behavior change: count the distinct observable changes in Requested Outcome and offer to file N linked tickets when there is more than one. Deliberately a scope-SHAPE rule, not a length rule — measured evidence shows ticket length does not predict how much work a ticket becomes (of six oversized plans on record the smallest originating ticket was 60% below median length, and one was already a split-off child). New Atomicity confidence dimension, a Step 9b blocking condition, a Step 5.5f checklist row, and an explicit note in the Requested Outcome template. Subsumes the weaker 'conflating two issues' line in Step 6, which asked about merged bugs rather than merged asks.

## 3.5.0 (2026-05-10)

Feature requests are now filable when they pass the same evidence bar as bugs. Replaced the blanket 'no feature requests' gate in Step 9b with three evidence-specific sub-conditions: cited backend capability, Hard-typed evidence, and observable-behavior phrasing. Resolves the internal contradiction between the 'Missing capability' category (Step 3) and the old gate (Step 9b). TRIGGER description and Guidelines updated to match. Per-server wrapper command descriptions broadened from 'issue or unexpected behavior' to 'issue or feature request'.

## 3.4.1 (2026-04-14)

Clarified consumer-project routing — consumers (e.g. SmartRules / SR) may integrate with eRegistrations directly via REST (not via MCP). The earlier wording 'a consumer project that calls the MCP' wrongly excluded SR, which is the actual origin of #58/#68/#69. Added the SR alias everywhere, listed SR's concrete internal surfaces (procedures-api, gdb-sync.js, hash files) as examples.

## 3.4.0 (2026-04-14)

Added the 'Production repositories (routing reference)' table listing the exact GitHub repo names under `UNCTAD-eRegistrations` for MCP, the BPA/DS/GDB/Keycloak backends, and consumer projects (SmartRules). Step 5.5c now references these by exact name instead of asking the user to recall them. The rule 'do not invent a repo name; verify with `gh repo view` and do not fall back to the MCP repo' is explicit.

## 3.3.0 (2026-04-14)

Step 5.5c reframed as a ROUTING decision, not a phrasing rule. Issues whose fix lives in the backend (GDB/BPA/DS/Keycloak) must be filed in that backend's repository, not the MCP repo. MCP-repo tickets are reserved for MCP-tool-layer bugs: wrong API call, response transformation, validation, auth handling, or exposing a backend capability that already exists. Backend source citations remain welcome as EVIDENCE in whichever repo the ticket lands in — the distinction is evidence (allowed) vs. prescription in the wrong repo (not allowed). Step 9 now branches by filing destination.

## 3.2.0 (2026-04-14)

Added Step 5.5 — Scope & Sanitization gate. Reports must not cite local filesystem paths or couple to out-of-scope caller projects (e.g. SmartRules/procedures-api). New confidence dimension 'Scope hygiene'.
