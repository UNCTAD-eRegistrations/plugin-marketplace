---
name: upgrade-2.17-to-2.18
description: >
  Upgrade a single eRegistrations instance under
  `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from 2.17 to 2.18, where
  `<env>` is one of dev/test/preview/prelive/live. Bumps standard unctad images,
  swaps the minio image and healthcheck, and removes deprecated env vars. Strict
  mode — aborts on anything unexpected. Env-aware anomaly thresholds for
  `BUILD_TYPE` and `EREGISTRATIONS_VERSION`. LIVE invocations require a
  retype-country confirmation rail before commit (skipped in chain mode — the
  orchestrator does it once up front). Two invocation modes: standalone (creates
  branch, pushes, opens a pull request against master via gh on GitHub origins,
  manual link on Bitbucket origins) and chain mode (`CHAIN_MODE=1
  CHAIN_BRANCH=<name>`, commits to orchestrator-managed branch, no push, no PR —
  the orchestrator squashes the chain and ships a single PR). Swarm-stack
  (docker-stack.yml) shape only — instances still on docker-compose.yml must run
  /docker-swarm-migration first.
license: UNCTAD-Internal
compatibility: Run from the eregistrations-v4 working tree on master with a clean tracked tree. Requires an authenticated CLI for the host VCS (gh for GitHub origins; Bitbucket origins skip CLI PR creation and print a manual link).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(grep *), Bash(test *), Bash(ls *), Bash(basename *), Bash(dirname *), AskUserQuestion
metadata:
  version: "1.2.0"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country>] [<env>] [BACKUP_CONFIRMED=1] [CHAIN_MODE=1 CHAIN_BRANCH=<name>]"
  jira: "TOBE-17814"
---

# Upgrade an eRegistrations instance from 2.17 to 2.18

You are performing a mechanical eRegistrations 2.17 → 2.18 upgrade of a single instance. The target file is `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`, where `<env>` ∈ {dev, test, preview, prelive, live}. The upgrade applies five fixed transformations (image bumps, minio swap, healthcheck rewrite, two env-var deletions). The five rules are environment-invariant; only the **anomaly thresholds** in STEP 2 vary by env. Operate in **strict mode**: any anomaly pauses for explicit user confirmation, with `abort` as the default.

The skill is invoked as `/upgrade-2.17-to-2.18` with optional positional args (see *Arguments* below). It is also routed to by the `upgrade-eregistrations-instance` orchestrator when it detects a swarm-stack instance on `unctad/*:2.17` images.

When the upgrade is approved, the skill commits on a fresh branch `chore/upgrade-<env>-<country>-2.17-to-2.18`, pushes it, and opens a pull request against `master` via `gh`.

## Arguments

The skill accepts up to five positional/flag tokens, whitespace-separated, in any order:

- `<env>` — one of `dev`, `test`, `preview`, `prelive`, `live` (lowercase). Disambiguated by exact keyword match.
- `<country>` — the folder name under `Conf-<UPPER_ENV>/compose/`, e.g. `kenya`, `lesotho`, `colombia`. Anything that isn't an env keyword and isn't a `KEY=VALUE` flag is treated as `<country>`.
- `BACKUP_CONFIRMED=1` — flag (any other value of `BACKUP_CONFIRMED` is treated as not-confirmed). Suppresses the STEP 1.5 backup prompt — used by the orchestrator, which already asked.
- `CHAIN_MODE=1` — flag. Switches to chain mode: the orchestrator owns branch creation, push, and PR. Sub-skill commits a single step-scoped commit on `<CHAIN_BRANCH>` and returns. Implies `BACKUP_CONFIRMED=1`. Skips the STEP 5 commit-or-not prompt and STEP 5.5 LIVE retype-country rail (orchestrator did the rail once before the first step).
- `CHAIN_BRANCH=<branch>` — required when `CHAIN_MODE=1`. The branch the orchestrator already created and switched to. Sub-skill verifies the working tree is on this branch in STEP 0 and commits here in STEP 6.

Tokenizer rules:
- Whitespace-split.
- For each token: if it matches `^[A-Z_]+=.+$`, treat as a `KEY=VALUE` flag and store; if lowercased it equals one of the env keywords, set `<env>`; otherwise it's `<country>`.
- Unknown `KEY=VALUE` flags warn ("Unknown flag `<token>`, ignoring.") but do not abort.

Missing positional values trigger AskUserQuestion prompts in STEP 1. If `<country>` was supplied via args, validation is single-shot (no retry loop) — orchestrator-routed invocations pre-validate, so a typo here means a config bug, not user fumble. Interactive STEP 1 keeps the two-strikes loop.

Env → directory mapping:

| `<env>` | `<UPPER_ENV>` | Directory |
|---|---|---|
| dev | `DEV` | `Conf-DEV/compose/` |
| test | `TEST` | `Conf-TEST/compose/` |
| preview | `PREVIEW` | `Conf-PREVIEW/compose/` |
| prelive | `PRELIVE` | `Conf-PRELIVE/compose/` |
| live | `LIVE` | `Conf-LIVE/compose/` |

## Scope (intentionally narrow)

- **In scope:** a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` whose `unctad/*` images are pinned at `:2.17`.
- **Out of scope:** instances still on `docker-compose.yml` (refuse and point at `/docker-swarm-migration`), Coolify-managed instances, simultaneous upgrades of multiple instances, version pairs other than 2.17 → 2.18.

If the target instance has only `docker-compose.yml` (no `docker-stack.yml`), abort with: "`<country>` is still on docker-compose.yml. Run `/docker-swarm-migration` first to convert the instance to swarm, then re-run this skill." The 2.17 → 2.18 upgrade flow assumes the swarm migration has already happened — see TOBE-17731.

## STEP 0: Pre-flight git checks

Before doing anything else, verify the repository is in a state where the upgrade can proceed. Run these checks in order. If any fails, print the failure reason and stop — do not proceed to STEP 1 and do not modify any files. STEP 0 is git-only; the eregistrations-v4 directory shape check happens in STEP 1 once `<env>` is known. If invoked standalone, STEP 1's directory check is the only eregistrations-v4 shape gate.

The branch and pull checks differ between standalone and chain modes:

**Standalone mode** (no `CHAIN_MODE=1`):

1. **Working tree is a git repo at the repo root.** Run `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Current branch is `master`.** Run `git rev-parse --abbrev-ref HEAD`. If the result is not exactly `master`, abort and print: "Refusing to run on branch <branch-name>. Switch to master first."
3. **No staged or modified tracked files.** Run `git status --porcelain --untracked-files=no`. If the output is non-empty, abort and print: "There are staged or modified tracked files. Resolve the changes below first." followed by the same output. Untracked files are ignored — the skill only `git add`s the single target file, so stray untracked files cannot be bundled into the upgrade commit.
4. **Origin host detected, CLI authenticated.** If the orchestrator already set `HOST` in conversation state (it does so in its own pre-flight), reuse that value. Otherwise resolve it now: run `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. The skill will skip CLI-based PR creation and print a manual Bitbucket URL after push.
   - Otherwise abort: "Unsupported origin host: <url>."
5. **`master` is in sync with origin.** Run `git pull --ff-only origin master`. If it fails, abort and print the git error verbatim. Suggest: "Resolve divergence (e.g. `git pull --rebase`) and re-run."

**Chain mode** (`CHAIN_MODE=1`, requires `CHAIN_BRANCH=<branch>`):

1. **Working tree is a git repo at the repo root.** Same check as standalone.
2. **Currently on `<CHAIN_BRANCH>`.** Run `git rev-parse --abbrev-ref HEAD`. If the result is not exactly `<CHAIN_BRANCH>`, abort: "Chain mode expected branch `<CHAIN_BRANCH>` but on `<actual>`. Orchestrator state inconsistent."
3. **No staged or modified tracked files.** Same check as standalone — the orchestrator should have ensured a clean tree between steps.
4. **Skip host detection and pull.** The orchestrator already validated both before creating the chain branch.

When pre-flight passes, proceed to STEP 1.

## STEP 1: Resolve env, country, target

Resolve `<env>` and `<country>`, verify the working tree shape, build the candidate list, and pick the instance to upgrade.

1. **Resolve `<env>`.** If supplied via args, use it. Otherwise AskUserQuestion: "Which environment? dev / test / preview / prelive / live." Lowercase the answer and validate against the keyword set. Two-strikes invalid → abort.

2. **Compute `<UPPER_ENV>`** from the env→directory mapping table above.

3. **Verify eregistrations-v4 shape.** Run `test -d "Conf-<UPPER_ENV>/compose"`. If missing, abort: "`Conf-<UPPER_ENV>/compose/` does not exist — this doesn't look like the eregistrations-v4 working tree, or the env is not configured in this repo."

4. **Find candidates.** Run:

   ```bash
   for f in Conf-<UPPER_ENV>/compose/*/docker-stack.yml; do
     if grep -q 'unctad/.*:2\.17' "$f"; then
       echo "$(basename "$(dirname "$f")")"
     fi
   done | sort
   ```

5. **No candidates found.** If the loop produced zero lines, print: "Nothing to upgrade — no `Conf-<UPPER_ENV>` swarm-stack instance contains `unctad/*:2.17`. Note: instances still on `docker-compose.yml` must run `/docker-swarm-migration` first to convert to swarm before this skill applies." Exit 0. Do not abort.

6. **Resolve `<country>`.**
   - If supplied via args: validate it appears in the candidate list. If not, print "`<country>` is not a valid choice for env=`<env>`. Eligible: <list>." and abort cleanly (single-shot, no retry — args came from a caller, retrying is a typo-recovery affordance for interactive use).
   - If not supplied: print one country per line prefixed with `- `, then ask: "Which `<env>` instance? Type the country folder name." Trim whitespace. If invalid, reprint the candidate list and ask again. On the second consecutive invalid answer, abort: "No valid instance picked, exiting."

7. **Confirm the target file exists.** Compute `TARGET=Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`. Run `test -f "$TARGET"`. If missing, abort: "$TARGET not found." (This should not happen if the candidate list was built correctly.)

8. **Save state for the rest of the run:** `<env>`, `<UPPER_ENV>`, `<country>`, `TARGET`.

Proceed to STEP 1.5.

## STEP 1.5: Backup confirmation

If `BACKUP_CONFIRMED=1` was passed in args (orchestrator-routed and chain-mode invocations always set this), skip this step and proceed to STEP 2.

Otherwise AskUserQuestion: "Is the current state of `<env>`/`<country>` recoverable (snapshot, prior tag, manual export)? (y/N)"

- `y` (case-insensitive) — proceed to STEP 2.
- `N` or empty — abort cleanly: "Resolve backups before re-running. The upgrade itself is mechanical, but rollback isn't free."

## STEP 2: Pre-transformation strict scan

Compute the env-aware anomaly thresholds:

| `<env>` | expected `BUILD_TYPE` | expected `EREGISTRATIONS_VERSION` |
|---|---|---|
| dev | `DEV` | `DEV` |
| test, preview, prelive, live | `LIVE` | `2.17` |

Print one line stating the thresholds in effect: "Env: `<env>`. Expected `BUILD_TYPE=<expected_BT>`. Expected `EREGISTRATIONS_VERSION=<expected_EV>`." This makes a wrong-env mistake surface immediately as a wall of anomalies.

Before applying any edits, scan `<TARGET>` for **anomalies**. Each anomaly pauses for explicit user input. Do not silently proceed.

For every anomaly, print:

```
ANOMALY: <kind>
  File: <TARGET>:<line-number>
  Line: <verbatim-line>
  (c)ontinue / (s)kip / (a)bort   [default: abort]
```

Read the user's single-character answer. Empty input means abort. The behaviour:

- `c` — apply the relevant transformation rule to this occurrence.
- `s` — leave this occurrence untouched. Skipped anomalies survive into STEP 4's post-scan as a fail-safe; if they leave a `2.17` token behind, the user gets a second chance to handle them.
- `a` — stop the skill, no edits made.

If the user picks `s` for an anomaly kind, remember the choice for that kind only — do not re-prompt for further occurrences of the same kind in the same run.

**The anomaly kinds (run all five scans, collect the list, then prompt one anomaly at a time):**

1. **Mixed unctad versions.** A line matching `image:\s*unctad/[^:]+:[^ ]+` whose tag is neither `2.17` nor `2.18`. Examples: `unctad/mule3-kenya:DEV`, `unctad/mule4-kenya:DEV`, `unctad/cas-backend:beta`, `unctad/bpa-backend:3.6.8-53`. Country mule images on `:DEV` are expected and the user typically answers `s`.

2. **Already-2.18 unctad services.** A line matching `image:\s*unctad/[^:]+:2\.18`. This usually means a previous partial upgrade. Flag every occurrence.

3. **Non-standard minio.** Either:
   - the file contains no `minio:` service block (search for `^  minio:` at indent 2), OR
   - the `minio:` block's `image:` is not exactly `image: minio/minio:latest`, OR
   - the `minio:` block's `test:` line is not exactly the expected `test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]` (allow whitespace variation around brackets and commas).

4. **Unexpected `EREGISTRATIONS_VERSION` value.** Any line matching `EREGISTRATIONS_VERSION=` whose RHS, after stripping surrounding double quotes, is not `<expected_EV>`.

5. **Unexpected `BUILD_TYPE` value.** Any line matching `BUILD_TYPE=` whose RHS, after stripping surrounding double quotes, is not `<expected_BT>`.

If no anomalies are detected, print "No anomalies. Applying transformations." and proceed.

If anomalies were detected and the user resolved them all (no `a` answer), proceed to STEP 3 and apply the transformations only to the expected occurrences (i.e. `unctad/*:2.17` lines, the standard minio image/healthcheck, exactly `EREGISTRATIONS_VERSION=<expected_EV>`, and exactly `BUILD_TYPE=<expected_BT>`). Do not auto-rewrite anomalous lines.

## STEP 3: Apply the five transformations

Edit `<TARGET>` in place. Apply each rule across the whole file. Preserve indentation and line endings exactly. Do not reformat anything else.

**Rule 1 — Bump unctad image tags.**
For every line matching `^(\s*)image:\s*unctad/([^:\s]+):2\.17\s*$`, replace `:2.17` with `:2.18`. Keep the leading whitespace and the image name verbatim. Country-specific images on non-`:2.17` tags (e.g. `unctad/mule3-kenya:DEV`) do not match and are not touched.

**Rule 2 — Swap minio image.**
Replace the line `    image: minio/minio:latest` (within the `minio:` service block) with `    image: pgsty/minio:latest`. Preserve the existing indentation (two-space, four-space, however it appears).

**Rule 3 — Replace minio healthcheck.**
Within the `minio:` service block, find the `test:` line that contains `["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]` and replace it with `test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/9000'"]`. Preserve the leading indentation of the original `test:` line.

**Rule 4 — Remove `EREGISTRATIONS_VERSION=<expected_EV>`.**
Delete every line whose stripped content is exactly `- EREGISTRATIONS_VERSION=<expected_EV>` or `- "EREGISTRATIONS_VERSION=<expected_EV>"` (with or without surrounding double quotes around the value). For test/preview/prelive/live this is `2.17`; for dev this is `DEV`. Typical sites: `bpa-frontend` and `ds-backend`. Remove the entire line including its leading whitespace and trailing newline — do not leave a blank line behind.

**Rule 5 — Remove `BUILD_TYPE=<expected_BT>`.**
Delete every line whose stripped content is exactly `- BUILD_TYPE=<expected_BT>` or `- "BUILD_TYPE=<expected_BT>"`. For test/preview/prelive/live this is `LIVE`; for dev this is `DEV`. Same line-removal rules as Rule 4.

**Apply order:** rules 1 → 2 → 3 → 4 → 5. Each rule operates on the file produced by the previous rule.

**Tooling.** Apply the edits using your file-editing tool of choice (Edit/Write). Do not shell out to `sed -i` — macOS and Linux disagree on the `-i` flag, and the skill must work on both.

When all five rules are applied, proceed to STEP 4.

## STEP 4: Post-transformation safety scan

After applying the five rules, scan the modified `<TARGET>` for any remaining `2.17` token.

Run:

```bash
grep -n '2\.17' "$TARGET" || true
```

For every match, present it as an anomaly with the same `(c)ontinue / (s)kip / (a)bort` prompt. `c` here means "leave it as is, this `2.17` is intentional"; `s` is identical (anomaly is left untouched); `a` rolls back: run `git restore -- "$TARGET"` and exit.

The standard upgrade should leave **zero** `2.17` matches. A non-zero count usually indicates either a comment, a non-standard env value, or a missed image line — pausing for the user is correct.

When the user has resolved all matches (or there were none), proceed to STEP 5.

## STEP 5: Diff review

Show the user the diff and ask for explicit approval before committing.

1. Run `git --no-pager diff --no-color -- "$TARGET"` and print the output verbatim (do not summarise).

**Standalone mode:**

2. Ask: "Commit, push, and open PR? (y/N)"
3. Read the answer.
   - `y` (case-insensitive) — if `<env>=live`, proceed to STEP 5.5. Otherwise, proceed to STEP 6.
   - Anything else — run `git restore -- "$TARGET"` and exit cleanly: "Aborted. No commit made."

**Chain mode:**

2. Skip the y/N prompt — the orchestrator already gathered intent for the whole chain. Proceed straight to STEP 6 (commit only). Skip STEP 5.5 too — the orchestrator does the LIVE retype-country rail once before the first step.

## STEP 5.5: LIVE confirmation rail (standalone mode only when `<env>=live`)

In **chain mode**, this step is skipped — the orchestrator does the LIVE retype-country rail once before the first step in the chain.

In **standalone mode** for live envs, require a retype-country confirmation as a final guardrail before commit:

1. Print:
   ```
   This will upgrade a LIVE production instance: <country>.
   Type the country name exactly as it appears in <TARGET> to confirm — anything else aborts.
   ```
2. Read the user's answer. Trim whitespace.
3. Compare to `<country>` exactly (case-sensitive — country folders are lowercase by convention).
   - Match → proceed to STEP 6.
   - Mismatch → run `git restore -- "$TARGET"` and exit cleanly: "Country name mismatch. Aborted. No commit made."

## STEP 6: Commit (and push/PR in standalone mode)

### Chain mode

In chain mode, the orchestrator owns the branch lifecycle (creation, push, PR). The sub-skill only commits.

1. **Stage and commit on `<CHAIN_BRANCH>`.**

   ```bash
   git add "$TARGET"
   git commit -m "Step 2.17→2.18 on <env>.<country> TOBE-17814"
   ```

2. Print: "Step 2.17→2.18 committed on `<CHAIN_BRANCH>`." Return control to the orchestrator. Do not push, do not open a PR, do not switch branches.

### Standalone mode

1. **Compute the branch name.** `BRANCH=chore/upgrade-<env>-<country>-2.17-to-2.18` (using the resolved env and country folder name).

2. **Check the branch does not already exist.**
   - Local: `git rev-parse --verify "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort: "Branch $BRANCH already exists locally. Resolve manually."
   - Remote: `git ls-remote --exit-code --heads origin "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort the same way.
   - On either failure, run `git restore -- "$TARGET"` so the working tree is clean again before exiting.

3. **Create the branch and commit.**

   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade <env>.<country> from 2.17 to 2.18 TOBE-17814"
   ```

4. **Push the branch.**

   ```bash
   git push -u origin "$BRANCH"
   ```

   If the push is rejected, leave the local commit in place, return to `master` (`git checkout master`), and tell the user: "Push rejected. The local branch $BRANCH still has the commit; investigate and push manually."

5. **Open the PR — branch on `HOST`.**

   Compose the body using the template in the *PR body template* reference at the bottom of this skill. Replace `<env>`, `<UPPER_ENV>`, `<country>`, `<expected_EV>`, `<expected_BT>`, and `<skipped>` (the list of anomaly kinds the user answered `s` for, if any — empty bullet "(none)" if zero).

   - If `HOST=github`:

     ```bash
     gh pr create \
       --base master \
       --head "$BRANCH" \
       --title "Upgrade <env>.<country> from 2.17 to 2.18" \
       --body "<body>" \
       --assignee @me \
       --reviewer benoumemen
     ```

     If `gh pr create` fails, leave the branch pushed and the local commit in place. Print the gh error and tell the user: "PR creation failed; the branch is pushed. Open the PR manually."

   - If `HOST=bitbucket`: skip CLI PR creation. Parse `<workspace>/<repo>` from `git remote get-url origin` (formats `git@bitbucket.org:<workspace>/<repo>.git` or `https://bitbucket.org/<workspace>/<repo>.git`) and print:

     ```
     Branch pushed: $BRANCH
     Open the PR via the Bitbucket web UI at:
     https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master
     Set the assignee to yourself and the reviewer to `benoumemen` in the Bitbucket UI.
     ```

6. **Print the PR URL** — the URL returned by `gh pr create` (GitHub) or the constructed Bitbucket URL on its own line.

7. **Switch back to master.**

   ```bash
   git checkout master
   ```

8. Done.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort (no edits made) | not in git repo; not on master; dirty tree; `gh` missing on a GitHub origin; unsupported origin host; pull fails; `Conf-<UPPER_ENV>/compose/` missing; user mistypes country twice (interactive only); country supplied via args is invalid; target file missing; branch already exists locally or on origin | Print failure reason, exit non-zero. |
| Clean exit (no edits made) | candidate scan finds zero files; selected file has zero `unctad/*:2.17` lines; user said "N" to backup confirmation | Print "Nothing to upgrade" / "<country> is already on 2.18", exit 0. |
| Soft pause | any anomaly (pre-scan or post-scan); diff-review answered `N`; LIVE retype-country mismatch | Wait for user input; on abort/restore/mismatch, run `git restore -- "$TARGET"` and exit cleanly. |

Never retry, never silently fall back. Any unexpected failure: print the error, exit, let the user re-run.

## Reference: PR body template

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`
from eRegistrations 2.17 to 2.18.

## Transformations applied

- Bumped every `unctad/<*>:2.17` image tag to `:2.18`.
- Swapped `minio/minio:latest` for `pgsty/minio:latest`.
- Replaced minio healthcheck with `CMD-SHELL bash -c 'echo > /dev/tcp/localhost/9000'`.
- Removed `EREGISTRATIONS_VERSION=<expected_EV>` from `bpa-frontend` and `ds-backend`.
- Removed `BUILD_TYPE=<expected_BT>` from `bpa-frontend` and `ds-backend`.

(`<expected_EV>` and `<expected_BT>` are `DEV` for env=dev, `2.17`/`LIVE` otherwise.)

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against the five fixed transformations documented in this skill (image bumps :2.17→:2.18, minio image swap, minio healthcheck rewrite, EREGISTRATIONS_VERSION line removal, BUILD_TYPE line removal).
```
