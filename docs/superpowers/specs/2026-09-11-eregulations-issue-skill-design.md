# `eregulations-issue` — Design Spec

**Date:** 2026-09-11
**Status:** Revised after adversarial review (two independent reviewers), then re-aligned on PR 79 (`api-surfaces.md` read at the 7.4.2 tips); third review 2026-09-11 (**Appendix C**) moved the defect catalogue to a private overlay and added the disprove pass; revision D 2026-09-11 (**Appendix D**) restricted the skill to 7.x and made the overlay a runtime fetch from the private repository; branch recreated without the old history (D-8); API reference moved private and PR 79 replaced by #81 (D-9); pending implementation
**Plugin:** `eregulations` (bump 0.2.1 → 0.3.0)
**Skill:** `eregulations-issue`, version 0.1.0
**Command:** `/eregulations:issue`
**Sibling:** `bpa-mcp:ereg-issue` (eRegistrations). Same ticket substrate, different intake.

> **Revision note.** The first draft touched the host before evaluating
> `host_posture`, was only reachable from the router in the one lane where
> triage is least needed, put `host` and `posture` into the filed ticket, fed
> the version gate from an undefined source, and specified a probe that could
> not reach Surface C from one base URL. This revision reorders Steps 2–4,
> defines the gate's version source, enumerates what may leave the machine,
> and rewrites the probe contract. **Appendix A** lists every reviewer finding
> and where it is addressed or why it was rejected.
>
> **Re-alignment note (PR 79, 2026-09-11).** `api-surfaces.md` was re-read at
> the `main` tips: the 7.x branches of Public, Admin, SPA and Statistics were
> renamed to `main` on 2026-09-07, `dot-net8-roxana-user-rights` is retired
> (never a filing target), the Basic-auth gate ships on `main` with no default
> credential and exempts `/release.json`, `/Home/CustomCss` is on `main` since
> 7.4.0, and five B 7.x defects were fixed between 2026-09-05 and 2026-09-11.
> Every branch is now single, so `version_branch` is always hardcoded; the
> probe's `branch_hint` only ever says `retired-roxana-image`. **Appendix B**
> lists the changes.
>
> **Superseded in part (2026-09-11): the HTTP release stamps are gone.** A
> later change (`eRegulations-deploy` `feature/release-stamp-off-http`) removes
> `/release.json`, `/version.json` and the `Server: Kestrel` header from the
> 7.x images and adds a gate-exempt `/health`. The clause above that the gate
> "exempts `/release.json`", and the reasoning that a roxana image is "the only
> 7.x build without `/release.json`", no longer hold. `/health` is now the
> gate-exempt 7.x signal and `/release.json` a transitional fallback for images
> built before the change. **Appendix E** carries the re-grounding.

> This repository is public. Nothing in this spec, the skill, its routing table,
> its samples or its tests may carry a host address, a credential, a VPN name,
> a real instance slug, a security posture, **or the description of an open
> defect** (symptom keywords, evidence paths, disprove text, security flags).
> Fleet facts come from the fleet overlay at runtime
> (`ereg-router/references/resolution.md`); defect facts come from the **defect
> overlay**, fetched at runtime from the private repository
> `UNCTAD-eRegistrations/eregulations-knowledge-base` (see *Where the rules live*). Samples, the
> fixture overlay and its corpus use synthetic slugs (`alpha`, `bravo`, …) and
> synthetic rules (`fx-…`).

## Purpose

Turn a vague human report about a **7.x** eRegulations instance — or a request
for a new 7.x capability — into a verified, pre-qualified `qualified-ticket`
filed as a GitHub issue on the right `UNCTAD-eRegistrations/eRegulations-*`
repository, ready for a maintainer or an autopilot to triage.

**7.x only (D-1).** An instance that is not on 7.x is refused, not ticketed:
the policy since 2026-09-03 is to migrate legacy instances, never to fix them.
The skill still tells the reporter what it found and writes a local note, but
it files nothing and offers no override.

The skill **pre-qualifies**: it names candidate repositories, the branch to read,
the first evidence source and the things to disprove. It does **not** diagnose,
fix, deploy or write to any instance. It never sends anything but anonymous
`GET` requests to a host, and only after the host gate has passed.

It is the `bugfix` dispatch target that `ereg-router` Step 5 currently lists as
"no dedicated skill yet".

## Decisions taken (conversation, 2026-09-11)

| Decision | Choice | Alternatives rejected |
| --- | --- | --- |
| Filing destination | GitHub issue on the candidate repo; **plus** a Jira comment only when the report named an `ERN-…` key | GitHub only; Jira only |
| Scope | Bugs **and** feature requests | Bugs only |
| Architecture | Thin skill on top of `ereg-router` scripts | Fork of `ereg-issue`; generalised multi-platform `ereg-issue` |
| Ticket schema | `qualified-ticket` 1.1 = `ereg-issue` 1.0 + additive fields; every 1.0 requirement kept | Relaxing `instance.name` for features (breaks the 1.0 consumer) |
| Gate ordering | `gates.py` runs right after resolution; no host contact before `host_posture` passes | Probe first, gate later |
| Defect catalogue location (2026-09-11, C-1, revised D-5) | Private repository `UNCTAD-eRegistrations/eregulations-knowledge-base`, fetched at runtime with the operator's `gh` credential and cached; the public table keeps the three gotchas and `surface-defaults.json` | rules committed to the public repo; moving the whole plugin to a private marketplace; a hand-copied local file (kept only as a manual override) |
| Scope of lines (2026-09-11, D-1) | 7.x only; anything else is refused with no override | OUT-OF-SCOPE tickets with an audited override |
| Line authority (D-2) | A `200` from the application's health/stamp probe (`/health`, or `/release.json` on an image built before the change) is the application answering and decides the line; the overlay decides host and posture | "more restrictive of overlay and probe" (C-6's remedy rewrite is superseded) |
| Pre-filing check (C-5) | A read-only disprove pass by a fresh subagent between validate and file | The self-scan of Step 9 alone |

## What is reused, and from where

| Need | Reused from | Never re-implemented here |
| --- | --- | --- |
| instance → host / version / posture / unresolved / drift | `ereg-router/scripts/fleet_resolve.py` | version inference from a country or a repo name |
| gate verdicts | `ereg-router/scripts/gates.py`, `audit.py`; `branch_pair.py` for evidence only | any gate decided from prose |
| lane detection (`plan` / `build` / `execute`) | `ereg-router` Step 3, stated before acting | half-runs |
| probe table, checkout identification, known defects | `api-surfaces.md` §1, §3–§6, §8, in the private knowledge base (fetched with `gh api`) | endpoint facts from repo `CLAUDE.md`s |
| ticket conformance enums | `bpa-mcp/skills/ereg-issue/tests/validate_ticket.py` (copied to `scripts/`, extended) | a jsonschema dependency |
| defect rules and corpus | the defect overlay at runtime (`scripts/rules.py`: `gh api` fetch, cache, same missing/malformed semantics as `fleet_resolve.py`) | any defect description in a committed file |

`fleet_resolve.py`, `gates.py` and `audit.py` are addressed by path relative to
the plugin (`$PLUGIN/skills/ereg-router/scripts/…`). Every runnable block in
`SKILL.md` re-assigns `$PLUGIN`, as the router does, because shell state does
not persist between tool calls.

## Layout

```
plugins/eregulations/
  commands/issue.md                         # /eregulations:issue (new file)
  skills/eregulations-issue/
    SKILL.md
    routing-table.json                      # three gotcha rules only (fixed / config / retired: safe to publish)
    surface-defaults.json                   # surface → candidate repos (branch is always main), used when no rule matches
    fixtures/
      defects.sample.json                   # synthetic overlay: four fx-* rules + corpus, what CI loads
    qualified-ticket.schema.json            # 1.1
    samples/
      qualified-ticket.bug.example.json
      qualified-ticket.feature.example.json
    scripts/
      probe_surface.py                      # read-only HTTP probe → surface, line (7.x | not-7.x | unknown), branch_hint, release
      route.py                              # deterministic scoring over routing-table.json
      redact.py                             # evidence/log/URL redaction before anything is written
      rules.py                              # public table ∪ defect overlay: flag → env → gh fetch → cache → local file → not loaded
      gate_context.py                       # line rule (D-2), gate context builders
      validate_ticket.py                    # stdlib validator + CLI (prints VALID)
    tests/
      conftest.py                           # sibling scripts/ + ereg-router/scripts on sys.path
      test_issue_routing_table.py
      test_issue_route.py
      test_issue_probe_surface.py
      test_issue_redact.py
      test_issue_validate_ticket.py
      test_issue_gate_cases.py
```

Test basenames carry the `issue_` infix so a combined `pytest plugins/` run does
not collide with `bpa-mcp/skills/ereg-issue/tests/test_routing_table.py`.
Scripts are stdlib-only (`urllib`, `json`, `argparse`, `re`), run under plain
`python3`, and ship tests per `CLAUDE.md` "Bundled skill tests". The validator
lives in `scripts/` so pytest collects its tests from
`tests/test_issue_validate_ticket.py` — a `validate_ticket.py` under `tests/`
is never collected (default `python_files = test_*.py`).

## Procedure (what `SKILL.md` orchestrates)

Order is load-bearing: **resolve → gate → probe → ground → qualify → emit →
validate → disprove → file.** Nothing contacts a host before Step 3 says it
may, and nothing is filed for a host that is not on 7.x.

### Step 1 — Hard floor (blocks until present)

Ask one question at a time, only for what is missing.

- **Bug:** `symptom` (plain language, user-visible), `instance` slug, `url`
  (exact page or endpoint). The probe base URL is derived from `url`, never
  typed separately. **The query string is dropped** (`redact.strip_query`)
  before the URL is probed, stored or shown: a pasted URL can carry a
  credential in its query string, and it must be neither replayed nor filed (C-4). The slug ↔
  URL pairing is recorded as an `environment-mapping` claim with
  `needs_live_verification: true`.
- **Feature:** `desired_behaviour`, `surface` (B / C / SPA / deploy / monitor;
  Surface A has no 7.x and is refused), `instance` (the instance the reporter
  has in mind, or the documented sentinel `platform` when the request is
  platform-wide), and
  **one of**: a cited existing capability (endpoint, setting, UI element) or an
  observable behaviour the feature changes. Neither → `NEEDS-MORE-INFO`;
  nothing is filed.

Also captured for both: `expected` vs `actual`, `scope` (one procedure / one
instance / fleet-wide; condition), optional `jira_key` (`ERN-\d+` only).

### Step 2 — Resolve (bugs)

```bash
PLUGIN=<path-to>/plugins/eregulations
RUN=$(mktemp -d)   # per-run directory; every intermediate file lives here
python3 "$PLUGIN/skills/ereg-router/scripts/fleet_resolve.py" <slug> > "$RUN/resolve.json"
```

- Report every `drift` entry to the user, in chat. Never fill an `unresolved`
  field by inference.
- `known_instance: false` → offer the nearest `known_slugs`, ask, stop.
- When dispatched by the router, the router hands over `resolve.json` and
  `gates.json` paths and this step reads them instead of re-running.

Features skip Step 2; their gate context is built in Step 3 with `line: 7.x`
(the only line the skill serves).

### Step 3 — Gate (before any host contact)

Assemble the context from `resolve.json` (only `host`, `version`, `platform`,
`posture`, `version_major` — never `known_instance` / `known_slugs`) plus:

| Key | Value |
| --- | --- |
| `kind` | `bugfix` for a bug; `dev` for a feature |
| `secondary_kinds` | `["upgrade"]` when the report asks for the upgrade |
| `touches_admin_public`, `targets_admin_deploy` | **never set** by this skill — it builds and deploys nothing, so `branch_pair` and `media_mount` can only pass |
| `version_major` | see the version rule below |

```bash
python3 "$PLUGIN/skills/ereg-router/scripts/gates.py" < "$RUN/context.json" > "$RUN/gates.json"
```

**Act on `host_posture` immediately.** `block` (compromised or unresolved) →
report the gate, reason and remedy verbatim; **no probe, no grounding, no
filing**; the skill may still write a `NOTES.md` with what the reporter said,
nothing more. `warn` (degraded) → say so, continue read-only.

**Features:** the context has no `posture`, so `host_posture` blocks by design;
for a feature the skill reads **only** the `unsupported_version` decision and
says so in the ticket (`lane: plan`). A feature is always judged on `line: 7.x`;
a reporter asking for a legacy-line capability is refused at Step 1.

**Line rule (D-2), the one place it is defined.** Two sources say what line
a host is on: the operator overlay (`version`) and the probe. A `200` from
the application's health/stamp probe (`/health`, or `/release.json` on an
image built before the stamp removal) is the application itself answering, so
when the probe decides, its answer is the line. The overlay decides host and
posture, never the line against a probe that answered.

| Overlay | Probe | `version_major` sent to the gate | Outcome |
| --- | --- | --- | --- |
| 7 | 7.x | 7 | pass |
| 7 | not-7.x | **not 7** (the probe's reading) | `unsupported_version: block`, refused; the overlay is stale, say so |
| 5 | 7.x | **7** | pass; `version_mismatch: true`, drift reported: "the overlay records 5, the host answers 7.x: correct the overlay" |
| 5 | not-7.x or unknown | 5 | refused |
| 7 | unknown | 7 (the probe added no information) | pass on the overlay's word; `line: unknown` in the ticket with the `unresolved` reason |
| absent | any | absent | never reached for a bug: an unresolved host already blocks `host_posture` |

Because the probe runs after this step, `unsupported_version` is evaluated
**twice**: once here on the overlay value (to know whether the run may go on),
and again after Step 4 with the probe's reading. The second verdict is the one
that decides; a block there is terminal (D-1): no override, no `audit.py`
entry, no ticket. `fleet.overlay_version` and `line` are both kept.

### Step 4 — Probe and light grounding (read-only, only after Step 3)

```bash
python3 "$PLUGIN/skills/eregulations-issue/scripts/probe_surface.py" \
  --url "<base-url derived from the reporter's url, query string dropped>" [--api-url <admin-api base>] \
  [--timeout 5] > "$RUN/probe.json"
```

Contract of `probe_surface.py` (D-3: it answers one question, *is this host on
7.x, and which surface*; it no longer tells 4.x, 5.x and 6.x apart):

- **GET only, anonymous.** It never sends `Authorization`, a cookie, or a body,
  never follows a login redirect, and never calls `/api/tariffs/*` (which on
  `main` proxies to an external rate-limited API with the instance's key).
- **`/health` first — the new gate-exempt 7.x signal.** `200` JSON
  `{"status": "ok"}` → C 7.x (admin-api), `release: null`, done. `200` JSON
  `{"status": "up"}` → admin-web (its body since the deploy Task 9; never
  admin-api, never Public) → hop. `200` text
  `ok` → new Public **or** admin-web: fetch `/` and read `window.__env`;
  `apiUrl` present → admin-web → hop to that admin-api (`allow_hop`); absent →
  B 7.x `main`, `release: null`. A `401` carrying `WWW-Authenticate: Basic
  realm="eRegulations"` means the gate did **not** exempt `/health`, so this is
  not a new `main`; fall through to `/release.json` to tell an old `main` from
  a roxana image. `404`/other → fall through.
- **`/release.json` next — transitional, for images built before the stamp
  removal, still gate-exempt on those.** `200` with `track: admin-api-core` →
  C 7.x (old admin-api), `release` from the body; `200` with a version on a
  public host → B 7.x `main` (old image), `release` from the body;
  `{"release": …}` only → admin-web (hop). A `401` here **and** a `401` from
  `/health` at step 1 is the signature of a Public image built from the retired
  roxana branch, which ships neither endpoint so its gate intercepts both:
  `surface: B, line: 7.x, branch_hint: retired-roxana-image`, stop. If a Basic
  gate was seen on one endpoint but the other was merely unreachable (not a
  clean `404`/`401`), the gate still says B 7.x with `branch_hint: null` and an
  `unresolved` note (old-vs-roxana undecidable). The `release` (else `version`)
  value of a `200` `/release.json` is exposed as `release`; **`release` is
  `null` whenever only `/health` answered**, because the new images do not
  expose the release over HTTP.
- **Three hosts, not one.** Admin-api, admin-web (SPA nginx) and Public are
  separate hosts with no path prefix. When the base URL answers as admin-web
  (`/health` → text `ok` or JSON `{"status": "up"}` with a `window.__env.apiUrl`
  in the index, or an old `/release.json` → `{"release": …}` only), the script reads
  `window.__env.apiUrl` from the admin-web index (browser-reachable by design)
  and probes that second host for Surface C; `--api-url` overrides. Only when
  neither is reachable does it emit `surface: SPA`.
- **Not 7.x is one answer.** After neither `/health` nor `/release.json`
  answered `200` and no Basic gate appeared: swagger with `api/permission` →
  C 7.x (a health/stamp endpoint hidden by a proxy); swagger with `api/user`
  and no `api/permission` → C,
  `not-7.x`; a swagger or `/Country` answer shaped like ERegWebApi → A,
  `not-7.x`; `/api/isauthenticated` answering `200`/`401` without any 7.x
  signature → B, `not-7.x`. No `--procedure-id`, no `/Home/CustomCss`, no
  `usecontactpage`, no spelling probes: the skill does not need to know which
  legacy line it is refusing.
- **Undecidable stays undecided.** Nothing decisive → `line: "unknown"` with an
  `unresolved` list naming what did not answer. `unknown` is not `7.x`: the
  gate then runs on the overlay's word (D-2) and the ticket says the line was
  not confirmed.
- Output: `{"surface", "line" ∈ 7.x | not-7.x | unknown, "branch_hint",
  "release", "evidence": [{probe, status, conclusion}], "unresolved": []}`.
  Evidence bodies pass through `redact.py` before being written.

Overlay `version` vs probed `line` disagreement → a `drift` entry shown to the
human with the D-2 remedy; the ticket records `fleet.overlay_version` and
`line`, never the raw `drift` object.

Then, by lane, still read-only:

| Lane | Grounding allowed |
| --- | --- |
| `plan` | the probe above; reproduce the symptom with one anonymous GET on the reporter's URL; capture the real status and redacted body |
| `build` | plan + `git show <branch>:<path>` on the local checkouts named by the routing rule |
| `execute` | build + `docker logs <service>` on the resolved host, read-only, output redacted before it is stored |

**Hard rule kept from `ereg-issue`:** log silence ≠ healthy. Record what was
observed and which source was silent; never assert health.

### Step 5 — Pre-qualify

```bash
python3 "$PLUGIN/skills/eregulations-issue/scripts/route.py" \
  --probe "$RUN/probe.json" --text "<symptom + url + captured error>" > "$RUN/route.json"
```

`route.py` loads the public `routing-table.json` (three gotchas) **plus** the
defect overlay through `rules.py` (D-5), in this order: `--defects <path>`;
`EREG_DEFECTS`; a fresh read of `defects.json` from `UNCTAD-eRegistrations/eregulations-knowledge-base`
with `gh api … -H 'Accept: application/vnd.github.raw'` (10 s timeout), cached
as `~/.ereg/defects.cache.json` with the blob sha and the fetch time; the last
cache when the fetch fails; `~/.ereg/defects.local.json` as a manual
fallback; else **not loaded**, with the reason (`no gh`, `not authenticated`,
`no access`, `network`). Ids must be unique across public and overlay; a
malformed file raises naming its source. With nothing loaded it answers from
`surface-defaults.json` at `confidence: low`, sets `overlay_loaded: false`
and the ticket says so in `fleet.source_silent`; the ticket is still worth
filing. `overlay_ref` records where the rules came from (`blob sha`, `cache`,
`local`, `fixture`, `none`) so a maintainer knows which memory routed it.
It then filters rules by `surface` (every rule is 7.x) and scores each
remaining rule by distinct keywords matched; keywords listed in
`discriminators` count double. Output: `match_score`, `confidence` (`high`
when one rule leads on ≥1 discriminator; `medium` when the lead comes only
from generic tokens; `low` when nothing domain-specific matched or ≥2 rules
tie), and **all** tied `candidate_repos` when confidence is `low` — never a
single repo presented as settled.

Every routing target is on `main` (Public, Admin, SPA, deploy, Monitor since
2026-09-07), so `version_branch` is `main` on every rule and `read_via` never
carries a placeholder. The probe's `branch_hint` has one value,
`retired-roxana-image`: `route.py` then returns the gotcha rule
`b7-retired-roxana-image` (`closing_state_hint: WONT_FIX`, remedy "redeploy
from `channel/stable`; never patch the retired branch") as the sole winner,
whatever the symptom says. `version_mismatch` is "overlay version and probed
line disagree".

Second gate pass with the probe's line (Step 3 rule):

- `unsupported_version: block` → **refused** (D-1). The skill states what the
  probe saw, that the policy is migration, and where the migration wave is
  tracked; it writes `NOTES.md` only; no ticket, no override, no Jira.
- `pass` → `recommendation_hint: PROCEED`.
- **`branch_pair.py`** may run for evidence when the symptom is a build of Admin
  and Public together; its verdict becomes an `environment-mapping` claim,
  `kind: Hard` when the csproj reference was read. It is never a gate input here.

Gotchas: rules may carry `closing_state_hint` ∈ `NOT_A_BUG`,
`INTENTIONAL_DESIGN`, `WONT_FIX`, `FIXED`. Three families: the Basic-auth
pre-launch gate on Public 7.x (`BASIC_AUTH_ENABLED`) is configuration, not a
defect (`NOT_A_BUG`); the five B 7.x defects `api-surfaces.md` §8 marks
"fixed on `main` between 2026-09-05 and 2026-09-11 — do not re-report" are
`FIXED` rules whose remedy is "determine the running release with the operator
command `eregulations instance show <slug>` (the `/fleet` `running.releases`) —
it is no longer served over HTTP; if older than 7.4.2 redeploy from
`channel/stable`; if 7.4.2 or later and still reproducing, file it as a
regression with whatever release the operator can supply"; a retired roxana
image is `WONT_FIX` (redeploy, never patch). No rule's keywords contain a
credential pair; `test_issue_routing_table.py` checks the shape.

### Step 6 — Claims

Unchanged from `ereg-issue`: every factual statement becomes
`{claim, claim_type, kind, evidence, needs_live_verification}`. `Hard` requires
a `file:line` or a probe evidence entry. Runtime observations and environment
mappings set `needs_live_verification: true`.

### Step 7 — Rubric

`severity` / `scale` / `kind` / `affected_components` with the exact autopilot
enums. A rule may carry `security: true` in the overlay; a ticket routed to
such a rule defaults to `severity: high` and carries `security: true`. Which
rules are security-relevant is overlay content, not spec content (C-1).

### Step 8 — Emit

Issues root: `issues/<slug>/` if the working tree has `issues/CLAUDE.md`,
otherwise `~/Desktop/eregulations-issue-reports/<slug>/`. Slug:
`ERN-1234-<short>` when a Jira key exists, else `YYYY-MM-DD-<short>`.

Files: `qualified-ticket.json` (schema 1.1), `NOTES.md` (same headings as
`ereg-issue`), `issue-body.md` = human-first Markdown followed by the fenced
block whose info string is exactly `qualified-ticket`, containing the JSON
verbatim.

**What may leave the machine.** The ticket's `fleet` block is an allowlist:
`line`, `overlay_version`, `platform`, `source_silent`, `drift: true|false`
(a flag, not the entries). **Forbidden anywhere in the ticket, the issue body,
`NOTES.md` or the Jira comment:** `host`, `posture`, addresses, VPN names,
gate reasons that name a posture, raw `drift` entries, and unredacted log or
response bodies. `redact.py` runs over every evidence string and log excerpt
before it is written: IPv4/IPv6 literals, `Authorization`/`Cookie` headers,
connection strings, bearer/JWT-shaped tokens, e-mail addresses, and any value
of an env var whose name contains `PASSWORD`, `SECRET`, `KEY`, `TOKEN`.
`test_issue_redact.py` proves each pattern. The `instance.name` slug is
allowed because the target repositories are private (verified 2026-09-11) and
the slug is what the maintainer needs; the visibility check in Step 10 guards
the day that changes.

The human part always states: surface and line as **probed** (and the release),
the overlay version when it differs, the lane the evidence was gathered in,
candidate repos with confidence, `also_check_and_disprove`, first evidence
source, and which defect memory routed it (`overlay_ref`).

### Step 9 — Validate (hard gate)

```bash
python3 "$PLUGIN/skills/eregulations-issue/scripts/validate_ticket.py" <issues-root>/<slug>/qualified-ticket.json
```

Must print `VALID`. Then scan for Assumptions presented as facts and downgrade
them. Stop and report the verdict when `closing_state` ∈ `{NOT_A_BUG,
INTENTIONAL_DESIGN, WONT_FIX, FIXED}` (a gotcha hit).

### Step 9b — Disprove (read-only, before the filing question)

A fresh subagent (`Agent`, general-purpose, no write tools) receives the
validated ticket, the probe evidence and the rule's `also_check_and_disprove`
list, and must return `{"verdict": "stands" | "weakened" | "refuted",
"notes": [...]}`. It may read local checkouts and issue anonymous GETs under
the same rules as Step 4; it never contacts a host the gate blocked, and it
never writes. `refuted` → `recommendation_hint: NEEDS-MORE-INFO`, nothing is
filed, the notes go to `NOTES.md`. `weakened` → the named claims are
downgraded to `Assumption`, the notes are appended, filing may proceed.
`stands` → proceed. Verdict and notes are recorded under
`qualification.disprove`. This is the adversarial pass the skill was asked to
have (C-5); Step 9's self-scan is not it.

### Step 10 — File (explicit, opt-in)

1. `gh auth status` must succeed.
2. `gh repo view UNCTAD-eRegistrations/<candidate> --json visibility` must say
   `PRIVATE`. If a target is not `PRIVATE`, stop for any ticket (the body
   carries the instance slug) and ask; a `security: true` ticket is never
   filed there — point the user to GitHub private vulnerability reporting or
   a private channel, and leave the files on disk.
3. Labels are a precondition, not an assumption: `gh label create
   eregulations-issue --force` (and `security --force` when applicable) on the
   target repo. Verified 2026-09-11: none of the target repos has either label
   today, and `gh issue create --label` fails on a missing label. If label
   creation is refused (no write permission), file **without** labels and say
   so; the fenced block is the machine contract, the label is a convenience.
4. `gh issue create --repo UNCTAD-eRegistrations/<candidate> --title "<symptom>"
   --body-file … [--label eregulations-issue] [--label security]`.
   With `confidence: low` and several candidates, ask the user which repo; if
   they do not know, save and stop — a ticket in the wrong repo is worse than none.
5. If `jira_key` is set **and** `mcp__atlassian__addCommentToJiraIssue` is
   available, post one comment: the handoff block **without** its host and
   posture lines, plus the GitHub issue URL. No key → no Jira. Nothing filed
   (gate block, refusal) → no Jira comment either. Tool unavailable → say so,
   do not fail the filing.

## `qualified-ticket` 1.1

Additive over 1.0. **Every 1.0 requirement is kept**, including
`instance.name` for all tickets — the autopilot consumes tickets with the 1.0
validator, so a relaxed field on 1.1 would break the consumer, not the producer.

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | `"1.1"` | |
| `surface` | enum `A, B, C, SPA, deploy, monitor, unknown` | required when `schema_version == "1.1"` |
| `line` | enum `7.x, unknown` | idem; a `not-7.x` host is refused before a ticket exists |
| `lane` | enum `plan, build, execute` | idem; lane the evidence was gathered in |
| `security` | boolean | default `false` |
| `jira_key` | string, optional | `ERN-\d+` |
| `fleet` | object, **allowlisted keys only** | `line`, `overlay_version`, `platform`, `source_silent`, `drift` (boolean) |
| `instance.name` | string, required | slug, or the sentinel `platform` for a platform-wide feature |
| `qualification.version_mismatch` | boolean | overlay version ≠ probed line |
| `qualification.disprove` | object, optional | `verdict` ∈ `stands`, `weakened`, `refuted`; `notes`: list of strings (Step 9b) |
| `qualification.overlay_ref` | string | which defect memory routed the ticket: a blob sha, `cache`, `local`, `fixture` or `none` (D-5) |

Validator: 1.1 fields are required only when `schema_version` is `1.1`; the
in-repo 1.0 sample (`plugins/bpa-mcp/skills/ereg-issue/samples/qualified-ticket.example.json`)
must validate unchanged (regression test, relative path). The validator also
rejects any `fleet` key outside the allowlist and any top-level `host` or
`posture` key.

## `routing-table.json`

Rule shape (superset of `ereg-issue`):

```json
{
 "id": "fx-b7-widget-500",
 "surface": "B",
 "line": [
  "7.x"
 ],
 "match": {
  "keywords": [
   "widget",
   "500",
   "save"
  ],
  "discriminators": [
   "widget"
  ]
 },
 "candidate_repos": [
  "eRegulations-4.0-Public"
 ],
 "version_branch": "main",
 "read_via": "git show main:Project/WebAppCore/Controllers/",
 "first_evidence_source": "browser network tab",
 "also_check_and_disprove": [
  "Confirm the widget is the failing control."
 ],
 "closing_state_hint": null,
 "memory_ref": "api-surfaces#8 fixture"
}
```

`version_branch` is always the string `main` and `line` is always `["7.x"]`;
`version_branch_by_line` no longer exists (D-4).
Repositories are the six routing targets (`eRegulations-4.0-Admin`,
`-4.0-Public`, `-5.0-Admin-SPA`, `-Statistics`, `-deploy`, `-Monitor`);
`eRegulations-4.0-API` (Surface A, no 7.x) and `eRegulations-CR-Alerts` exist
in the org but are not routing targets. The test's known set is these eight
names.

**Where the rules live (C-1, D-5).** The public `routing-table.json` holds
exactly three rules, safe to publish because none of them describes a defect
that is open anywhere: `deploy-basic-auth-prelaunch-gate` (`NOT_A_BUG`,
configuration), `b7-fixed-null-menuid` (`FIXED`, a harmless UI bug with no
legacy twin) and `b7-retired-roxana-image` (`WONT_FIX`, selected by
`branch_hint`, no keywords). The 27 other 7.x rules and their 27-entry corpus
are **overlay content** in the private repository `UNCTAD-eRegistrations/eregulations-knowledge-base`
(`defects.json`: 23 open defects, by surface B 8, C 9, SPA 1, deploy 4,
monitor 1, plus the four other `FIXED` gotchas whose keywords describe defects
still open on legacy lines or retired images). Same shape as a public rule
plus an optional `security: true`. The 19 legacy rules the skill no longer
routes are kept there under `legacy/` for reference. The same repository
holds `api-surfaces.md` itself, its known-defects section included (moved
there on 2026-09-11, D-9). `surface-defaults.json` maps surface →
candidate repos so a report with no matching rule still gets a repo, at
`confidence: low`. `fixtures/defects.sample.json` is the synthetic overlay CI
loads (`conftest.py` sets `EREG_DEFECTS` to it unless `EREG_DEFECTS_REAL=1`);
on an operator's machine the same tests run over the fetched file.

Dropped: `b5-requeriments-spelling` — a line-identification fact, already
fixed on 7.x, not a defect to file.

Keyword discipline: every rule has ≥1 discriminator that no other rule **on the
same surface** shares; `test_issue_routing_table.py` enforces it. The corpus
test scores **filtered** rules (same surface as the entry).

## Router wiring

- `ereg-router/SKILL.md` Step 5 gains a clause: a `bugfix` request dispatches to
  `eregulations-issue` **in every lane with no blocking gate** (the skill is
  read-only in `plan` and `build`), instead of stopping at the handoff block;
  a router block still stops before dispatch, as today. The router hands over
  the one per-run file the skill consumes (`resolve.json`); the skill re-runs
  the gates with its own context, so `gates.json` is not a channel (C-8). It
  never reuses `/tmp/ereg-context.json` as a channel. `upgrade` and `provision` keep
  "no dedicated skill yet". Router `metadata.version` bumped with a changelog
  entry (`CLAUDE.md` rule).
- Standalone invocation (`/eregulations:issue` or plain English matching the
  skill description) is the primary entry and runs Steps 2–3 itself.
- `commands/issue.md` (new): explicit entry, `$ARGUMENTS` forwarded as the
  initial report, same `allowed-tools` as the skill.
- `plugin.json` 0.3.0, README section "Reporting an issue", Kimi manifests
  regenerated (`scripts/generate-kimi-manifests.py`).

`allowed-tools` for the skill and the command, **scoped, never bare `Bash`**
(C-3; a skill whose safety story is read-only GETs grants itself only what
its steps use):
`Read, Write, Grep, Glob, Agent, Bash(mkdir -p *), Bash(mktemp *),
Bash(python3 *), Bash(git show *), Bash(git ls-tree *), Bash(git -C *),
Bash(git rev-parse *), Bash(gh *), Bash(docker logs *), Bash(ssh *),
Bash(cat *), Bash(tee *), Bash(echo *), Bash(date *),
mcp__atlassian__addCommentToJiraIssue`.
The SSH and docker patterns are used only in `execute` lane, read-only, after
`host_posture` passed. `Agent` is for Step 9b only.

## Tests

| Test | Proves |
| --- | --- |
| `test_issue_validate_ticket.py` | the two 1.1 samples valid; `line` outside `7.x`/`unknown` invalid; the in-repo 1.0 sample valid unchanged; a 1.1 ticket without `surface`/`line`/`lane` invalid; any ticket without `instance.name` invalid; a `fleet.host` or top-level `posture` key invalid |
| `test_issue_routing_table.py` | rules = public table ∪ loaded overlay (the fixture in CI, the fetched file locally); ids unique across both; every public rule has a non-null `closing_state_hint`; resolution order flag → env → fetch → cache → local → none, with a stub `gh` runner: a failing fetch falls back to the cache and names the reason, no `gh` is "not loaded", a malformed source raises naming it; the fetch is `gh api` with the raw accept header and nothing else; every rule well-formed; repo names in the known set of eight, candidate repos among the six targets; `line` is exactly `["7.x"]`; `version_branch` is `main`; ≥1 discriminator unique per surface; `closing_state_hint` ∈ {null, NOT_A_BUG, INTENTIONAL_DESIGN, WONT_FIX, FIXED}; no keyword shaped like `user:password` |
| `test_issue_route.py` | no overlay → surface default at `low` with `overlay_loaded: false` and `overlay_ref: none`; `overlay_ref` passes through; `security` passes through from the rule; deterministic scoring; discriminators weigh double; `confidence` by the stated rules; ties → `low` with all repos; the surface filter excludes rules; `line: unknown` caps at `medium`; `branch_hint: retired-roxana-image` forces the `WONT_FIX` gotcha |
| corpus (the loaded overlay's `corpus` plus the public gotcha corpus, ≥1 entry per keyword-matched rule, each with `surface`/`line`) | each symptom routes to its intended rule with a unique winner among filtered rules |
| `test_issue_probe_surface.py` (stub opener injected, as `fleet_resolve.py` does) | each §1.1 row yields `7.x`, `not-7.x` or `unknown` as documented; `/health` is probed first — `200` JSON `{"status":"ok"}` → C 7.x, `200` text `ok` → B 7.x `main` (or the admin-web `apiUrl` hop when `window.__env` carries one), `release` `null` on either; `/release.json` `200` still decides `main` on an old image and exposes `release`; a Basic `401` on **both** `/health` and `/release.json` yields `retired-roxana-image` and stops, while a gate on one endpoint with the other unreachable yields B 7.x `branch_hint: null` + `unresolved`; a 6.x admin-api, an ERegWebApi and a legacy Public each yield `not-7.x` without any procedure-id, `CustomCss` or spelling request; no request is ever non-GET or carries `Authorization`; timeouts become `unresolved` and `unknown`, never `7.x` |
| `test_issue_redact.py` | every listed pattern is redacted; a URL query value under `pwd`/`password`/`token`/`key`/`secret` is redacted while other parameters survive; `strip_query` drops query and fragment; a clean string is untouched |
| `test_issue_gate_cases.py` (imports `gates.py` through `conftest.py`, relative path, works in CI's per-suite runs) | line rule D-2: overlay 7 + probe unknown → 7; overlay 7 + probe not-7.x → not 7 → `unsupported_version: block`, refused; overlay 5 + probe 7.x → 7 → pass with `version_mismatch: true`; overlay 5 + probe unknown → block; posture `compromised` → `host_posture: block`; the feature context is judged on `unsupported_version` only and passes on 7.x |

Run: `uv run --python 3.9 --with pytest python -m pytest plugins/eregulations/skills -q`
(and 3.13), `python3 scripts/validate-plugins.py` (no new errors from
`eregulations`), `python3 scripts/generate-kimi-manifests.py --check`.

## Out of scope

- Diagnosing or fixing the defect; deploying anything; writing to any instance.
- Jira issue **creation** (only a comment on a named key).
- eRegistrations 2.x reports (`bpa-mcp:ereg-issue`) and MCP tool defects
  (`bpa-mcp:mcp-issue`); the skill's description says so and hands off.
- A Monitor MCP path for resolution; the overlay path is what ships.
- Creating the GitHub labels ahead of time on all seven repos (Step 10 does it
  lazily; a one-off `gh label create` loop is an operator task outside the skill).
- Reports about 4.x, 5.x or 6.x instances, and Surface A altogether: refused
  with a pointer to the migration tracking, never ticketed (D-1).
- Purging old commits from GitHub. The recreated branch no longer carries
  them, but GitHub keeps them fetchable by hash until it purges them, and PR 79
  keeps its own commits. Erasure needs GitHub Support (D-8).

## Effort estimate (agent execution time)

About 3 hours: the plan's original 22 files minus the legacy sample, minus the
legacy probe branches and the per-line branch map, plus the fetch-and-cache
loader with its stubbed `gh` tests, the disprove step, the redaction and
probe additions. A first execution in a scratch tree reached 64/66 green
before the 7.x restriction, so most script code exists and is trimmed rather
than designed. The earlier 6–8 h and 4–5 h figures are retired.

Outside the figure: operator label creation and the PR review cycle.

## Appendix A — Adversarial review findings and disposition

Two reviewers, 2026-09-11. R1 = gates and hygiene; R2 = feasibility and code.

| # | Finding | Disposition |
| --- | --- | --- |
| R1-1, R2-7 | Host evidence gathered before `host_posture` is evaluated | **Fixed** — Steps reordered: resolve → gate → probe (Step 3) |
| R1-2, R2-5 | Router only dispatches in `execute` lane; context channel undefined | **Fixed** — router Step 5 clause for `bugfix` in every lane; two named per-run files handed over |
| R1-3 | `host`/`posture`/`drift` and unredacted logs leave the machine | **Fixed** — `fleet` allowlist, forbidden keys enforced by the validator, `redact.py`, Jira block stripped |
| R1-4, R2-12 | Labels do not exist on target repos; `gh issue create --label` fails; visibility unchecked | **Fixed** — Step 10 creates labels (`--force`) or files without, checks `PRIVATE` before any `security` ticket |
| R1-5 | 1.1 without `instance.name` breaks the 1.0 consumer | **Fixed** — `instance.name` stays required; `platform` sentinel for platform-wide features |
| R1-6, R2-4 | Gate's `version_major` source undefined; fails open on stale overlay | **Fixed** — "more restrictive of overlay and probe", table in Step 3, two-pass evaluation |
| R1-7, R2-11 | Feature 7.x rule decided by prose | **Fixed** — feature context `kind: dev` run through `gates.py`; only `unsupported_version` honoured, stated |
| R1-8 | `closing_state: PENDING_DECISION` on legacy stops Step 8 before the override | **Fixed** — legacy tickets keep `closing_state: null`; Step 9 stops only on the three gotcha states |
| R1-9 | `branch_pair`/`media_mount` blocks unaddressed | **Fixed** — skill never sets `touches_admin_public`/`targets_admin_deploy`; `branch_pair.py` is evidence only |
| R1-10 | `/tmp/ereg-context.json` fixed path, no writer | **Fixed** — per-run `mktemp -d`, the skill writes its own context |
| R1-11, R2-9 | `branch_hint` assumed resolved; placeholders undefined | **Fixed** — nullable, resolution order defined, single-branch lines hardcoded, `<controller>` dropped |
| R1-12 | `version_mismatch` vacuous | **Fixed** — redefined as overlay-vs-probe disagreement |
| R1-13 | Base URL not tied to the slug | **Fixed** — derived from `url`; pairing is a claim needing live verification |
| R1-14, R2-3 | Basic-auth wording implies sending credentials; gate breaks "first decisive probe" | **Fixed** — checked on the first 401 from any probe, concludes and stops; never sends `Authorization`; default credential never in keywords |
| R1-15, R2-15 | `allowed-tools` unlisted; `monitor` missing from feature surfaces | **Fixed** — listed; surfaces aligned with the enum |
| R1-16, R2-14 | Counts wrong; estimate ~2.5× low; samples need synthetic slugs | **Fixed** — 16 creates / 3 edits; 6–8 h; router fixture slugs |
| R2-1 | Surface C unreachable from one base URL | **Fixed** — `--api-url` or the `window.__env.apiUrl` hop from admin-web |
| R2-2 | Surface B line undecidable; 6.x vs 7.x flips the gate | **Fixed** — `/Home/CustomCss`, `/api/procedure/usecontactpage`, `--procedure-id`; `unknown` when undecidable, never a pick |
| R2-6 | `validate_ticket.py` self-tests never collected | **Fixed** — validator in `scripts/`, tests in `tests/test_issue_validate_ticket.py` |
| R2-8 | Seed gaps (security items), wrong line lists, branch-specific rules unfilterable | **Fixed** — rules added, lines corrected (`6.x` where §3.4 applies), `branch` filter added; `b5-requeriments-spelling` dropped |
| R2-10 | Legacy disprove sentence impossible for Surface A | **Fixed** — per-surface text |
| R2-13 | Corpus test vs filter inconsistency | **Fixed** — corpus entries carry surface/line/branch; test scores filtered rules |
| R2-15 | Tariffs probe rate-limited and non-decisive; test basename collision; 1.0 sample path | **Fixed** — probe dropped; `test_issue_*` basenames; in-repo path named |
| R2-12 | Repo names unverifiable by R2 | **Rejected as a defect** — verified by R1 with `gh` and by local remotes; recorded here as verified 2026-09-11 |

## Appendix B — Re-alignment on PR 79 (2026-09-11)

`api-surfaces.md` as merged by PR 79 supersedes the 2026-09-04 read this spec was first written against. What changed and where the spec now says so:

| Fact in PR 79 | Effect on this spec |
| --- | --- |
| 7.x branches renamed to `main` (Public, Admin, SPA, Statistics) on 2026-09-07; `feature/implement-advanced-user-rights` no longer exists | `version_branch` always from the rule (Step 5); routing-table shape loses `branch`; every 7.x rule reads `main` |
| `dot-net8-roxana-user-rights` retired: 34 commits never merged, never a `channel/stable` release, hand-built images may still run | probe `branch_hint` reduced to `retired-roxana-image`; `b7-retired-roxana-image` gotcha (`WONT_FIX`, redeploy from `channel/stable`) |
| Basic-auth gate on `main` since 7.3.2, **no default credential**, `/release.json` and `/version.json` exempt | `/release.json` probed first and decisive through the gate; a Basic `401` is B 7.x `main` unless `/release.json` was `404` (retired image); no credential to scrub from the reference |
| `/Home/CustomCss` on `main` since 7.4.0 | no longer a roxana discriminator; Surface B decision table rewritten (Step 4) |
| Five B 7.x defects fixed on `main` between 2026-09-05 and 2026-09-11 (#51, #53, #58, #59 and one commit) | five `FIXED` gotcha rules; the legacy twins of three of them restricted to 6.x/5.x; one item removed from the security list. Since Appendix C only `b7-fixed-null-menuid` is public; the other four are overlay content |
| One A 6.x defect confirmed on A 4.x as well; the 6.x path documented | a 4.x twin rule added; the 6.x rule's `read_via` fixed (overlay content since Appendix C) |
| Two B 7.x front-end files confirmed on `main` | two rules no longer branch-specific (overlay content since Appendix C) |
| SPA old line is `archive/main-2026-05` | known-branch set in the table test |
| The five router files of Task 0 are exactly PR 79's content | plan Task 0 waits for #81, PR 79's replacement, to merge into `main`, then rebases (D-8, D-9) |

## Appendix C — Third review (2026-09-11) and disposition

One reviewer, after the PR 79 re-alignment; the load-bearing claims were checked
against `gates.py`, `fleet_resolve.py`, the 1.0 validator, the Public repository's
commit dates and the marketplace repository's visibility.

| # | Finding | Disposition |
| --- | --- | --- |
| C-1 | The 49-rule table and its corpus publish descriptions of unpatched legacy defects in a repository verified PUBLIC; PR 79's §8 already does | **Fixed by decision** — defect rules and corpus move to the private overlay; the public table keeps three gotchas and the surface defaults; the plan no longer carries the rule bodies. **Dependencies:** this branch recreated without the old commits (D-8); PR 79 closed and replaced by #81, its commits left to GitHub Support (D-9) |
| C-2 | The plan mandated an AI attribution trailer and a generated-with line, and the branch uses `feat/`, against the operator's global rules | **Fixed** in the plan; the branch was recreated as `feature/eregulations-issue-skill` without the old commits (D-8) |
| C-3 | `allowed-tools` widened from the spec's scoped list to bare `Bash` in the skill and the command | **Fixed** — scoped list restored and completed (`git ls-tree`, `git -C`, `tee`, `echo`, `Agent`) |
| C-4 | A reporter URL whose query string carries a credential is replayed by the plan-lane GET and stored in `instance.url`; the redactor has no URL pattern | **Fixed** — `strip_query` before probe, store and display; query-value pattern in `redact.py` with tests |
| C-5 | No adversarial pass before filing; `also_check_and_disprove` is written for the maintainer and never attempted; verification is host identity plus one anonymous GET | **Fixed** — Step 9b disprove pass by a fresh read-only subagent; `qualification.disprove` |
| C-6 | Overlay 5 + probe 7.x blocks with the remedy "upgrade the instance", the wrong remedy for a stale overlay | **Fixed** — `gate_context.py --annotate` |
| C-7 | The `FIXED` gotchas need the running release and the probe does not expose it | **Fixed** — `release` field in the probe output |
| C-8 | Spec and plan disagreed on the router handoff (`gates.json`); "every lane" ignored that the router stops on a block before dispatch | **Fixed** — `resolve.json` only; "every lane with no blocking gate" |
| C-9 | Lane detection in Step 1 needed the overlay host from Step 2 | **Fixed** — lane stated after Step 2, from local checks only |
| C-10 | Spec (6–8 h) and plan (2.5–4 h) estimates disagreed; a plain rebase after a squash-merge of PR 79 replays its commits | **Fixed** — one figure; superseded by D-8: the branch never merges PR 79's branch and rebases on `main` after #81 is merged |

Verified and left standing: gate ordering; the version-merge rule; the
`/release.json`-first inference (`ReleaseEndpoint.cs` landed on `main` on
2026-09-03, `BasicAuthMiddleware.cs` on 2026-09-04, so no `main` build is gated
without `/release.json`); 1.0 compatibility (`instance.name` is hard-floor in the
1.0 validator); the fail-closed probe; the test arithmetic.

## Appendix D — Revision D (2026-09-11): 7.x only, overlay fetched at runtime

Decided in conversation after Appendix C. Two facts drove it: the skill will
only ever serve 7.x instances (the migration policy of 2026-09-03), and a
hand-copied overlay file is the one operational cost of keeping the plugin in
the public marketplace, which a runtime fetch removes.

| # | Decision | Effect |
| --- | --- | --- |
| D-1 | **7.x only.** A host that is not on 7.x is refused: no OUT-OF-SCOPE ticket, no override, no `audit.py` entry, no Jira; a local `NOTES.md` at most. Surface A (ERegWebApi) has no 7.x and is refused outright. | Step 5 second pass is terminal; Steps 8–10 never see a legacy line; the legacy sample is dropped; `line` enum is `7.x, unknown` |
| D-2 | **The application decides its line** (endpoint superseded by E-2: `/health`, `/release.json` only on pre-2026-09-11 images). A `200` from the app's health/stamp probe beats the overlay's `version`; the overlay keeps host and posture. Overlay lower than probe → pass with `version_mismatch: true` and a drift remedy "correct the overlay". Overlay 7 but probe `not-7.x` → refused. Probe `unknown` → the overlay's word, said as unconfirmed. | Replaces "more restrictive of overlay and probe" and supersedes C-6's remedy rewrite (`--annotate` dropped) |
| D-3 | **The probe answers 7.x / not-7.x / unknown.** `/health` first, then `/release.json` for images built before the stamp removal, then the both-endpoints-gated roxana signature, then one not-7.x reading per surface. No `--procedure-id`, `/Home/CustomCss`, `usecontactpage` or spelling probes. | Smaller probe, fewer requests to a host, fewer test rows (re-grounded off the HTTP stamps in Appendix E) |
| D-4 | **Every rule is `main`.** `line` is always `["7.x"]`, `version_branch` always `main`; `version_branch_by_line` and the line dimension of `surface-defaults.json` go; Surface A and `eRegulations-4.0-API` leave the routing targets. | Table tests simplify; 27 overlay rules + 3 public |
| D-5 | **Overlay from the private repository.** `rules.py` resolves flag → env → `gh api` fetch of `defects.json` from `UNCTAD-eRegistrations/eregulations-knowledge-base` → cache → local file → not loaded with the reason; `overlay_ref` in the ticket. The repository was created on 2026-09-11 with the 27-rule seed, the 19 legacy rules under `legacy/`, and, since D-9, the whole `api-surfaces.md`. | No per-operator copy; access is repository membership; CI keeps the fixture |
| D-6 | **PR 79 scrubbed at its tip, not in its history (corrected, then superseded by D-9).** Moving §8 alone was not enough: the endpoint tables kept describing open 7.x weaknesses, and the first four commits kept the old §8. | See D-9 |
| D-7 | **Kept from C:** disprove pass (C-5), scoped `allowed-tools` (C-3), URL redaction (C-4), `release` in the probe (C-7), router hand-off (C-8), lane after resolution (C-9), no attribution trailers (C-2). | — |
| D-8 | **Branch recreated (2026-09-11).** The first public branch carried the removed rules and the old §8 in its history. It was replaced by `feature/eregulations-issue-skill`, one commit on `main` holding this spec and the plan, and deleted. A reference-doc change another session had pushed only to the old branch was carried to PR 79's branch first and now lives in the knowledge base's copy of the reference. Task 0 never merges PR 79's branch; it rebases on `main` once #81 is merged. | Old commits stay fetchable by hash until GitHub purges them, and any clone still holding the old branch can push it back |
| D-9 | **Whole API reference private (2026-09-11).** An accurate map of these APIs is also a map of their weaknesses, so `api-surfaces.md` moved whole into `eregulations-knowledge-base`, known-defects section inline. PR 79 was closed and its branch deleted; #81 replaces it with the router's other changes and a Step 1 fetch. The skill and the router cite the reference by name and fetch it with `gh api`. | GitHub Support is asked to delete PR 79 and purge the old commits of both deleted branches |

Rejected on the way: moving the whole `eregulations` plugin to a private
marketplace (a second marketplace and CI for what one `gh api` call gives;
recommended first, withdrawn once the runtime fetch was on the table).

## Appendix E — Re-grounding off the HTTP release stamps (2026-09-11)

A later change on `eRegulations-deploy` (`feature/release-stamp-off-http`,
verified) removes the HTTP release stamps from every 7.x service. The probe
contract was keyed on `/release.json`; this appendix re-grounds it on `/health`,
which survives. Everything the earlier revision (Appendix B, D-2, D-3, the
`FIXED`-gotcha remedy) says about `/release.json` being *the* 7.x signal is
superseded by the rows below; `/release.json` remains only as a transitional
fallback.

| # | What changed on the fleet | Effect on this skill |
| --- | --- | --- |
| E-1 | `feature/release-stamp-off-http` removes `/release.json`, `/version.json` and the `Server: Kestrel` header from the 7.x images | the probe no longer depends on any of the three; a new image answers `/release.json`→404, `/version.json`→404, no `Server` header |
| E-2 | A new gate-exempt `GET /health` is added: admin-api → `200` JSON `{"status":"ok"}`; Public → `200` text `ok`; admin-web → `200` text `ok`, then JSON `{"status":"up"}` from deploy Task 9; anonymous, `Cache-Control: no-store` | `/health` is the new 7.x signal, probed **first**; JSON `{"status":"ok"}` → C 7.x, text `ok` → B 7.x `main` (or the admin-web `apiUrl` hop) |
| E-3 | On new images the Basic-auth gate exempts `/health` (not `/release.json`); a gated new `main` answers `/health` `200` through the gate | a gated new `main` is decided at step 1 by `/health` `200`; the old rule "`/release.json` decides through the gate" holds only for images built before the change |
| E-4 | `/release.json` still answers `200` on images built before the change, exempt from their gate | kept as a transitional fallback: `track: admin-api-core`→C 7.x, a version on a public host→B 7.x `main`, `{"release":…}`→admin-web; it is the only source of `release` |
| E-5 | The retired roxana image ships neither `/health` nor `/release.json`, so its gate intercepts both | roxana stays detectable: a Basic `401` on **both** endpoints → `branch_hint: retired-roxana-image`; a gate on one with the other unreachable → B 7.x `branch_hint: null` + `unresolved` |
| E-6 | New images expose no release over HTTP, so `release` is `null` on any host that answered only `/health` | the `FIXED`/regression call can no longer read `/release.json`; the operator supplies the release with `eregulations instance show <slug>` (the provisioner `/fleet` `running.releases`), and a still-reproducing `FIXED` defect with no available release is filed as a regression. `release` stays in the probe output, populated only from an old image's `/release.json` |

**Dependency handshake.** This re-grounding and the `eRegulations-deploy` app-image
change are coupled: their plan Task 6 gates the app-image changes on this skill
work, so the skill accepts **both** the new (`/health`) and old (`/release.json`)
signals throughout the rollout, when both image generations run at once.
