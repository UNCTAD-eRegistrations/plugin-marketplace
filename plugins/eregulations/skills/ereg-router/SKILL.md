---
name: ereg-router
description: Use when handling any eRegulations or TradePortal request — a country portal throwing errors or refusing to start, a deploy or redeploy of Admin or Public, an upgrade to 7.x, a code change across the Admin and Public repos, a new instance, or a missing or wrong translation label. Classifies the request, resolves which instance and version it concerns, detects what this environment can actually do right now, and evaluates the safety gates before any work starts. Also reachable explicitly as /eregulations:ereg.
allowed-tools: Read, Bash, Grep, Glob, Skill
metadata:
  version: "0.1.0"
  version-date: "2026-08-26"
  argument-hint: "[request] or --dry-run [request]"
---

# eRegulations request router

Five steps, in order, before any eRegulations work starts: classify, resolve,
detect the lane, gate, dispatch. Each step can stop the run. None of them
guesses.

All load-bearing logic lives in `scripts/`. This file orchestrates those
scripts; it does not re-implement them.

## Two rules that are not negotiable

**Rule 1 — gate decisions come from running `scripts/gates.py`, never from
reading this prose and deciding.** Assemble the context, run the script, act
on what it returns. A gate that depends on remembering to check is a gate
that eventually does not fire; these must hold every time. `references/gates.md`
explains what each gate means — it is an explanation, not the decision.

**Rule 2 — a blocking decision stops the run.** Report the block, its reason
and its remedy, and stop. There is exactly one exception: `unsupported_version`
is `overridable`, and only with a reason the user states explicitly. Overriding
requires `scripts/audit.py` to run **first** — it refuses a blank or
whitespace-only reason with a `ValueError` and writes nothing, so a rejected
override cannot quietly proceed into the work. No other gate is overridable,
whatever reason is offered.

## Before you start

Every command below refers to this skill's own directory — the one holding this
file — as `$SKILL`, and each runnable block assigns it itself. **That repetition
is deliberate: shell state does not persist between tool calls**, so a variable
set in one block is gone by the next. Substitute the real path and paste each
block whole; never rely on an assignment from an earlier step.

Scripts are stdlib-only and run under plain `python3`. They need no install.

## Step 1 — Classify

Pick one **primary** kind, plus any **secondary** kinds, from:

`bugfix` · `deploy` · `upgrade` · `dev` · `provision` · `translations`

Compound requests are the norm in incident work, not the exception.
*"Kenya is down because it's on 5.x, migrate it"* is `bugfix` primary with
`upgrade` secondary. **Carry the secondaries into the context**, as
`secondary_kinds`, so the gates evaluate the whole request rather than its
first clause. This is load-bearing: the version gate reads `kind` **and**
`secondary_kinds`, and passes a 4.x/5.x/6.x target when `upgrade` is among
them — otherwise an upgrade request would be blocked by the gate whose own
remedy is "upgrade the instance to 7.x as part of this change".

Ask **one** question only when the *primary* is genuinely ambiguous and the two
candidates dispatch differently (`deploy` versus `upgrade`, typically). Do not
pick for the user, and do not ask about secondaries — add them.

**`translations` covers two unrelated systems — split them here, not later.**
This router's only `translations` target is the eRegulations *legacy* Admin
path: `MultilangCentralRepository` label-family files consolidated into
`LangAdmin.txt`. eRegistrations 2.x work through the Global Translation
Service is a different platform with its own tooling — **hand it off to the
`translations-mcp` plugin and stop**, rather than classifying it `translations`
and dispatching. If the request names a GTS key, `ds_sync`, a country
*instance* translation catalogue, or an eRegistrations 2.x version, it is the
latter. When it is genuinely unclear which platform is meant, that is the one
question to ask.

## Step 2 — Resolve

```bash
SKILL=<path-to>/plugins/eregulations/skills/ereg-router
python3 "$SKILL/scripts/fleet_resolve.py" <instance-slug>
```

Optional: `--overlay <path>` (default `~/.ereg/fleet.local.json`, or
`$EREG_OVERLAY`), `--monitor-url` / `--token` (or `$EREG_MONITOR_URL` /
`$EREG_MONITOR_TOKEN`) for the live Monitor path. Without a Monitor URL it
resolves from the overlay alone, which is the mode the plugin ships in.

The JSON it prints is the base of the gate context: `instance`, `host`,
`version`, `platform`, `posture`, `version_major`, plus `source`, `drift` and
`unresolved`.

- **Report every `drift` entry to the user.** Monitor won; the overlay is wrong
  and only a human can correct it.
- **Never fill an `unresolved` field by inference.** Not from the country name,
  not from a sibling instance, not from a previous conversation. Unresolved is a
  real outcome the fail-closed gates act on — see `references/resolution.md`.
- If the slug is not recognised, offer the nearest matches from the overlay and
  ask. Never guess which country was meant.

## Step 3 — Detect lane

Probe cheaply, in this order, and stop at the first failure:

1. **Repos present** — the eRegulations checkouts this request needs.
2. **VPN up** — the profile the overlay records for this host (`hosts.<host>.vpn`).
3. **SSH usable** — a non-interactive connection to the resolved host.
4. **Monitor reachable** — optional; its absence degrades to the overlay.

| Lane | Means | What it may do |
| --- | --- | --- |
| `plan` | no repos, no VPN | triage and hand off |
| `build` | repos, no server contact | code, PR, docs, local builds |
| `execute` | repos + VPN + SSH | everything, gates permitting |

**State the detected lane before acting.** The lane describes what is possible
right now, not which window is in use — a terminal with the VPN down is a
frequent and legitimate state, and the honest answer is `build`, not a half-run.

## Step 4 — Gate

### 4a — Branch pair, for anything building both Admin and Public

Set `touches_admin_public: true` and populate `branch_pair_valid` before running
the gates.

**Discover the Public web project's `.csproj`; never assume its name.** The
filename is branch-dependent — on some branches it is `WebAppCore.csproj`, on
`tradeportal` it is `Project/WebApp/WebApp.csproj`. Hardcoding either produces a
confident wrong answer.

```bash
PUBLIC_ROOT=<path-to>/eRegulations-4.0-Public
grep -rli 'Unctad\.eRegulations\.Library\.csproj' \
  --include='*.csproj' "$PUBLIC_ROOT"
```

`-i` is required, not cosmetic: `branch_pair.py` matches the reference
case-insensitively, so a branch that spells it differently is found by the
module and would be missed by a case-sensitive grep — silently, as zero
candidates.

- **Exactly one candidate** — that is the Public web project. Use it.
- **Zero, or more than one** — do not guess. Leave `branch_pair_valid` unset
  (`null`), list the candidates for the user, and let the gate block. That is
  the correct outcome, not a failure of this step.

Then derive:

```bash
SKILL=<path-to>/plugins/eregulations/skills/ereg-router
python3 "$SKILL/scripts/branch_pair.py" <public-csproj> <admin-root>
```

`<admin-root>` is the real Admin checkout root. The derived reference must
resolve **inside** it, and the path is compared case-exactly against the actual
directory entries on every host — because a case-insensitive macOS volume will
happily resolve a reference that `dotnet build` on Linux rejects.

Map the result into the context as `branch_pair_valid`:
`true` → `true`, `false` → `false`, and **`null` stays `null`** — "could not
determine" is not "fine". Use real booleans, never the strings `"true"` /
`"false"`: a non-boolean value blocks, because a value nobody can read is not
an answer. As with `media_mount`, an explicit `branch_pair_valid: false` blocks
on its own whether or not `touches_admin_public` is set — a pair derived and
found incompatible is not made compatible by a flag saying the check does not
apply. Report `reason`, `admin_branch` and `public_branch`
to the user either way.

### 4b — Media mount, for any Admin deploy

Set `targets_admin_deploy: true`, then determine `media_mount` yourself — no
script produces it. With `targets_admin_deploy: true` set, leaving `media_mount`
out blocks the deploy, because unconfirmed is not confirmed. An explicit
`media_mount: false` blocks on its own, whether or not `targets_admin_deploy`
is set — a mount checked and found missing is not un-found by a flag.

Read the **target instance's compose file** and look at the Admin service's
volumes for a mount whose target is `/app/media`, in either form:

```yaml
- ./content/media:/app/media          # short form
- type: bind                          # long form
  source: ${CONTENT_DIR}/media
  target: /app/media
```

```bash
grep -n '/app/media' <instance-compose-file>
```

- **A mount targeting `/app/media` is present** → `media_mount: true`.
- **The compose is readable and the Admin service has no such mount** →
  `media_mount: false`. Admin crashes on startup without it.
- **The compose cannot be read or the Admin service cannot be identified** →
  leave `media_mount` as `null`. The gate blocks, correctly: an unverified
  precondition is not a satisfied one.

A named volume mounted at `/app/media` satisfies the mount, but say so — some
platforms silently convert a relative bind source into a named volume, which
then starts empty and must be populated.

### 4c — Assemble the context and run the gates

The context is one flat JSON object. Every key has exactly one producer:

| Key | Produced by |
| --- | --- |
| `host`, `version`, `platform`, `posture`, `version_major` | Step 2, `fleet_resolve.py` |
| `kind`, `secondary_kinds` | Step 1 |
| `touches_admin_public`, `targets_admin_deploy` | Step 1, from the request's shape |
| `branch_pair_valid` | Step 4a, `branch_pair.py` → `valid` |
| `media_mount` | Step 4b, reading the instance compose |

Write it to a file, then evaluate. `gates.py` reads the context on stdin:

```bash
SKILL=<path-to>/plugins/eregulations/skills/ereg-router
CONTEXT=/tmp/ereg-context.json
python3 "$SKILL/scripts/gates.py" < "$CONTEXT"; echo "exit=$?"
```

It prints one decision per gate — `gate`, `status` (`block`/`warn`/`pass`),
`reason`, `remedy`, `overridable` — sorted with blocking decisions first.

**The verdict is in the JSON, and nowhere else.** The exit status answers "did
the evaluation run", not "what did it decide": it is 0 whenever the gates were
evaluated, block or pass alike, and non-zero only when the context on stdin
could not be read (one line on stderr, no traceback). Never treat a non-zero
status as "blocked", and never treat 0 as "cleared" — read the decisions.

### 4d — Act on the decisions

- **Any `block`** → stop. Report the gate, its reason and its remedy verbatim.
  Do not start the work, do not do "just the safe part".
- **`warn`** → report it and continue. `windows_target` is advisory: Windows/IIS
  is transitional, not a long-term target.
- **All `pass`** → continue to Step 5.

**Override, for `unsupported_version` only.** Ask the user for a reason. Record
it *before* doing anything else:

```bash
SKILL=<path-to>/plugins/eregulations/skills/ereg-router
CONTEXT=/tmp/ereg-context.json
python3 "$SKILL/scripts/audit.py" \
  --gate unsupported_version \
  --reason "<the reason the user actually gave>" \
  --context "$(cat "$CONTEXT")"
```

It appends to `~/.ereg/audit.jsonl` (override with `--log`). A blank reason
raises before anything is written — if the command fails, the override did not
happen and the block still stands. Never invent, summarise into existence, or
supply a reason on the user's behalf.

## Step 5 — Dispatch or hand off

**In `execute` lane, with no blocking gate** — load the matching skill and do
the work:

| Kind | Skill |
| --- | --- |
| `deploy` of a legacy instance | `deploying-legacy-eregulations-instance` |
| `dev` adding a Mule 3 webservice | `adding-mule3-webservice` |
| `translations` | `merged-eregulations-translations-into-langadmin` |
| `bugfix`, `upgrade`, `provision` | no dedicated skill yet — work from the resolved context, or hand off |

If the matching skill is not installed, hand off instead of improvising.

**In `plan` or `build` lane** — stop and emit the handoff block:

```
Classification: <primary> (+ <secondaries>)
Instance:       <slug> · host <host> · version <version> · platform <platform>
Source:         monitor | overlay      Drift: <entries, or none>
Unresolved:     <fields, or none>
Lane:           plan | build  (<which probe failed>)
Gates:          <gate>: <status> — <reason>   (one line each)
Proposed steps: <what would be done in execute lane>
```

**Jira** — if, and only if, the request named an ERN key, post the handoff block
as a comment on that issue. No key, no Jira. Free-form is the front door;
ticket integration is opt-in.

**If a dispatched skill fails mid-run**, this router owns the record: what was
attempted, what changed, and what did not. Half-finished server work that nobody
wrote down is the worst available outcome.

## Dry run

`--dry-run` runs Steps 1–4 and prints the decision — classification, resolved
context, lane, and every gate decision with its reason — then **stops before
dispatch**. Nothing is executed, nothing is written, no override is recorded.
Use it before any consequential run, and to debug a misroute.

## References

| File | What it holds |
| --- | --- |
| `references/gates.md` | what each gate means, its failure direction, and why |
| `references/resolution.md` | resolution order, overlay schema, drift, unresolved |
| `references/versions.md` | version lineage and the 7.x-only policy (a human hint) |
| `references/access.md` | credential and VPN profile **names** — no addresses, no values |
