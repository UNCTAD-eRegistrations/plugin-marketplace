# eRegulations Plugin — Design Spec

**Date:** 2026-08-26
**Status:** Approved (revised after adversarial review)
**Plugin name:** `eregulations`
**Version:** 0.1.0
**Companion package:** `mcp_eregulations_monitor` (in `mcp-eregistrations` monorepo)
**Scope decision:** A + B (knowledge layer + Monitor MCP server). C (Coolify control plane) explicitly out of scope.

> **Revision note.** An adversarial review of the first draft found ten defects, four of them structural. This revision inverts the compromised-host gate to fail closed, removes all fleet posture data from the plugin (the marketplace repo is public), derives branch pairing from code instead of a table, and replaces the assumed Monitor API credential with a least-privilege account plus a lockout-safe auth path. See **Appendix A** for the full list and where each is addressed.

## Purpose

A single, portable front door for every eRegulations request — bugfix, deploy, upgrade, dev — that behaves identically in a terminal, the desktop app, or the web.

Today the operational knowledge for ~90 eRegulations country instances lives in three places that do not reach Claude in any window:

1. `eRegulations Platform — Branches & Deployment Handover` (Google Doc)
2. Three complete `SKILL.md` files parked in a Drive folder, installed nowhere
3. `eRegulations-deploy/docs/*` (8 files) plus `HANDOVER-2026-06-08.md`

Seven of the eight `eRegulations-*` repos have no `CLAUDE.md`. Only `eRegulations-5.0-Admin-SPA` does.

The eRegistrations side of the house already solves this with the `unctad-digital-government` marketplace (18 plugins, 7 enabled). This spec applies that proven pattern to eRegulations.

**This is a knowledge-distribution problem, not a tooling problem.** Every design decision below follows from that.

## Constraints (established, not chosen)

| Constraint | Source | Consequence |
| --- | --- | --- |
| Terminal is the only executor | User decision, 2026-08-25 | App/web lanes must degrade honestly, never half-execute |
| Ships to the team via the marketplace | User decision, 2026-08-25 | See next row — this one has teeth |
| **`plugin-marketplace` is a PUBLIC GitHub repo** | `gh repo view` → `"visibility": "PUBLIC"` | **No credentials, no server addresses, and no security posture may ship in the plugin** |
| Front door is one router command | User decision, 2026-08-25 | Routing is explicit and auditable, not implicit skill-matching |
| 7.x only going forward | Handover Doc §3 | New work on 4.x/5.x/6.x is gated |
| Admin ↔ Public branch pairing | Handover Doc §10; `WebAppCore.csproj` project-references `Unctad.eRegulations.Library` | A build gate is mandatory — and derivable from code, so it is derived |
| Two hosts recorded as likely compromised | Handover Doc §5 | A fail-closed host gate is mandatory |
| Admin crashes without `/app/media` | Handover Doc §10 | A deploy precondition check is mandatory |
| Monitor API is still moving | `eRegulations-Monitor/PRD.md` (provisioning is Phase-1) | MCP server must fail loudly on shape change |
| Monitor auth is user/password → JWT, no service accounts, 5-attempt lockout | `backend/src/routes/auth.ts`, `middleware/auth.ts` | Credential provisioning is a Monitor-side change, not an admin action |

## Data classification

This table governs where every fact is allowed to live. It exists because the marketplace is public.

| Class | Examples | Lives in | Never in |
| --- | --- | --- | --- |
| **Public knowledge** | Version lineage, gate policy, build procedures, which repos pair | The plugin | — |
| **Fleet state** | Which instance runs where, what version, up/down | Monitor, resolved at runtime | The plugin |
| **Security posture** | Which hosts are compromised or unmaintained | Monitor `posture` field, or the operator's local overlay | **The plugin** |
| **Addresses** | Server IPs, SSH targets, VPN endpoints | Operator's local overlay; `<host>` placeholders in docs | **The plugin** |
| **Credentials** | Any secret value | Secret store, referenced by name only | **The plugin** |

**Operator local overlay:** `~/.ereg/fleet.local.yaml` — never in any repo, listed in the plugin README as an operator-created file. Holds addresses and any posture overrides Monitor cannot yet serve.

> **Pre-existing exposure, out of scope but worth acting on:** `5.9.49.171` is already committed to this public repo. Every other address in `plugins/` is loopback or RFC1918. Worth a separate look; not fixed here.

## Architecture

Two deliverables in two repos.

```
plugin-marketplace/
└── plugins/eregulations/
    ├── .claude-plugin/plugin.json      # name matches dir; validate-plugins.py enforces
    ├── .kimi-plugin/plugin.json        # mirror; enforced by same validator
    ├── .mcp.json                       # registers the Monitor server
    ├── README.md                       # documents the ~/.ereg/ overlay the operator must create
    ├── commands/
    │   └── ereg.md                     # the /ereg front door
    └── skills/
        ├── ereg-router/
        │   ├── SKILL.md                # classify → resolve → lane → gates → dispatch
        │   ├── references/
        │   │   ├── versions.md         # 4.x/5.x/6.x/7.x lineage + support policy  [public knowledge]
        │   │   ├── gates.md            # gate definitions + fail-open/closed policy [public knowledge]
        │   │   ├── resolution.md       # HOW to resolve fleet facts, not WHAT they are
        │   │   └── access.md           # credential NAMES + which VPN profile; no addresses
        │   └── fixtures/
        │       └── fleet.sample.yaml   # synthetic fleet for gate tests; no real hosts
        ├── deploying-legacy-eregulations-instance/   # from Drive, split
        │   ├── SKILL.md
        │   └── references/
        ├── adding-mule3-webservice/                  # from Drive
        └── merged-eregulations-translations-into-langadmin/  # from Drive

mcp-eregistrations/
└── src/mcp_eregulations_monitor/       # tenth package in the monorepo
```

Note what is **absent** versus the first draft: there is no `fleet.md` and no `branch-pairing.md`. Both were static tables of facts that rot. Fleet facts are resolved at runtime; branch pairing is derived from code.

### Naming decisions

- **Plugin is `eregulations`**, not `ereg` — sits unambiguously beside the eRegistrations plugins in the same marketplace.
- **Command is `/ereg`** — typed constantly; brevity wins where ambiguity does not.
- **Server display name is `Monitor`**; entry point `mcp-eregulations-monitor`; package `mcp_eregulations_monitor`.

The package name uses `eregulations` inside a repo named `mcp-eregistrations`. This mismatch is accepted deliberately: the monorepo already ships nine servers as one PyPI package with per-server entry points and a shared `mcp_eregistrations_common` HTTP/audit layer. Forking a second distribution to fix a name would duplicate the release train, the auth scaffolding, and the CI for no functional gain.

### Why reference files are not skills

They are data the router reads, not behaviour. Registering them as skills would put four near-identical descriptions into skill-matching and cause misfires. They load only when the router resolves context.

### Why the 51 KB skill is split

`deploying-legacy-eregulations-instance/SKILL.md` is 51 KB as authored. Loaded whole it dominates context on every invocation, for a procedure where a typical run needs a fraction of it. It becomes a `SKILL.md` carrying the flow, plus `references/` for per-phase detail.

## Component 1 — The `/ereg` router

`/ereg <free-form request>` runs five steps in fixed order. Each may stop the run. None guesses silently.

`/ereg --dry-run <request>` runs steps 1–4 and prints the decision — classification, resolved context, lane, gates evaluated and why — then stops before dispatch. This is both the safety valve before a consequential run and the only practical way to debug a misroute. Dry-run is also the mode every acceptance scenario is asserted against.

### Step 1 — Classify

Into a **primary** kind, plus optional **secondary** kinds, from:

`bugfix` · `deploy` · `upgrade` · `dev` · `provision` · `translations`

Compound requests are the norm in incident work, not the exception — *"Kenya is down because it's on 5.x, migrate it"* is `bugfix` (primary) + `upgrade` (secondary). The primary kind drives dispatch; secondaries are carried into the resolved context so gates evaluate against the whole request, not just its first clause.

If the primary is genuinely ambiguous — the request could reasonably lead with either kind, and they dispatch differently — the router asks one question. It does not pick.

### Step 2 — Resolve context

Two sources with a strict precedence rule:

> **Monitor is authoritative for STATE** — up/down, version actually running, which server hosts it, SSL status.
> **The plugin is authoritative for POLICY** — what we support, which gates exist, what each gate does.

They do not override each other because they answer different questions. Note the correction from the first draft: *which server hosts an instance* is state, and Monitor owns it. It was previously miscategorised as a plugin-held fact, which is what let the host gate run on stale data.

**Resolution order for any fleet fact:** Monitor → operator overlay (`~/.ereg/fleet.local.yaml`) → **unresolved**. There is no third source and no guessing. "Unresolved" is a real outcome that gates act on.

**Drift detection.** Where Monitor and the overlay disagree, Monitor wins and the router reports the drift, so the overlay is corrected by real runs rather than rotting.

Resolution targets, by primary kind:

| Kind | Must resolve |
| --- | --- |
| `bugfix` | instance → host → **host posture** → version → access route |
| `deploy` | instance → host → target version → **derived branch pair** → host preconditions |
| `upgrade` | instance → current version → target 7.x → data migration inputs |
| `dev` | repo → active branch → **derived** paired repo branch |
| `provision` | v1: resolve target host, then hand off — see Scope Boundaries |
| `translations` | instance → label families → `LangAdmin.txt` target |

### Step 3 — Detect lane

Cheap probes in order: repos present → VPN up → SSH usable → Monitor reachable (public, so usually yes).

Three outcomes:

- **plan** — triage and hand off. No repos, no VPN.
- **build** — code, PR, docs, builds. Repos, no server contact.
- **execute** — everything. Repos + VPN + SSH.

The lane describes what is *possible right now*, not which window is in use. A terminal with the VPN down is a frequent, legitimate state; the router degrades honestly rather than starting work it cannot finish.

### Step 4 — Gates

Each gate declares a **failure direction**, and that declaration is the load-bearing part of this design.

- **Fail closed** — if the gate's input cannot be verified, the gate *blocks*. Used wherever proceeding on stale data could damage a system or touch a compromised host.
- **Fail open** — if the input cannot be verified, the gate warns and proceeds. Used only for advisory facts.

| Gate | Fires when | Direction | Overridable |
| --- | --- | --- | --- |
| **Host posture** | Resolved host posture is `compromised`, **or is `unknown`/unresolved** | **Closed** | No |
| **Branch pair** | A build touches Admin + Public and the derived pair does not resolve | **Closed** | No |
| **Missing media mount** | Admin deploy without `/app/media` bind-mounted | **Closed** | No |
| **Unsupported version** | New work would land on 4.x / 5.x / 6.x | Closed | **Yes, audited** |
| **Windows target** | Any Windows/IIS deploy | Open (advisory) | n/a |

**The host-posture gate is the reason this revision exists.** In the first draft it consumed a static table and, when Monitor was unreachable, proceeded on unverified data. That is wrong in both directions: a stale record reading "not compromised" means the gate silently never fires, and one reading "compromised" blocks legitimate work. It now treats **unresolved and unknown as blocking**, identically to a confirmed-compromised host. An operator who knows better records the posture in their overlay; nobody proceeds on a host the system cannot identify.

**Branch pairing is derived, not tabulated.** The router reads `WebAppCore.csproj`'s project reference to `Unctad.eRegulations.Library` and verifies it resolves against the actual Admin checkout. A static table would rot with nothing to correct it — there is no Monitor equivalent for branches. Deriving it makes the gate correct by construction, and reduces `versions.md` to a hint for humans rather than a source of truth. As of writing, the local clones are Admin `database-layer-update-NET8` (6.x) and Public `tradeportal` (5.x) — an invalid pair the gate must reject.

**Override audit.** The unsupported-version gate is the only overridable one, and it bypasses the org's headline policy. Every override appends a record to `~/.ereg/audit.jsonl`: timestamp, request, gate, resolved context, the stated reason. The override is refused without a reason. Local file, never committed — this is a memory aid and an incident-reconstruction trail, not an access control.

### Step 5 — Dispatch or hand off

- **execute lane** — load the specific skill, do the work.
- **plan / build lane** — stop and emit a handoff block: classification (primary + secondary), resolved context, gates evaluated, proposed steps.

If the request names an ERN key, the handoff is also posted as a Jira comment. If it does not, Jira is untouched. Free-form is the front door; ticket integration is opt-in.

### Error handling

| Failure | Behaviour |
| --- | --- |
| Monitor unreachable | Fall to the operator overlay. Facts it cannot supply are **unresolved**, and unresolved input to a fail-closed gate **blocks**. Advisory facts proceed labelled unverified. |
| Instance not recognised | Offer nearest matches; ask. Never guess which country was meant. |
| Ambiguous primary kind | Ask one question. Never pick between `deploy` and `upgrade`. |
| Dispatched skill fails mid-run | Router owns the record: what was attempted, what changed, what did not. Half-finished server work that nobody wrote down is the worst available outcome. |

## Component 2 — Monitor MCP server

Package `mcp_eregulations_monitor` in the `mcp-eregistrations` monorepo. Follows the `graylog-mcp` precedent: **Monitor-native auth, not Keycloak**. Reuses `mcp_eregistrations_common` for HTTP and audit.

### Auth model — verified against the code, not assumed

`backend/src/routes/auth.ts` and `middleware/auth.ts` establish:

- Username + password → JWT bearer, passwords bcrypt-hashed
- Role hierarchy `viewer` (0) < `operator` (1) < `admin` (2), enforced by `requireRole`
- **Account lockout after 5 failed attempts, 15 minutes**
- A refresh token with a payload shape deliberately different from the access token

This produces four hard requirements:

1. **A dedicated `viewer`-role account**, not a shared human account. Least privilege is enforced *server-side* by `requireRole` — strictly stronger than the first draft's "we simply won't expose write tools," which is a convention any later change can undo.
2. **Never auto-retry a rejected credential.** One failed login surfaces to the operator immediately. Retrying a stale password burns the 5-attempt budget and locks the account — and if the account were shared with a human, it would lock a person out of the fleet dashboard mid-incident.
3. **Implement refresh properly**, honouring the two payload shapes. This is real work the first draft's estimate omitted.
4. **Shape probe on connect** — Monitor's API is still moving, so the server verifies the response shape and **fails loudly on mismatch** rather than returning confidently wrong fleet data.

### Monitor-side prerequisites (external, blocking for B)

These are changes to `eRegulations-Monitor`, a different repo with its own review and deploy:

- **A `viewer` service account** for the MCP server. Monitor has no service-account concept today — this is a feature request, not an admin action.
- **A `posture` field** on the server record (`ok` / `degraded` / `compromised` / `unknown`), so the host gate can resolve posture from live state instead of an operator overlay. Until it exists, the overlay is the only source and the gate blocks on anything not listed — correct, but noisier.

### Tool surface — seven tools, all read-only

| Tool | Purpose |
| --- | --- |
| `monitor_connection_status` | Verify connectivity and auth state |
| `monitor_auth_login` | Authenticate; no auto-retry on rejection |
| `monitor_instance_list` | List instances; filter by country / server / version / status |
| `monitor_instance_get` | Full record for one instance |
| `monitor_ssl_status` | SSL/expiry state, fleet-wide or per instance |
| `monitor_server_list` | Servers with instance counts and posture |
| `monitor_fleet_summary` | Counts by version / server / status |

### Provisioning is excluded from v1

Monitor exposes `routes/provision.ts`. Wrapping it would let a chat window create a country instance. That is a consequential write, Monitor's provisioning is still PRD-stage, and nothing in A+B needs it. The `viewer` role also makes it unreachable server-side. Revisit in v2 with its own confirmation rails.

### The seam

A works standalone: the router calls Monitor over plain HTTP. B swaps that for tools.

**Corrected claim:** this is *one section of `ereg-router/SKILL.md`, plus a distinct auth path* — not the one-line swap the first draft asserted. HTTP and MCP differ in error surface (status codes and timeouts versus tool errors), and MCP adds a login/refresh lifecycle the HTTP path has no equivalent for. B's estimate absorbs the difference. The seam still holds where it matters: **B is an accelerator, not a dependency.** If Monitor's API shifts, A keeps working.

## Security

The plugin references credentials **by name only** and carries no value, no address, and no posture. See **Data classification** — that table is the enforceable rule, and the marketplace being public is why it exists.

**Flagged, deliberately out of scope:** `RD Different accesses` (same Drive folder) contains working VPN, SSH, GitLab, Mailgun and currency-API passwords in plain text, several tied to a personal account rather than an institutional one. Two of the hosts those credentials open are recorded as likely compromised. Rotating them and moving them to a shared secret store is worth its own piece of work. It is not folded in here: mixing a security cleanup into a tooling change makes both harder to review.

## Acceptance criteria

Mechanical checks:

- `uv run --python 3.12 scripts/validate-plugins.py` passes (the system Python is 3.9 and too old for the script's type syntax)
- Python half passes the monorepo's existing ruff + mypy + `pytest` setup
- Unit tests use fixtures recorded from Monitor, not live calls

### Conventions the validator enforces

Every `SKILL.md` must carry, in frontmatter:

- `name`, `description`, `allowed-tools`
- a `metadata` block containing `version` and `version-date`

Keep `allowed-tools` minimal per the marketplace `CLAUDE.md`.

**Baseline at branch point: 14 errors across 149 files, all pre-existing in other plugins.** This work must not increase that count. Fixing the pre-existing 14 is out of scope.

### Gate scenarios

**All gate scenarios run in `execute` lane against `fixtures/fleet.sample.yaml`.** Both halves of that sentence are corrections from the first draft:

- *Execute lane*, because plan lane touches nothing **by construction** — no VPN, no SSH. A plan-lane assertion cannot distinguish "the gate fired" from "the lane prevented action," so it tests the lane, not the gate.
- *Synthetic fixtures*, because the first draft pinned its host-gate test to Turkmenistan TP — the last instance on Old eRegulations, and the one the handover makes top priority to move. The day it moves, that test passes while testing nothing: a green result meaning the opposite of what it appears to.

**If any of these silently passes, the router is worse than useless — it is confidently wrong about production.**

| # | Scenario | Must |
| --- | --- | --- |
| 1 | Bugfix against a fixture host with posture `compromised`, execute lane | Block. Offer migration, not in-place repair. |
| 2 | Bugfix against a fixture host with posture **absent**, execute lane | Block identically to #1 — this is the fail-closed assertion |
| 3 | Admin + Public build against the current clones, execute lane | Block on the derived pair, citing the actual `csproj` reference |
| 4 | Fleet question with Monitor unreachable and no overlay entry | Advisory facts labelled unverified; any fail-closed gate blocks |
| 5 | Monitor and overlay disagree on version | Monitor wins; drift reported |
| 6 | Unsupported-version override without a stated reason | Refused. With a reason: proceeds, and `~/.ereg/audit.jsonl` gains a record |
| 7 | Compound request (`bugfix` + `upgrade`) | Both kinds resolved; gates evaluate against both |
| 8 | Rejected Monitor credential | Surfaces once. **No retry.** Asserted against a mock counting login attempts — exactly one |

Scenario 8 is asserted with a mock rather than the live service, because verifying "it does not lock the account" against the real Monitor risks locking the account.

## Sequencing and cost

A ships first, complete and working. B follows.

| Phase | Artifacts | Agent time |
| --- | --- | --- |
| **A** | 1 router skill · 4 reference files · 1 fixture fleet · derived branch-pair check · dry-run mode · audit-log writer · 3 Drive skills migrated (one split) · 1 marketplace entry · 8 acceptance runs | **6–9 h** |
| **B** | 1 Python package (~7 modules) · 7 tools · auth + refresh lifecycle · lockout-safe login path · shape probe · fixtures + unit tests · pyproject entry point + wheel manifest · `.mcp.json` · 1 PyPI release · router seam swap | **12–16 h** |
| **Follow-up** | 7 repo `CLAUDE.md` pointers | 7 PRs, review-paced |

**Total for A+B: ≈ 18–25 hours of agent execution**, up from the first draft's 12–18. The increase is almost entirely the auth lifecycle, the fail-closed logic, and the larger acceptance set — all of which the review showed were missing rather than optional.

**External blockers, both on `eRegulations-Monitor`:**

1. A `viewer` service account — needs service-account support built, then reviewed and deployed.
2. A `posture` field on the server record — needs a schema change, reviewed and deployed.

Neither blocks A. **A is fully functional with posture supplied by the operator overlay**, and can be built, validated and shipped while both land.

**Rollout:** install from a local marketplace path → run the eight gate scenarios → publish to the marketplace at 0.1.0 → announce.

## Scope Boundaries

**In scope:** the `/ereg` router with dry-run and override auditing, its reference files and fixtures, the three migrated Drive skills, the read-only Monitor MCP server, marketplace packaging for both.

**Out of scope:**

- **C — Coolify/API control plane.** Deploys need VPN + SSH, which the terminal already has. The 4.x/5.x Windows fleet, where most instances still live, has no API to drive.
- **Instance provisioning tools.** See Component 2.
- **Credential rotation** for `RD Different accesses`. See Security.
- **The `5.9.49.171` exposure** already committed to this public repo. See Data classification.
- **Fixing the 14 pre-existing validator errors** in other plugins.
- **The seven repo `CLAUDE.md` PRs** as a blocking dependency. The plugin is fully functional if they never merge.

## Appendix A — Adversarial review findings and disposition

| # | Severity | Finding | Where addressed |
| --- | --- | --- | --- |
| F1 | Critical | Plugin would publish a compromised-host map to a public repo | **Data classification**; `fleet.md` deleted; overlay introduced |
| F2 | Critical | Host gate consumed rotting data and failed **open** | **Step 4**; gate now fail-closed, unknown treated as compromised |
| F3 | High | Gate scenario asserted in plan lane, where nothing can act anyway | **Gate scenarios**; all now execute lane |
| F4 | High | Test fixture pinned to Turkmenistan, whose migration is top priority | **Gate scenarios**; `fixtures/fleet.sample.yaml` |
| F5 | High | Monitor has no service accounts; retry could lock the account | **Auth model**; `viewer` account, no-retry rule, scenario 8 |
| F6 | Medium | "One-file swap" understated the MCP auth lifecycle | **The seam**; claim corrected, B re-estimated |
| F7 | Medium | Single classification fails on compound incident requests | **Step 1**; primary + secondary kinds |
| F8 | Medium | The one overridable gate had no audit trail | **Step 4**; `~/.ereg/audit.jsonl`, reason required |
| F9 | Medium | `branch-pairing.md` would rot with nothing to correct it | **Step 4**; derived from `csproj` instead |
| F10 | Low | No way to ask the router what it would do | **Component 1**; `--dry-run` |

## Open questions

None blocking. The two Monitor-side prerequisites are external dependencies with owners, not design questions.
