---
name: upgrade-2.15-to-2.16
description: >
  Upgrade a single eRegistrations instance under
  `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from 2.15 to 2.16, where
  `<env>` is one of dev/test/preview/prelive/live. Bumps unctad image tags from
  `:RC` to `:BETA`, version-bumps `EREGISTRATIONS_VERSION` and `BUILD_TYPE` env
  vars, renames `RESTHEART_URL` to `RESTHEART_PUBLIC_URL` on bpa-backend, adds
  GDB integration env vars, and adds `RESTHEART_PASSWORD` to camunda. Strict
  mode — aborts on anything unexpected. Env-aware anomaly thresholds for
  `BUILD_TYPE` and `EREGISTRATIONS_VERSION`. LIVE invocations require a
  retype-country confirmation rail before commit (skipped in chain mode — the
  orchestrator does it once up front). Two invocation modes: standalone (creates
  branch, pushes, opens PR) and chain mode (`CHAIN_MODE=1 CHAIN_BRANCH=<name>`,
  commits to orchestrator-managed branch, no push, no PR). Swarm-stack
  (docker-stack.yml) shape only — instances still on docker-compose.yml must
  run /docker-swarm-migration first.
license: UNCTAD-Internal
compatibility: Run from the eregistrations-v4 working tree on master (standalone) or on the orchestrator-supplied chain branch (chain mode), with a clean tracked tree. Requires an authenticated CLI for the host VCS in standalone mode (gh for GitHub origins; Bitbucket origins skip CLI PR creation and print a manual link).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(grep *), Bash(test *), Bash(ls *), Bash(basename *), Bash(dirname *), AskUserQuestion
metadata:
  version: "1.0.1"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country>] [<env>] [BACKUP_CONFIRMED=1] [CHAIN_MODE=1 CHAIN_BRANCH=<name>]"
  jira: "TOBE-17814"
---

# Upgrade an eRegistrations instance from 2.15 to 2.16

You are performing a mechanical eRegistrations 2.15 → 2.16 upgrade of a single instance. The target file is `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`, where `<env>` ∈ {dev, test, preview, prelive, live}. The upgrade applies a fixed set of transformations: image tag bumps from `:RC` to `:BETA`, env-var version bumps, and a handful of new/renamed env vars to enable the GDB integration that lands in 2.16. Operate in **strict mode**: any anomaly pauses for explicit user input, with `abort` as the default.

The skill is invoked as `/upgrade-2.15-to-2.16` with optional positional args (see *Arguments* below). It is also routed to by the `upgrade-eregistrations-instance` orchestrator when it detects a swarm-stack instance on `unctad/*:RC` images.

When the upgrade is approved, **standalone mode** commits on a fresh branch `chore/upgrade-<env>-<country>-2.15-to-2.16`, pushes it, and opens a pull request. **Chain mode** (orchestrator-invoked) skips branch creation, push, and PR — it commits a single step-scoped commit on the orchestrator-managed branch and returns.

## Arguments

The skill accepts up to four positional/flag tokens, whitespace-separated, in any order:

- `<env>` — one of `dev`, `test`, `preview`, `prelive`, `live` (lowercase).
- `<country>` — the folder name under `Conf-<UPPER_ENV>/compose/`, e.g. `syria2`, `colombia`, `lomasdezamora`.
- `BACKUP_CONFIRMED=1` — flag. Suppresses the STEP 1.5 backup prompt.
- `CHAIN_MODE=1` — flag. Switches to chain mode: orchestrator owns branch/push/PR. Requires `CHAIN_BRANCH` to also be set.
- `CHAIN_BRANCH=<branch>` — the branch the orchestrator already created and switched to. Sub-skill commits here.

Tokenizer rules:
- Whitespace-split.
- For each token: if it matches `^[A-Z_]+=.+$`, treat as a `KEY=VALUE` flag and store; if lowercased it equals one of the env keywords, set `<env>`; otherwise it's `<country>`.
- Unknown `KEY=VALUE` flags warn ("Unknown flag `<token>`, ignoring.") but do not abort.

Missing positional values trigger AskUserQuestion prompts in STEP 1. If `<country>` was supplied via args, validation is single-shot (no retry loop).

Env → directory mapping:

| `<env>` | `<UPPER_ENV>` | Directory |
|---|---|---|
| dev | `DEV` | `Conf-DEV/compose/` |
| test | `TEST` | `Conf-TEST/compose/` |
| preview | `PREVIEW` | `Conf-PREVIEW/compose/` |
| prelive | `PRELIVE` | `Conf-PRELIVE/compose/` |
| live | `LIVE` | `Conf-LIVE/compose/` |

## Scope (intentionally narrow)

- **In scope:** a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` whose `unctad/*` images are pinned at `:RC` (the 2.15 tag convention).
- **Out of scope:** instances still on `docker-compose.yml` (refuse and point at `/docker-swarm-migration`), Coolify-managed instances, simultaneous upgrades of multiple instances, version pairs other than 2.15 → 2.16.

If the target instance has only `docker-compose.yml` (no `docker-stack.yml`), abort with: "`<country>` is still on docker-compose.yml. Run `/docker-swarm-migration` first to convert the instance to swarm, then re-run this skill."

## STEP 0: Pre-flight git checks

Before doing anything else, verify the repository is in a state where the upgrade can proceed.

**Standalone mode** (no `CHAIN_MODE=1`):

1. **Working tree is a git repo at the repo root.** Run `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Current branch is `master`.** Run `git rev-parse --abbrev-ref HEAD`. If not `master`, abort: "Refusing to run on branch <branch>. Switch to master first."
3. **No staged or modified tracked files.** Run `git status --porcelain --untracked-files=no`. If non-empty, abort and print: "There are staged or modified tracked files. Resolve the changes below first." followed by the same output.
4. **Origin host detected, CLI authenticated.** If the orchestrator already set `HOST` in conversation state, reuse it. Otherwise resolve it now: `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. The skill will skip CLI-based PR creation and print a manual Bitbucket URL after push.
   - Otherwise abort: "Unsupported origin host: <url>."
5. **`master` is in sync with origin.** Run `git pull --ff-only origin master`. On failure, abort and print the git error verbatim.

**Chain mode** (`CHAIN_MODE=1`):

1. **Working tree is a git repo at the repo root.** Same as standalone.
2. **Currently on the orchestrator-supplied chain branch.** Run `git rev-parse --abbrev-ref HEAD`. If it doesn't equal `<CHAIN_BRANCH>`, abort: "Chain mode expected branch `<CHAIN_BRANCH>` but on `<actual>`. Orchestrator state inconsistent."
3. **No staged or modified tracked files.** Same as standalone (the orchestrator should have ensured this between steps).
4. **Skip host detection and pull** — orchestrator did both already.

When pre-flight passes, proceed to STEP 1.

## STEP 1: Resolve env, country, target

1. **Resolve `<env>`.** If supplied via args, use it. Otherwise AskUserQuestion: "Which environment? dev / test / preview / prelive / live." Lowercase, validate. Two-strikes invalid → abort.

2. **Compute `<UPPER_ENV>`** from the table above.

3. **Verify eregistrations-v4 shape.** Run `test -d "Conf-<UPPER_ENV>/compose"`. If missing, abort: "`Conf-<UPPER_ENV>/compose/` does not exist."

4. **Find candidates.** Run:

   ```bash
   for f in Conf-<UPPER_ENV>/compose/*/docker-stack.yml; do
     if grep -q 'unctad/.*:RC' "$f"; then
       echo "$(basename "$(dirname "$f")")"
     fi
   done | sort
   ```

5. **No candidates found.** If zero lines: "Nothing to upgrade — no `Conf-<UPPER_ENV>` swarm-stack instance contains `unctad/*:RC` images. Note: instances still on `docker-compose.yml` must run `/docker-swarm-migration` first." Exit 0.

6. **Resolve `<country>`.**
   - If supplied via args: validate against candidates list. Invalid → single-shot abort.
   - If not supplied: list candidates, ask "Which `<env>` instance? Type the country folder name." Two-strikes invalid → abort.

7. **Confirm target file exists.** Compute `TARGET=Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`. Run `test -f "$TARGET"`. If missing, abort.

8. Save state for the rest of the run: `<env>`, `<UPPER_ENV>`, `<country>`, `TARGET`.

## STEP 1.5: Backup confirmation

If `BACKUP_CONFIRMED=1` was passed (orchestrator-routed and chain-mode invocations always set this), skip this step.

Otherwise AskUserQuestion: "Is the current state of `<env>`/`<country>` recoverable (snapshot, prior tag, manual export)? (y/N)"

- `y` (case-insensitive) → STEP 2.
- `N` or empty → abort: "Resolve backups before re-running."

## STEP 2: Pre-transformation strict scan

Compute env-aware anomaly thresholds:

| `<env>` | expected `BUILD_TYPE` | expected `EREGISTRATIONS_VERSION` |
|---|---|---|
| dev | `DEV` | `DEV` |
| test, preview, prelive, live | `RC` | `2.15` |

Print: "Env: `<env>`. Expected `BUILD_TYPE=<expected_BT>`. Expected `EREGISTRATIONS_VERSION=<expected_EV>`."

Scan `<TARGET>` for **anomalies**. Each pauses for `(c)ontinue / (s)kip / (a)bort` (default abort, empty = abort). `c` applies the relevant rule to this occurrence; `s` leaves untouched (remembered for the kind); `a` exits without edits.

**Anomaly kinds:**

1. **Unexpected unctad image tag.** A line matching `image:\s*unctad/[^:]+:[^ ]+` whose tag is not in `{RC, BETA, DEV}`. The `:RC` images are the upgrade targets; `:BETA` indicates a partial prior upgrade; `:DEV` is the convention for country-specific mule images and is expected (typical answer: `s`).

2. **Already-2.16 services.** Any unctad service already on `:BETA`. Suggests partial upgrade.

3. **Unexpected `EREGISTRATIONS_VERSION` value.** Any `EREGISTRATIONS_VERSION=` line whose RHS (after stripping quotes) is not `<expected_EV>`.

4. **Unexpected `BUILD_TYPE` value.** Any `BUILD_TYPE=` line whose RHS (after stripping quotes) is not `<expected_BT>`.

5. **Missing expected service blocks.** If the file lacks `bpa-frontend:`, `bpa-backend:`, or `camunda:` service blocks (rule sites). Print the missing names — typically a country-specific compose variant. Skipping means the corresponding env-var rules below silently no-op.

If no anomalies: "No anomalies. Applying transformations." and proceed.

## STEP 3: Apply the transformations

Edit `<TARGET>` in place. Preserve indentation and line endings exactly. Apply rules in order; each operates on the file produced by the previous.

### Image tag rules

**Rule 1 — Bump `unctad/*:RC` to `unctad/*:BETA`.**
For every line matching `^(\s*)image:\s*unctad/([^:\s]+):RC\s*$`, replace `:RC` with `:BETA`. Keep leading whitespace and image name verbatim.

**Rule 2 — Special-case `unctad/license-registry`.**
If a line matches `^(\s*)image:\s*unctad/license-registry:RC\s*$`, replace it with `:DEV` (not `:BETA`). This is the historical pattern from commits 9d0a1315 and 57a92838 — license-registry follows the country-image `:DEV` convention rather than the platform `:BETA` cycle. After Rule 1 you may already see `:BETA` here; if so, Rule 2 is a no-op for that line.

### Env-var rules on `bpa-frontend`

Locate the `bpa-frontend:` service block (indent 2). All env-list rules below operate **only inside its `environment:` list**.

**Rule 3 — Bump `EREGISTRATIONS_VERSION`.**
Replace any list item whose stripped content is `- EREGISTRATIONS_VERSION=<expected_EV>` (or quoted variant) with `- EREGISTRATIONS_VERSION=2.16`. Preserve original indentation, dash, and quoting style.

**Rule 4 — Bump `BUILD_TYPE`.**
Replace any list item whose stripped content is `- BUILD_TYPE=<expected_BT>` (or quoted variant) with `- BUILD_TYPE=BETA`. For env=dev, the threshold is `DEV` and the replacement is `BETA` too — dev is treated like other envs for this var in 2.16 (per commits 9d0a1315/57a92838).

**Rule 5 — Ensure `USE_NEW_DS=true` is present.**
If no list item already starts with `USE_NEW_DS=` (with or without surrounding quotes), append `- USE_NEW_DS=true` to the env list, matching the indentation of the surrounding items. If present with a value other than `true`, raise it as a Rule 5 anomaly: print the existing line and ask `(c)ontinue (overwrite to true) / (s)kip / (a)bort`.

**Rule 6 — Ensure `GDB_URL` is present.**
If no list item already starts with `GDB_URL=`, append `- GDB_URL=https://gdb.$YOUR_DOMAIN_NAME/` (preserving env-list indentation and `$VAR` interpolation style — note the trailing `/`). If present, leave as-is.

### Env-var rules on `bpa-backend`

Locate the `bpa-backend:` service block.

**Rule 7 — Rename `RESTHEART_URL` to `RESTHEART_PUBLIC_URL`.**
Find the env-list item matching `RESTHEART_URL=<value>` (with or without quotes). Replace just the var name with `RESTHEART_PUBLIC_URL`, keeping `<value>` and quoting style intact. If both `RESTHEART_URL` and `RESTHEART_PUBLIC_URL` exist already, raise an anomaly.

**Rule 8 — Ensure `REGISTRY_SERVICE_PUBLIC_URL` is present.**
If no list item starts with `REGISTRY_SERVICE_PUBLIC_URL=`, append `- "REGISTRY_SERVICE_PUBLIC_URL=https://gdb.$YOUR_DOMAIN_NAME"` (use the same quoting style as the surrounding bpa-backend env items — most use double-quotes).

**Rule 9 — Ensure `RESTHEART_USERNAME` is present.**
If no list item starts with `RESTHEART_USERNAME=`, append `- "RESTHEART_USERNAME=$RESTHEART_USER"`.

### Env-var rules on `camunda`

Locate the `camunda:` service block.

**Rule 10 — Ensure `RESTHEART_PASSWORD` is present in camunda env.**
If no list item starts with `RESTHEART_PASSWORD=`, append `- "RESTHEART_PASSWORD=$RESTHEART_PASSWORD"` to camunda's environment list.

### Env-var rules on `ds-backend` (or legacy `ereg-cms-frontend`)

Locate the DS-side service. In 2.15 the service is named **`ereg-cms-frontend`** (rename to `ds-backend` happens in 2.16 → 2.17). Apply rules to whichever name is present.

**Rule 11 — Ensure `EREGISTRATIONS_VERSION=2.16` and `BUILD_TYPE=BETA` are present in DS env.**
If a `EREGISTRATIONS_VERSION=` item already exists, replace its value to `2.16` (raising an anomaly if the source value isn't `<expected_EV>`). Otherwise append `- "EREGISTRATIONS_VERSION=2.16"`. Same logic for `BUILD_TYPE=BETA`.

### Mule changes

**Rule 12 — Ensure mule depends_on includes dataweave.**
Locate the `mule:` service block. If it has no `depends_on:` block, append:
```
    depends_on:
      - "dataweave"
```
with the matching indentation. If `depends_on:` exists but doesn't list `dataweave`, raise an anomaly. Do not strip activemq from depends_on here — that change is part of 2.16 → 2.17.

When all rules are applied, proceed to STEP 4.

## STEP 4: Post-transformation safety scan

After applying the rules, scan the modified `<TARGET>` for any remaining surprises that would suggest the upgrade is incomplete:

1. `grep -n 'unctad/[^:]\+:RC' "$TARGET" || true` — should be empty (Rule 1 catches all).
2. `grep -n 'EREGISTRATIONS_VERSION=2\.15' "$TARGET" || true` — should be empty.
3. `grep -n 'BUILD_TYPE=RC' "$TARGET" || true` — should be empty.

For every match, present it as an anomaly with `(c)ontinue / (s)kip / (a)bort`. `a` rolls back via `git restore -- "$TARGET"` and exits.

## STEP 5: Diff review

Show diff: `git --no-pager diff --no-color -- "$TARGET"`. Print verbatim.

**Standalone mode**: AskUserQuestion: "Commit, push, and open PR? (y/N)". `y` → STEP 5.5 (LIVE only) → STEP 6. Anything else → `git restore -- "$TARGET"` and exit cleanly.

**Chain mode**: skip the y/N prompt — the orchestrator already gathered intent. Proceed straight to STEP 6 (commit only). The orchestrator handles the between-step pause and the squash + PR at the end of the chain.

## STEP 5.5: LIVE confirmation rail (standalone mode only when `<env>=live`)

In **chain mode**, this step is skipped — the orchestrator does the LIVE retype-country rail once before the first step and threads `BACKUP_CONFIRMED=1` plus the chain branch through.

In **standalone mode** for live envs:

1. Print: "This will upgrade a LIVE production instance: `<country>`. Type the country name exactly to confirm."
2. Read trimmed answer. Compare to `<country>` exactly (case-sensitive).
3. Mismatch → `git restore -- "$TARGET"` and exit cleanly: "Country name mismatch. Aborted."

## STEP 6: Commit (and push/PR in standalone mode)

### Chain mode

1. **Stage and commit on the chain branch.**

   ```bash
   git add "$TARGET"
   git commit -m "Step 2.15→2.16 on <env>.<country> TOBE-17814"
   ```

2. Print: "Step 2.15→2.16 committed on `<CHAIN_BRANCH>`." Return control to the orchestrator. Do not push, do not open a PR.

### Standalone mode

1. **Compute branch name.** `BRANCH=chore/upgrade-<env>-<country>-2.15-to-2.16`.

2. **Check branch doesn't exist** (locally and on origin). If it does, abort and `git restore -- "$TARGET"`.

3. **Create branch and commit.**

   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade <env>.<country> from 2.15 to 2.16 TOBE-17814"
   ```

4. **Push.** `git push -u origin "$BRANCH"`. On rejection: leave the local commit, print recovery hint.

5. **Open PR.**
   - GitHub: `gh pr create --base master --head "$BRANCH" --title "Upgrade <env>.<country> from 2.15 to 2.16" --body "<body>"`
   - Bitbucket: skip CLI; print the manual link in the format `https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master`.

6. **Print the PR URL.**

7. **Switch back to master.** `git checkout master`.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort (no edits) | not in git repo; not on master (standalone) / not on chain branch (chain mode); dirty tree; gh missing on GitHub origin in standalone mode; pull fails; `Conf-<UPPER_ENV>/compose/` missing; user mistypes country twice (interactive); country supplied via args is invalid; target file missing; branch already exists locally or on origin (standalone) | Print failure reason, exit non-zero. |
| Clean exit (no edits) | candidate scan finds zero files; selected file has zero `unctad/*:RC` lines; user said "N" to backup confirmation | Print "Nothing to upgrade" / "<country> is already on 2.16", exit 0. |
| Soft pause | any anomaly (pre-scan, post-scan, rule-specific); diff-review answered N (standalone only); LIVE retype-country mismatch (standalone only) | Wait for input; on abort/restore/mismatch, run `git restore -- "$TARGET"` and exit cleanly. |

## Reference: PR body template (standalone mode)

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`
from eRegistrations 2.15 to 2.16.

## Transformations applied

- Bumped every `unctad/<*>:RC` image tag to `:BETA` (license-registry → `:DEV`).
- Bumped `EREGISTRATIONS_VERSION` from `<expected_EV>` to `2.16` on bpa-frontend and DS service.
- Bumped `BUILD_TYPE` from `<expected_BT>` to `BETA` on bpa-frontend and DS service.
- Ensured `USE_NEW_DS=true` and `GDB_URL=https://gdb.$YOUR_DOMAIN_NAME/` on bpa-frontend.
- Renamed `RESTHEART_URL` → `RESTHEART_PUBLIC_URL` on bpa-backend.
- Added `REGISTRY_SERVICE_PUBLIC_URL` and `RESTHEART_USERNAME` on bpa-backend.
- Added `RESTHEART_PASSWORD` on camunda.
- Ensured mule `depends_on: ["dataweave"]`.

(`<expected_EV>` and `<expected_BT>` are `DEV` for env=dev, `2.15`/`RC` otherwise.)

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against the rules in this skill.
- [ ] Smoke-test bpa-frontend renders, bpa-backend `/health` ok, restheart still reachable.
```
