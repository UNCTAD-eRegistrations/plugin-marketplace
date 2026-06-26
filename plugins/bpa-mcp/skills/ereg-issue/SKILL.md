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

## Step 4 — Pre-qualify (routing table + scoring + version gate + gotcha pre-check)
- Read `routing-table.json`. **Score every rule** by the count of DISTINCT keywords it matches against the symptom + url + captured error text. Weight domain-specific discriminators (e.g. `ereg_process`, `act_ru_execution`, `DataWeave`, `realm_smtp_config`, `validate_catalogs`, `silentCheckSsoRedirectUri`, `__ro__`) HIGHER than base-rate tokens (`file`, `500`, `service`, `token`). Record the winning rule's score as `qualification.match_score`.
- **Confidence** (`qualification.confidence` ∈ high|medium|low): `high` when one rule clearly leads on at least one domain-specific token; `medium` when the lead comes only from generic tokens; `low` when no domain-specific token matched OR ≥2 rules tie on score. When confidence is `low` or rules tie, list ALL candidate_repos and state explicitly that confidence is low — NEVER present a single repo as settled.
- Populate `qualification.candidate_repos`, `version_branch`, `first_evidence_source`, `also_check_and_disprove`, `memory_ref` from the top-scoring rule(s).
- **Version hard gate** (use the INSTANCE version derived in Step 2's fleet matrix, NOT the rule's `version_hint`): if the matched rule's `version_hint` does not equal the instance version, do NOT copy the rule's `version_branch`/`read_via` verbatim — emit the branch matching the INSTANCE instead (e.g. instance=2.17 → `version_branch: "release/2.17"`, `read_via: "git show release/2.17:<path>"`) and set `qualification.version_mismatch: true`. The `<instance_version_branch>` placeholder in a rule's `read_via` MUST be replaced with the instance's actual release branch (e.g. `2.17`). When the hint matches the instance, set `version_mismatch: false`.
- These are CANDIDATES, not a verdict. Carry each `also_check_and_disprove` entry forward and have the maintainer actively confirm it ISN'T the cause THIS time before ruling it out — a prior incident's red herring can be the real fault in a new one.
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
- Write `issue-body.md` — the GitHub issue body Step 9 files. It is the human-readable report Markdown (symptom, instance/version, IDs, expected vs actual, scope, candidate repos + confidence, `also_check_and_disprove`, first-evidence source), FOLLOWED BY a machine-readable conformance block: a fenced block whose info string is EXACTLY `qualified-ticket`, containing the verbatim contents of `qualified-ticket.json`:

  ````
  ```qualified-ticket
  { ...the full qualified-ticket.json contents... }
  ```
  ````

  Autopilot parses this block (when present) to seed its claims/rubric directly; the prose above it stays human-first.
- Slug: `ERE-1234-<short>` if a ticket id exists, else `YYYY-MM-DD-<short>`.

## Step 8 — Self-review + validate before filing (HARD GATE)
- Run the validator: `python3 <skill-dir>/tests/validate_ticket.py <issues-root>/<slug>/qualified-ticket.json`. It MUST print `VALID`. If not, fix the ticket and re-run.
- Scan for unfilled Assumptions presented as fact; downgrade unverified claims.
- If `closing_state` is set (gotcha hit), STOP — report the known-lie verdict; do not file.

## Step 9 — File the GitHub issue (optional, explicit)
- Confirm `gh auth status`. File the `issue-body.md` written in Step 7 to the candidate repo:
  `gh issue create --repo <candidate-repo> --title "<symptom>" --body-file <issues-root>/<slug>/issue-body.md --label ereg-issue`
- This is the same substrate the autopilot watcher consumes. Autopilot parses the `qualified-ticket` fenced block when present (seeds its claims/rubric from the structured JSON), and falls back to re-extracting from the prose otherwise — so always keep the block intact in the filed body.
