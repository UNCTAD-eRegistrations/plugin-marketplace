---
name: ereg-issue
effort: medium
description: >
  Report an eRegistrations runtime/deployment issue — standardized and
  pre-qualified into a verified qualified-ticket (symptom, instance, version, IDs,
  candidate repo/version, claims) ready for the maintainer/autopilot triage.
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
  version: "0.2.1"
  version-date: "2026-06-25"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "0.2.1 (2026-06-25): lead description with 'Report' (intent verb) for triggering + mcp-issue parity; pre-qualification kept as the differentiator."
    - "0.2.0 (2026-06-24): full intake/derive/ground/qualify/emit procedure."
    - "0.1.0 (2026-06-24): initial scaffold — packaging only; body added in Task 4."
---

# eRegistrations Issue Reporting (ereg-issue)

Turn a vague human report into a verified, pre-qualified `qualified-ticket`.
You PRE-QUALIFY (candidate repo/version + red-herrings to disprove); you do NOT
diagnose, fix, or deploy — that is the maintainer's job.

## Step 1 — Capture the hard floor (BLOCKS until present)
Collect, asking one question at a time only for what's missing:
- **symptom** — plain-language, user-visible ("file never reaches the desk").
- **instance** — host or URL (e.g. jamaica).
- **url** — the exact page/endpoint where it happened.
Do not proceed past this step without all three.

## Step 2 — Auto-derive context (fill silently; flag any gap in `fleet.source_silent`)
- **version/stack/orchestration** — probe the instance origin (`/status`, `ls /usr/*.jar`). If you cannot reach the origin, record the gap; never guess.
- **IDs** — parse the URL (`ds_url_parse`) and resolve `service_id` / `file_id` / `process_instance_id` / `role` via `file_get` / `service_get`.
- **error + status** — if the symptom is reproducible NON-destructively via an MCP read, capture the real response. NEVER reproduce a destructive/write path here.
- Ask the human only for `expected` vs `actual` and `scope` (one file vs many; condition).

## Step 3 — Light grounding (read-only; do NOT diagnose)
- Confirm instance reachable (`ds_health`/origin), IDs resolve, capture any live error, one Graylog peek for the signature.
- HARD RULE: log silence ≠ healthy. Many real bugs log nothing (200-PUT wipe, swallowed publish FK, dropped GDB column, unindexed DataWeave error). Record what you observed and which source was silent — never assert health.

## Step 4 — Pre-qualify (routing table + gotcha pre-check)
- Read `routing-table.json`. Match the symptom (keywords + version_hint) to the best rule(s). Populate `qualification.candidate_repos`, `version_branch`, `first_evidence_source`, `known_red_herrings`, `memory_ref`. If multiple rules match, list all candidate_repos and say so.
- These are CANDIDATES, not a verdict. Always carry the rule's `known_red_herrings` forward so the maintainer disproves them.
- Gotcha pre-check: if the symptom matches a known platform "lie" in the eregistrations-ai-process gotcha library (G1–G48), record it in `qualification.gotcha_hits` and set `closing_state` to `WONT_FIX` or `NOT_A_BUG` — do not file a defect ticket.

## Step 5 — Classify claims (ISC + constraint kind)
For each factual statement in the report, record `{claim, claim_type, kind, evidence, needs_live_verification}`:
- `claim_type` ∈ code-fact | runtime-observation | environment-mapping | quantitative-estimate | future-prescription.
- `kind` ∈ Hard | Soft | Assumption (Hard requires a file:line citation).
- Set `needs_live_verification: true` for runtime-observation / environment-mapping claims — autopilot's static-code verifier CANNOT settle these.

## Step 6 — Assign the rubric (autopilot enums — exact)
- `severity` ∈ critical|high|medium|low|info (critical = data loss/auth bypass/prod outage/irreversible).
- `scale` ∈ Small|Medium|Large|Architectural; `kind` ∈ bug|feature|refactor|design|docs|infra|unknown.
- `affected_components` = repo-relative paths surfaced by the routing rule + claims.

## Step 7 — Emit artifacts
- Resolve the issues root: if the current working tree contains an `issues/CLAUDE.md`, write under `issues/<slug>/`; otherwise `~/Desktop/ereg-issue-reports/<slug>/`. Create it with `mkdir -p`.
- Write `qualified-ticket.json` (conform to `qualified-ticket.schema.json`).
- Write `NOTES.md` seeded with: `# <symptom>` then `## Context` (instance, version, IDs, reporter), `## Repro`, and stub headings `## Findings`, `## Hypotheses-refuted`, `## Fix-options`, `## Verification`, `## Status` for the maintainer.
- Slug: `ERE-1234-<short>` if a ticket id exists, else `YYYY-MM-DD-<short>`.

## Step 8 — Self-review + validate before filing (HARD GATE)
- Run the validator: `python3 <skill-dir>/tests/validate_ticket.py <issues-root>/<slug>/qualified-ticket.json`. It MUST print `VALID`. If not, fix the ticket and re-run.
- Scan for unfilled Assumptions presented as fact; downgrade unverified claims.
- If `closing_state` is set (gotcha hit), STOP — report the known-lie verdict; do not file.

## Step 9 — File the GitHub issue (optional, explicit)
- Confirm `gh auth status`. Render the ticket as an issue body and file to the candidate repo:
  `gh issue create --repo <candidate-repo> --title "<symptom>" --body-file <issues-root>/<slug>/issue-body.md --label ereg-issue`
- This is the same substrate the autopilot watcher consumes.
