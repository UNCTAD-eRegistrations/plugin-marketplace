---
name: upgrade-eregistrations-instance
description: >
  Orchestrator for upgrading a single eRegistrations instance to a target platform
  version. Resolves the instance from a natural-language phrase like "lesotho test" or
  "syria2 test 2.18", auto-detects the source version from `unctad/*` image tags
  (with `EREGISTRATIONS_VERSION` as the tiebreaker between 2.14 and 2.15, which both
  use the `:RC` platform tag), detects the deployment shape (docker-compose vs
  docker-stack/swarm), and dispatches to a chain of upgrade sub-skills covering one
  version step each. For single-step pairs (e.g. 2.17 → 2.18) it forwards to one
  sub-skill; for multi-step pairs (e.g. 2.14 → 2.18) it owns the branch lifecycle:
  creates one branch, runs sub-skills in chain mode (commit-only), squashes their
  per-step commits into one, pushes, and opens a single PR. LIVE retype-country rail
  fires once before the first step in any chain. Supported source versions: 2.14,
  2.15, 2.16, 2.17. Other version pairs and the `compose` shape abort cleanly with a
  "no chain registered" message. The 2.17 → 2.18 upgrade and chains involving it
  assume the instance has already been migrated to swarm — instances still on
  `docker-compose.yml` route to `/docker-swarm-migration` first.
license: UNCTAD-Internal
compatibility: Requires the eRegistrations deployment-config repo on disk and an authenticated CLI for the host VCS (gh for GitHub origins; for Bitbucket origins the orchestrator prints a manual PR link after push). Sub-skills add their own preconditions.
allowed-tools: Read, Grep, Glob, Bash(git *), Bash(test *), Bash(grep *), Bash(ls *), Bash(basename *), Bash(dirname *), Bash(gh *), Skill, AskUserQuestion
metadata:
  version: "3.1.0"
  version-date: "2026-05-04"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country> <env>] [<from>-to-<to>]"
  jira: "TOBE-17814"
  epic: "TOBE-17813"
---

# Upgrade an eRegistrations instance — orchestrator

You are the **router** for eRegistrations instance upgrades. Your job is to:

1. Confirm the working tree is the eregistrations-v4 repo and is clean.
2. Resolve `<country>`, `<env>`, `<from>`, `<to>` (auto-detecting `<from>` from the file when possible).
3. Detect the **deployment shape** (compose vs swarm) and refuse compose-only with a pointer to `/docker-swarm-migration`.
4. Confirm a backup/snapshot exists.
5. Look up `(<env>, <from>, <to>, <shape>)` in the **dispatch table** and resolve it to a chain (list) of sub-skills.
6. Run the chain:
   - **Single-step chain** (one sub-skill): hand off via `Skill` and let it own its branch + PR.
   - **Multi-step chain** (two or more sub-skills): orchestrator owns the branch lifecycle — creates one branch, runs each sub-skill in chain mode (commit-only), squashes the per-step commits into one, pushes, and opens a single PR.
7. After the chain completes, print a verification checklist and offer to post a Jira tracker comment.

You **never** apply transformations yourself. All edit logic lives in the sub-skills.

## Dispatch table

The table maps `(<env>, <from>, <to>, <shape>)` to a **chain** — an ordered list of sub-skills. A chain may contain one entry (single-step) or several (multi-step).

| Env | From | To | Shape | Chain |
|---|---|---|---|---|
| any (dev/test/preview/prelive/live) | 2.17 | 2.18 | swarm | `[/upgrade-2.17-to-2.18]` |
| any | 2.16 | 2.17 | swarm | `[/upgrade-2.16-to-2.17]` |
| any | 2.16 | 2.18 | swarm | `[/upgrade-2.16-to-2.17, /upgrade-2.17-to-2.18]` |
| any | 2.15 | 2.16 | swarm | `[/upgrade-2.15-to-2.16]` |
| any | 2.15 | 2.17 | swarm | `[/upgrade-2.15-to-2.16, /upgrade-2.16-to-2.17]` |
| any | 2.15 | 2.18 | swarm | `[/upgrade-2.15-to-2.16, /upgrade-2.16-to-2.17, /upgrade-2.17-to-2.18]` |
| any | 2.14 | 2.15 | swarm | `[/upgrade-2.14-to-2.15]` |
| any | 2.14 | 2.16 | swarm | `[/upgrade-2.14-to-2.15, /upgrade-2.15-to-2.16]` |
| any | 2.14 | 2.17 | swarm | `[/upgrade-2.14-to-2.15, /upgrade-2.15-to-2.16, /upgrade-2.16-to-2.17]` |
| any | 2.14 | 2.18 | swarm | `[/upgrade-2.14-to-2.15, /upgrade-2.15-to-2.16, /upgrade-2.16-to-2.17, /upgrade-2.17-to-2.18]` |
| any | any | any | compose | _(unregistered)_ — run `/docker-swarm-migration` first |
| any | any | any | coolify | _(unregistered)_ — out of scope (Coolify-managed) |

Each row covers all five envs in one entry; sub-skills handle env-aware anomaly thresholds internally.

To extend: write a new atomic sub-skill (e.g. `/upgrade-2.18-to-2.19` for a future version, or `/upgrade-2.13-to-2.14` for a deeper history reach) and add the rows that include it.

## Conventions

- **`<from>` and `<to>`** — platform versions, e.g. `2.15`, `2.16`, `2.17`, `2.18`. The orchestrator auto-detects `<from>` from the target file's `unctad/*` image tags; user supplies `<to>` (default `2.18`).
- **`<env>`** — one of `dev`, `test`, `preview`, `prelive`, `live`. Maps to `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE`.
- **`<country>`** — a folder name under `Conf-<UPPER_ENV>/compose/`.
- **`<shape>`** — `compose` if `docker-compose.yml` is the authoritative file in the instance dir; `swarm` if `docker-stack.yml`.
- **Tag-to-version mapping** (used for source-version detection): `:RC` → `2.14` *or* `2.15` (ambiguous — disambiguated by `EREGISTRATIONS_VERSION`, see STEP 3), `:BETA` → `2.16`, `:2.17` → `2.17`, `:2.18` → `2.18`.

## STEP 0: Pre-flight

Run these checks and abort on the first failure. Do not modify any files.

1. **Working tree is a git repo at the repo root.** `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Repo looks like eregistrations-v4.** `test -d Conf-TEST/compose`. If missing, abort: "This doesn't look like the eregistrations-v4 working tree (no `Conf-TEST/compose/` directory)."
3. **Current branch is `master`.** `git rev-parse --abbrev-ref HEAD`. If not `master`, abort: "Refusing to dispatch from branch `<branch>`. Switch to master first."
4. **No staged or modified tracked files.** `git status --porcelain --untracked-files=no`. Non-empty → abort and print the output verbatim.
5. **Origin host detected, CLI authenticated.** Run `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. Multi-step chains will skip CLI-based PR creation and print a manual Bitbucket URL after push; single-step chains hand off to a sub-skill that does the same.
   - Otherwise abort: "Unsupported origin host: <url>."
6. **`master` is in sync with origin.** `git pull --ff-only origin master`. If it fails, abort and print the git error verbatim. Suggest: "Resolve divergence (e.g. `git pull --rebase`) and re-run."

When all six checks pass, proceed to STEP 1. Save `HOST` in conversation state — sub-skills will read it.

## STEP 1: Identify the instance

Resolve `<country>`, `<env>`, `<to>` (target version) from arguments and/or interactive prompts. `<from>` is auto-detected in STEP 3.

1. **Parse arguments.** If invoked with arguments, tokenize on whitespace and lowercase. Recognize:
   - Tokens equal to one of `dev`, `test`, `preview`, `prelive`, `live` → set `<env>`.
   - Tokens of the form `<from>-to-<to>` (e.g. `2.15-to-2.18`) → set `<from>` (override) and `<to>`.
   - Tokens of the form `<X.Y>` alone (e.g. `2.18`) → set `<to>`.
   - The remaining token (if any) → candidate `<country>`.

2. **Ask for missing pieces** (only fields not already set):
   - `<env>` missing: "Which environment? dev / test / preview / prelive / live."
   - `<country>` missing: list directories under `Conf-<UPPER_ENV>/compose/` and ask: "Which country? Type the folder name."
   - `<to>` missing: print default `2.18` and ask: "Press Enter to use target 2.18, or type the target version (e.g. `2.17`)."

3. **Resolve `<env>` to a directory.** `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE`.

4. **Validate `<country>` exists.** `test -d "Conf-<UPPER_ENV>/compose/<country>"`. Missing → abort with the eligible list. Two-strikes invalid (interactive) → abort.

Save `INSTANCE_DIR=Conf-<UPPER_ENV>/compose/<country>`.

## STEP 2: Detect deployment shape

Inspect `<INSTANCE_DIR>` and decide which **shape** applies. Use the first match:

| Files present                                            | `<shape>` |
|----------------------------------------------------------|-----------|
| Both `docker-compose.yml` and `docker-stack.yml`         | ask the user which is authoritative — do **not** guess. |
| `docker-stack.yml` only                                  | `swarm` |
| `docker-compose.yml` only                                | `compose` |
| Neither                                                  | abort: "No docker-compose.yml or docker-stack.yml in `<INSTANCE_DIR>`." |

Compute `TARGET=<INSTANCE_DIR>/<chosen-file>`.

## STEP 3: Detect source version + sanity-check eligibility

Auto-detect the source version from the unctad image tags in `<TARGET>`. If `<from>` was already set via args, treat the auto-detected value as a cross-check.

1. **Build a tag histogram.** Run:

   ```bash
   grep -oE 'image:[[:space:]]*unctad/[^:[:space:]]+:[^[:space:]]+' "$TARGET" \
     | sed -E 's/.*:([^:]+)$/\1/' \
     | sort | uniq -c | sort -rn
   ```

2. **Map tags to versions** using the table in *Conventions*. Country-specific images on `:DEV` (e.g. `unctad/mule3-kenya:DEV`) and the floating-tag services (`statistics-backend:DEV`, `ds-frontend:DEV` pre-2.17) are noise — count them but don't use them for the dominant-tag decision. Specifically, ignore the `mule3-`, `mule4-`, and `cashier-` country variants and the `:DEV`-tagged statistics/ds-frontend pre-2.17 lines.

3. **Pick the dominant version.** The majority of platform-tag occurrences (after filtering noise) determines the candidate. Then:
   - All-`:RC` (or majority `:RC`) → ambiguous between `2.14` and `2.15`. Disambiguate via the `EREGISTRATIONS_VERSION` env var on the canonical service block (prefer `bpa-frontend`, fall back to `ereg-cms-frontend`):
     ```bash
     grep -hE 'EREGISTRATIONS_VERSION=["'"'"']?(2\.14|2\.15)' "$TARGET" | sed -E 's/.*EREGISTRATIONS_VERSION=["'"'"']?(2\.14|2\.15).*/\1/' | sort -u
     ```
     - Single line `2.14` → `<auto_from>=2.14`.
     - Single line `2.15` → `<auto_from>=2.15`.
     - Both / neither / `DEV` → ambiguous: print the histogram and the env-var lines and ask "RC tag could mean 2.14 or 2.15. What is the source version? (`2.14` / `2.15`)".
   - All-`:BETA` (or majority `:BETA`) → `2.16`
   - All-`:2.17` → `2.17`
   - All-`:2.18` → `2.18`
   - Otherwise: print the histogram and ask: "Mixed image tags detected. What is the source version? (`2.14` / `2.15` / `2.16` / `2.17` / `2.18`)" and use the user's answer as `<auto_from>`.

4. **Reconcile with args.** If `<from>` was supplied via args and differs from `<auto_from>`, print both and ask: "Argument `<from>` is `<arg>` but the file looks like `<auto_from>`. Use which? (`<arg>` / `<auto_from>`)" — default to `<auto_from>` on empty input.

5. **Eligibility sanity-check.** Build a fixed-string pattern from `<from>` (escape every `.`) and confirm the file actually contains the expected tags:

   ```bash
   grep -q "image:[[:space:]]*unctad/.*:${FROM_PATTERN}" "$TARGET"
   ```

   Tag-to-grep mapping: `2.14` → `RC`, `2.15` → `RC`, `2.16` → `BETA`, `2.17` → `2.17`, `2.18` → `2.18`. If the grep finds nothing, exit 0 cleanly: "`<country>` `<env>` has no `unctad/*` images on the `<from>` tag pattern — already on `<to>` or never on `<from>`. Nothing to upgrade."

6. **Idempotency check.** If `<from> == <to>` (e.g. user asked for 2.18 and file is already 2.18), print: "`<country>` `<env>` is already on `<to>`. Nothing to upgrade." Exit 0.

Print: "Target: `<TARGET>` — upgrading `<from>` → `<to>` (shape: `<shape>`)." and proceed.

## STEP 4: Backup confirmation

Once before the whole chain, ask:

> "Is the current state of `<country>` `<env>` recoverable (snapshot, prior tag, manual export)? (y/N)"

If `N` (or empty), abort: "Resolve backups before re-running. The upgrade itself is mechanical, but rollback isn't free."

If `y`, continue. The orchestrator threads `BACKUP_CONFIRMED=1` to every sub-skill in the chain — sub-skills won't re-ask.

## STEP 5: Resolve and run the chain

Look up `(<env>, <from>, <to>, <shape>)` in the dispatch table.

- **No match.** Print:
  > "No chain registered for `(env=<env>, from=<from>, to=<to>, shape=<shape>)`.
  > Tracked under TOBE-17814 (parent epic TOBE-17813). To unblock, either:
  > - extend the dispatch table here and write a new atomic sub-skill (use `upgrade-2.17-to-2.18` as the template), or
  > - perform the upgrade manually for now."
  Exit 0 (clean — unregistered combos are expected, not failures).

- **Match found, single-step chain (one sub-skill).** Print: "Routing to `<sub-skill>` (`<env>`, `<shape>`, `<from>` → `<to>`)." Call `Skill(skill="<sub-skill-name>", args="<country> <env> BACKUP_CONFIRMED=1")`. The sub-skill creates its own branch, commits, pushes, and opens its own PR. When the sub-skill returns, proceed to STEP 6.

- **Match found, multi-step chain (two or more sub-skills).** The orchestrator owns the branch lifecycle. Run STEP 5a → 5d below.

### STEP 5a: Create the chain branch

1. **Compute the branch name.**

   `BRANCH=chore/upgrade-<env>-<country>-<from>-to-<to>` (e.g. `chore/upgrade-test-syria2-2.15-to-2.18`).

2. **Check the branch doesn't already exist.**
   - Local: `git rev-parse --verify "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort: "Branch $BRANCH already exists locally. Resolve manually."
   - Remote: `git ls-remote --exit-code --heads origin "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort the same way.

3. **Record the base commit.** `BASE_SHA=$(git rev-parse HEAD)` — the orchestrator squashes against this at STEP 5d.

4. **Create the branch.** `git checkout -b "$BRANCH"`.

### STEP 5b: LIVE confirmation rail (only when `<env>=live`)

For LIVE production targets, ask the user to retype the country name once before any step touches the file:

1. Print:
   ```
   This will upgrade a LIVE production instance: <country>
   from <from> to <to> across <N> step(s).
   Type the country name exactly to confirm — anything else aborts.
   ```
2. Read the user's answer. Trim whitespace.
3. Compare to `<country>` exactly (case-sensitive).
   - Match → proceed to STEP 5c.
   - Mismatch → `git checkout master`, `git branch -D "$BRANCH"`, exit cleanly: "Country name mismatch. Aborted. No commit made."

### STEP 5c: Run the chain

For each sub-skill in the chain, in order:

1. Print: "Step `<i>/<N>`: `<sub-skill>` (`<step_from>` → `<step_to>`)."

2. **Invoke the sub-skill in chain mode.**

   ```
   Skill(skill="<sub-skill-name>", args="<country> <env> BACKUP_CONFIRMED=1 CHAIN_MODE=1 CHAIN_BRANCH=<BRANCH>")
   ```

   The sub-skill applies its rules, runs its post-scan, shows its diff, commits a single step-scoped commit on `<BRANCH>` (with message `Step <step_from>→<step_to> on <env>.<country> TOBE-17814`), and returns.

3. **After sub-skill returns**, verify a commit was made:

   ```bash
   git log --oneline "$BASE_SHA..HEAD"
   ```

   The number of commits should equal `<i>` (one per completed step). If it's still `<i-1>`, the sub-skill aborted mid-step (e.g. user answered `a` to an anomaly, or the LIVE rail mismatched, or a post-scan fail rolled back). In that case:
   - Print: "Step `<i>/<N>` aborted by sub-skill. The chain branch `<BRANCH>` is left in place with the prior `<i-1>` step(s) committed."
   - Print recovery hint: "To finalize the partial chain into a PR, re-run `/upgrade-eregistrations-instance` and answer 'continue partial' when offered. To abandon, run `git checkout master && git branch -D <BRANCH>`."
   - Exit 0 (clean) — the user decides next.

4. **Between steps**, if there are more steps remaining, ask:

   > "Step `<i>/<N>` complete. Continue to step `<i+1>/<N>` (`<next_from>` → `<next_to>`)? (y/N)"

   - `y` → next iteration.
   - `N` or empty → stop here, finalize the partial chain. Set the **effective `<to>`** to the last completed step's `<step_to>` (used in STEP 5d for the squashed commit message and PR title). Adjust `BRANCH` for the partial chain: rename via `git branch -m "$BRANCH" "chore/upgrade-<env>-<country>-<from>-to-<effective_to>"` and update the variable. Proceed to STEP 5d.

   The pause exists to let the user verify each step's diff (already shown by the sub-skill) before committing further. If the user wants to run the whole chain non-stop, they can answer `y` to all.

### STEP 5d: Squash, push, open single PR

After the chain runs (whether complete or partially complete), the branch has `<N_completed>` commits ahead of `<BASE_SHA>` (where `<N_completed>` is the number of sub-skills that committed).

1. **Squash to a single commit** (only if `<N_completed> > 1`).

   ```bash
   git reset --soft "$BASE_SHA"
   git commit -m "Upgrade <env>.<country> from <from> to <effective_to> TOBE-17814"
   ```

   If `<N_completed> == 1`, leave the single commit as-is — it already has a step-scoped message, but rename it for clarity:

   ```bash
   git commit --amend -m "Upgrade <env>.<country> from <from> to <effective_to> TOBE-17814"
   ```

2. **Push the branch.**

   ```bash
   git push -u origin "$BRANCH"
   ```

   On rejection: leave the local branch and commit, return to master (`git checkout master`), and tell the user: "Push rejected. Branch `<BRANCH>` retained locally with the squashed commit. Investigate and push manually."

3. **Open the PR.** Compose the body using the *Multi-step PR body template* at the bottom of this skill, aggregating each step's transformations.

   - **GitHub:**

     ```bash
     gh pr create \
       --base master \
       --head "$BRANCH" \
       --title "Upgrade <env>.<country> from <from> to <effective_to>" \
       --body "<body>"
     ```

   - **Bitbucket:** print the manual link:

     ```
     Branch pushed: $BRANCH
     Open the PR via the Bitbucket web UI at:
     https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master
     ```

4. **Print summary:**
   ```
   ✓ Chain complete: <from> → <effective_to> in <N_completed> step(s).
   PR: <url>
   ```

5. **Switch back to master.** `git checkout master`.

## STEP 6: Post-handoff

After the chain finishes (single-step or multi-step):

1. Print a verification checklist tailored to the shape:
   - **swarm**: "After the PR merges and CI redeploys: `docker stack ps <stack>` and `docker service ls` should show the new image digests for `bpa-frontend`, `bpa-backend`, `ds-backend`, `ds-frontend`. Hit the instance's `/health` (BPA, DS) and smoke a known service flow."
2. Offer (don't auto-execute) to post a Jira comment on TOBE-17814 with the PR URL and the chain decision.
   - If `y`, draft the comment in ADF (markdown renders `\n` literally in Jira) and post via the Atlassian MCP tooling.
   - If `N` or empty, exit cleanly.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort | not eregistrations-v4; not on master; dirty tree; gh missing on GitHub origin; pull fails; instance dir missing; chain branch already exists | Print reason, exit non-zero. No sub-skill invoked. |
| Clean exit | no `unctad/*:<from>` images found; `<from>=<to>` (already on target); `(<env>, <from>, <to>, <shape>)` has no registered chain; user said "N" to backup confirmation | Print reason, exit 0. |
| Sub-skill mid-chain abort | sub-skill aborts during a step (anomaly `a`, LIVE rail mismatch in standalone fallback, post-scan fail) | The chain branch is left with the completed steps. Orchestrator does not retry — let the user investigate and decide whether to continue or abandon. |
| Push rejection on chain branch | `git push` fails after squash | Branch retained locally with the squashed commit; user pushes manually. |

## Reference: extending the orchestrator

To add a new upgrade path (e.g. 2.18 → 2.19):

1. Write a new atomic sub-skill `plugins/devops/skills/upgrade-2.18-to-2.19/SKILL.md` modelled on `upgrade-2.17-to-2.18`. Make it mode-aware (`CHAIN_MODE`, `CHAIN_BRANCH`).
2. Add row(s) to the **Dispatch table** above. Single-step row for the new pair, plus extension rows for any chain that reaches the new target (e.g. `2.17 → 2.19` chain `[2.17→2.18, 2.18→2.19]`).
3. Bump this orchestrator's `metadata.version`.
4. Update `plugins/devops/README.md` to list the new sub-skill.

To add a new "starting from older version" path (e.g. 2.13 → 2.18):

1. Write `plugins/devops/skills/upgrade-2.13-to-2.14/SKILL.md` (one new atomic skill).
2. Add tag-to-version mapping for the older tag pattern in *Conventions* and STEP 3. Note: 2.14 and 2.15 share `:RC` and are disambiguated via `EREGISTRATIONS_VERSION` — replicate that approach if 2.13 also reuses an existing platform tag, otherwise add a new tag-to-version row.
3. Add rows for `(2.13, 2.14)`, `(2.13, 2.15)`, `(2.13, 2.16)`, `(2.13, 2.17)`, `(2.13, 2.18)` — each chains the appropriate sub-skill list.
4. Bump version, update README.

## Reference: Multi-step PR body template

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`
from eRegistrations <from> to <effective_to>.

This PR is the squashed result of <N_completed> chained version step(s):
<list each sub-skill that ran, e.g.:>
- `/upgrade-2.15-to-2.16`
- `/upgrade-2.16-to-2.17`
- `/upgrade-2.17-to-2.18`

## Transformations applied

<aggregate the "Transformations applied" sections from each sub-skill's PR body
template, deduplicating where they overlap. Each step's transformations are
documented in its individual SKILL.md; reproduce the bullet list here so anyone
reading the PR doesn't need to chase three skill files.>

## Anomalies skipped

<aggregate skipped-anomaly bullets across all steps, prefixing each with the
step it came from, e.g. "(step 2.15→2.16) Mixed unctad versions on country mule">

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the squashed diff against the rules in each chained sub-skill.
- [ ] After merge: `docker stack ps <stack>` shows new image digests for bpa-frontend, bpa-backend, ds-backend, ds-frontend.
- [ ] Smoke-test BPA login, DS, and a known service flow end-to-end.
```
