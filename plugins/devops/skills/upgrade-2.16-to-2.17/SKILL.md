---
name: upgrade-2.16-to-2.17
description: >
  Upgrade a single eRegistrations instance under
  `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from 2.16 to 2.17, where
  `<env>` is one of dev/test/preview/prelive/live. Bumps unctad image tags from
  `:BETA` to `:2.17`, applies the BPA/DS/GDB service renames that landed in 2.17,
  pins floating `:DEV` tags for statistics, ds-frontend, gdb to `:2.17`, version-bumps
  `EREGISTRATIONS_VERSION` and `BUILD_TYPE`, and bumps Opensearch from 2.12.0 to
  2.19.4. Strict mode — aborts on anything unexpected. Env-aware anomaly thresholds
  for `BUILD_TYPE` and `EREGISTRATIONS_VERSION`. Detects legacy Wildfly-style
  Keycloak config and aborts with guidance (KC overhaul is out of scope here — it
  was completed during the 2.15 cycle on most instances). LIVE invocations require a
  retype-country confirmation rail (skipped in chain mode). Two invocation modes:
  standalone (creates branch, pushes, opens PR) and chain mode (`CHAIN_MODE=1
  CHAIN_BRANCH=<name>`, commits to orchestrator-managed branch). Swarm-stack
  (docker-stack.yml) shape only — instances still on docker-compose.yml must
  run /docker-swarm-migration first.
license: UNCTAD-Internal
compatibility: Run from the eregistrations-v4 working tree on master (standalone) or on the orchestrator-supplied chain branch (chain mode), with a clean tracked tree. Requires an authenticated CLI for the host VCS in standalone mode (gh for GitHub origins; Bitbucket origins skip CLI PR creation and print a manual link).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(grep *), Bash(test *), Bash(ls *), Bash(basename *), Bash(dirname *), AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country>] [<env>] [BACKUP_CONFIRMED=1] [CHAIN_MODE=1 CHAIN_BRANCH=<name>]"
  jira: "TOBE-17814"
---

# Upgrade an eRegistrations instance from 2.16 to 2.17

You are performing a mechanical eRegistrations 2.16 → 2.17 upgrade of a single instance. The target file is `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`, where `<env>` ∈ {dev, test, preview, prelive, live}. The upgrade applies a fixed set of transformations: image tag bumps from `:BETA` to `:2.17`, service renames (BPA/DS/GDB), pinning of `:DEV` tags on the statistics and ds-frontend services, env-var version bumps, and an Opensearch bump from 2.12.0 to 2.19.4. Operate in **strict mode**: any anomaly pauses for explicit user input, with `abort` as the default.

The skill is invoked as `/upgrade-2.16-to-2.17` with optional positional args. It is also routed to by the `upgrade-eregistrations-instance` orchestrator when it detects a swarm-stack instance on `unctad/*:BETA` images.

When the upgrade is approved, **standalone mode** commits on a fresh branch `chore/upgrade-<env>-<country>-2.16-to-2.17`, pushes it, and opens a pull request. **Chain mode** commits a single step-scoped commit on the orchestrator-managed branch and returns.

## Arguments

The skill accepts up to four positional/flag tokens, whitespace-separated, in any order:

- `<env>` — one of `dev`, `test`, `preview`, `prelive`, `live` (lowercase).
- `<country>` — the folder name under `Conf-<UPPER_ENV>/compose/`.
- `BACKUP_CONFIRMED=1` — flag.
- `CHAIN_MODE=1` — flag.
- `CHAIN_BRANCH=<branch>` — orchestrator-managed branch name.

Tokenizer rules and env→directory mapping are identical to `upgrade-2.15-to-2.16`.

## Scope (intentionally narrow)

- **In scope:** a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` whose `unctad/*` images are pinned at `:BETA` (the 2.16 tag convention).
- **Out of scope:** instances still on `docker-compose.yml` (refuse and point at `/docker-swarm-migration`), Coolify-managed instances, version pairs other than 2.16 → 2.17, instances with **legacy Wildfly-style Keycloak config** (see Pre-flight KC check below — abort with guidance).

## STEP 0: Pre-flight git checks

**Standalone mode:**

1. Working tree is a git repo at the repo root (`git rev-parse --show-toplevel`).
2. Current branch is `master`.
3. No staged or modified tracked files (`git status --porcelain --untracked-files=no` is empty).
4. Origin host detected, CLI authenticated (gh for GitHub, manual link for Bitbucket).
5. `master` in sync with origin (`git pull --ff-only origin master`).

**Chain mode:**

1. Working tree is a git repo.
2. Currently on `<CHAIN_BRANCH>`.
3. No staged or modified tracked files.
4. Skip host detection and pull.

## STEP 1: Resolve env, country, target

1. **Resolve `<env>`** (from args or interactive).
2. **Compute `<UPPER_ENV>`.**
3. **Verify shape**: `test -d "Conf-<UPPER_ENV>/compose"`.
4. **Find candidates**:
   ```bash
   for f in Conf-<UPPER_ENV>/compose/*/docker-stack.yml; do
     if grep -q 'unctad/.*:BETA' "$f"; then
       echo "$(basename "$(dirname "$f")")"
     fi
   done | sort
   ```
5. Zero candidates → "Nothing to upgrade — no `Conf-<UPPER_ENV>` swarm-stack instance contains `unctad/*:BETA`. Compose-only instances must run `/docker-swarm-migration` first." Exit 0.
6. Resolve `<country>` (validation rules same as 2.15→2.16).
7. Confirm `TARGET=Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` exists.
8. Save state.

## STEP 1.5: Backup confirmation

Same as 2.15→2.16: skip if `BACKUP_CONFIRMED=1`, otherwise prompt.

## STEP 2: Pre-transformation strict scan

### Anomaly thresholds

| `<env>` | expected `BUILD_TYPE` | expected `EREGISTRATIONS_VERSION` |
|---|---|---|
| dev | `DEV` | `DEV` |
| test, preview, prelive, live | `BETA` | `2.16` |

Print: "Env: `<env>`. Expected `BUILD_TYPE=<expected_BT>`. Expected `EREGISTRATIONS_VERSION=<expected_EV>`."

### Pre-flight Keycloak shape check

This is a **hard abort** check, not an anomaly: 2.16 → 2.17 assumes the Keycloak config is already in KC 17+ format (`KC_DB`, `KC_HOSTNAME`, `KEYCLOAK_ADMIN` env-var family, optional `command: ["start", "--optimized"]`). The KC overhaul itself was completed during the 2.15 cycle on every modern instance.

Locate the `keycloak:` service block and inspect its `environment:` list:

- **Modern KC (proceed)**: contains `KC_DB=postgres` (or any `KC_DB_*` keys) AND does not contain legacy `DB_VENDOR=` / `DB_ADDR=` env vars.
- **Legacy KC (abort)**: contains `DB_VENDOR=POSTGRES`, `DB_ADDR=`, or `KEYCLOAK_USER=` (the old Wildfly env-var family). Print:
  > "Keycloak in `<TARGET>` is on the legacy Wildfly env-var format (`DB_VENDOR`, `DB_ADDR`, etc.). The 2.16 → 2.17 skill assumes the KC 17+ overhaul has already happened — see commit `5ba86b39` (live.libya 2.17 upgrade) for the full pattern, or apply the overhaul manually before re-running this skill. Aborting."
  Exit non-zero.
- **Mixed / unrecognised**: print the keycloak env block verbatim and abort: "Keycloak env config doesn't match either modern or legacy shape. Resolve manually before re-running."

### Anomaly kinds (run all scans, prompt one at a time)

Each pauses for `(c)ontinue / (s)kip / (a)bort` (default abort). Same prompt mechanics as 2.15→2.16.

1. **Unexpected unctad image tag.** A line matching `image:\s*unctad/[^:]+:[^ ]+` whose tag is not in `{BETA, 2.17, DEV, 2.18}`. The `:BETA` images are the upgrade targets; `:DEV` is expected on country-specific mule images and on the floating-tag services that Rule 5 will pin (`statistics-backend`, `statistics-frontend`, `ds-frontend`, `license-registry`). `:2.18` is unexpected — flag it.

2. **Already-2.17 services.** Any unctad service already on `:2.17`. Suggests partial prior upgrade.

3. **Unexpected `EREGISTRATIONS_VERSION` value.** Any `EREGISTRATIONS_VERSION=` line whose RHS (after stripping quotes) is not `<expected_EV>`.

4. **Unexpected `BUILD_TYPE` value.** Any `BUILD_TYPE=` line whose RHS (after stripping quotes) is not `<expected_BT>`.

5. **Opensearch on unexpected version.** A line matching `image:\s*opensearchproject/opensearch:` whose tag is neither `2.12.0` (the expected 2.16 baseline) nor `2.19.4` (the 2.17 target). Print and prompt.

If no anomalies: "No anomalies. Applying transformations." and proceed.

## STEP 3: Apply the transformations

Edit `<TARGET>` in place. Preserve indentation and line endings. Apply rules in order.

### Image tag bumps

**Rule 1 — Bump unmanaged unctad images from `:BETA` to `:2.17`.**
For every line matching `^(\s*)image:\s*unctad/([^:\s]+):BETA\s*$`, replace `:BETA` with `:2.17`. Keep leading whitespace and image name verbatim.

**Rule 2 — Service rename + tag bump for the BPA / DS / GDB family.**
Apply each of these transformations exactly. They combine a service rename and a tag bump in one regex:

| Old line (anywhere in file)                    | New line                                |
|------------------------------------------------|-----------------------------------------|
| `image: unctad/eregbpafrontend:BETA`           | `image: unctad/bpa-frontend:2.17`       |
| `image: unctad/eregbpawebsocket:BETA`          | `image: unctad/bpa-websocket:2.17`      |
| `image: unctad/eregbpabackend:BETA`            | `image: unctad/bpa-backend:2.17`        |
| `image: unctad/eregcms:BETA`                   | `image: unctad/ds-backend:2.17`         |
| `image: unctad/license-registry:DEV`           | `image: unctad/gdb:2.17`                |
| `image: unctad/license-registry:BETA`          | `image: unctad/gdb:2.17`                |

Preserve leading indentation. The legacy service names (`eregbpafrontend`, `eregbpabackend`, `eregbpawebsocket`, `eregcms`, `license-registry`) survive 2.15→2.16 untouched and are renamed only here in 2.17.

Note that the YAML service block names (`bpa-frontend:`, `bpa-backend:`, `websocket:`, `ereg-cms-frontend:`, `gdb:`) are the local keys used in the docker-compose file and may already match the new image names — they do not need to be changed in this rule. Only the `image:` line gets the new value.

**Rule 3 — Pin floating `:DEV` tags on statistics, ds-frontend.**

| Old line                                       | New line                                |
|------------------------------------------------|-----------------------------------------|
| `image: unctad/statistics-backend:DEV`         | `image: unctad/statistics-backend:2.17` |
| `image: unctad/statistics-frontend:DEV`        | `image: unctad/statistics-frontend:2.17`|
| `image: unctad/ds-frontend:DEV`                | `image: unctad/ds-frontend:2.17`        |

**Rule 4 — Country-specific images stay on `:DEV`.**
Lines matching `^(\s*)image:\s*unctad/(mule3-|mule4-|cashier-)[^:\s]+:DEV` (country-specific mule and cashier images) **must not be touched**. Verify by greping for them post-edit and reporting the count for transparency. If any such line was inadvertently bumped, that's a Rule 4 anomaly — abort.

**Rule 5 — Opensearch bump.**
Replace `image: opensearchproject/opensearch:2.12.0` with `image: opensearchproject/opensearch:2.19.4`. If the source tag isn't `2.12.0`, the STEP 2 anomaly scan would have caught it; here we only operate on the standard line.

### Env-var version bumps

Locate every `EREGISTRATIONS_VERSION=` and `BUILD_TYPE=` env-list item (across all service blocks).

**Rule 6 — Bump `EREGISTRATIONS_VERSION`.**
Replace any list item whose stripped content is `- EREGISTRATIONS_VERSION=<expected_EV>` (or quoted variant) with `- EREGISTRATIONS_VERSION=2.17`. Preserve indentation, dash, and quoting.

**Rule 7 — Bump `BUILD_TYPE`.**
Replace any list item whose stripped content is `- BUILD_TYPE=<expected_BT>` (or quoted variant) with `- BUILD_TYPE=LIVE` for env=test/preview/prelive/live. For env=dev: `BUILD_TYPE=DEV` stays as-is, no replacement. (The `<expected_BT>` for dev is `DEV`, so the regex won't match anything to change.)

When all rules are applied, proceed to STEP 4.

## STEP 4: Post-transformation safety scan

After applying the rules, run these greps on the modified `<TARGET>`:

1. `grep -n 'unctad/[^:]\+:BETA' "$TARGET" || true` — should be empty (Rules 1, 2 catch all `:BETA`).
2. `grep -n 'unctad/eregbpafrontend\|unctad/eregbpabackend\|unctad/eregbpawebsocket\|unctad/eregcms\|unctad/license-registry' "$TARGET" || true` — should be empty (Rule 2 renamed all).
3. `grep -n 'EREGISTRATIONS_VERSION=2\.16' "$TARGET" || true` — should be empty.
4. `grep -n 'BUILD_TYPE=BETA' "$TARGET" || true` — should be empty.
5. `grep -n 'opensearch:2\.12' "$TARGET" || true` — should be empty.

For every match, present as an anomaly with `(c)ontinue / (s)kip / (a)bort`. `a` rolls back via `git restore -- "$TARGET"`.

## STEP 5: Diff review

Show diff: `git --no-pager diff --no-color -- "$TARGET"`. Print verbatim.

**Standalone mode**: AskUserQuestion: "Commit, push, and open PR? (y/N)". `y` → STEP 5.5 (LIVE only) → STEP 6. Anything else → `git restore` and exit cleanly.

**Chain mode**: skip the y/N prompt — proceed straight to STEP 6 (commit only).

## STEP 5.5: LIVE confirmation rail (standalone mode only when `<env>=live`)

In **chain mode**, this step is skipped — the orchestrator does the LIVE rail once before the first step.

In **standalone mode** for live envs:

1. Print: "This will upgrade a LIVE production instance: `<country>`. Type the country name exactly to confirm."
2. Compare to `<country>` exactly. Mismatch → `git restore -- "$TARGET"` and exit.

## STEP 6: Commit (and push/PR in standalone mode)

### Chain mode

1. Stage and commit on the chain branch:

   ```bash
   git add "$TARGET"
   git commit -m "Step 2.16→2.17 on <env>.<country> TOBE-17814"
   ```

2. Print: "Step 2.16→2.17 committed on `<CHAIN_BRANCH>`." Return.

### Standalone mode

1. `BRANCH=chore/upgrade-<env>-<country>-2.16-to-2.17`.
2. Check branch doesn't exist (locally and on origin). If it does, abort and `git restore`.
3. Create branch + commit:
   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade <env>.<country> from 2.16 to 2.17 TOBE-17814"
   ```
4. Push: `git push -u origin "$BRANCH"`.
5. Open PR:
   - GitHub: `gh pr create --base master --head "$BRANCH" --title "Upgrade <env>.<country> from 2.16 to 2.17" --body "<body>" --assignee @me --reviewer benoumemen`
   - Bitbucket: print manual link with reminder to set assignee + reviewer in the UI.
6. Print PR URL.
7. `git checkout master`.

## Reference: failure modes

Same taxonomy as 2.15→2.16, plus:

| Class | Examples | Outcome |
|---|---|---|
| Hard abort (no edits) | Legacy Wildfly Keycloak detected (DB_VENDOR/DB_ADDR present) | Print KC overhaul instructions, exit non-zero. |

## Reference: PR body template (standalone mode)

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`
from eRegistrations 2.16 to 2.17.

## Transformations applied

- Bumped every `unctad/<*>:BETA` image tag to `:2.17`.
- Renamed services (image keys only):
  - `unctad/eregbpafrontend` → `unctad/bpa-frontend`
  - `unctad/eregbpawebsocket` → `unctad/bpa-websocket`
  - `unctad/eregbpabackend` → `unctad/bpa-backend`
  - `unctad/eregcms` → `unctad/ds-backend`
  - `unctad/license-registry` → `unctad/gdb`
- Pinned floating `:DEV` tags to `:2.17` on `statistics-backend`, `statistics-frontend`, `ds-frontend`.
- Bumped `EREGISTRATIONS_VERSION` from `<expected_EV>` to `2.17`.
- Bumped `BUILD_TYPE` from `<expected_BT>` to `LIVE` (no-op for env=dev).
- Bumped Opensearch from `2.12.0` to `2.19.4`.

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against the rules.
- [ ] Smoke-test bpa-frontend renders, bpa-backend `/health` ok, ds-backend reachable, statistics dashboard loads.
- [ ] Verify Keycloak login flow still works (KC config unchanged, but `:BETA` → `:2.17` image tag).
```
