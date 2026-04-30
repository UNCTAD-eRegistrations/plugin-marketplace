---
name: upgrade-eregistrations-instance
description: >
  Orchestrator for upgrading a single eRegistrations instance to a target platform
  version. Resolves the instance from a natural-language phrase like "lesotho test" or
  "kenya live 2.17-to-2.18", detects the deployment shape (docker-compose vs
  docker-stack/swarm), confirms the source version, and dispatches to the matching
  upgrade sub-skill. Today the only registered route is `(test, 2.17→2.18, swarm)` →
  `/upgrade-test-to-2.18`. Other `(env, from→to, shape)` triples abort cleanly with
  a "no sub-skill registered" message rather than guessing or silently degrading.
  Strict mode. The 2.17 → 2.18 upgrade assumes the instance has already been migrated
  to swarm — instances still on `docker-compose.yml` route to `/docker-swarm-migration`
  first.
license: UNCTAD-Internal
compatibility: Requires the eRegistrations deployment-config repo on disk and an authenticated CLI for the host VCS (gh for GitHub origins; for Bitbucket origins the sub-skill prints a manual PR link after push). Sub-skills may add their own preconditions.
allowed-tools: Read, Grep, Glob, Bash(git *), Bash(test *), Bash(grep *), Bash(ls *), Bash(basename *), Bash(dirname *), Bash(gh *), Skill, AskUserQuestion
metadata:
  version: "2.0.0"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country> <env>] [<from>-to-<to>]"
  jira: "TOBE-17814"
  epic: "TOBE-17813"
---

# Upgrade an eRegistrations instance — orchestrator

You are the **router** for eRegistrations instance upgrades. Your job is short and mechanical:

1. Confirm the working tree is the eregistrations-v4 repo and is clean.
2. Resolve `<country>`, `<env>`, `<from>`, `<to>` from arguments and/or interactive prompts.
3. Detect the **deployment shape** (compose vs swarm) and refuse stack-only instances.
4. Sanity-check eligibility (does the chosen file actually contain `unctad/*:<from>`?).
5. Confirm a backup/snapshot exists.
6. Look up `(<env>, <from>, <to>, <shape>)` in the **dispatch table**.
7. If a sub-skill is registered, hand off via the `Skill` tool. Otherwise, abort cleanly with a "no sub-skill registered" message that names the missing tuple and points at TOBE-17814 / TOBE-17813.
8. After the sub-skill returns, print a verification checklist and offer to post a Jira tracker comment.

You **never** apply transformations yourself. All edit logic lives in the sub-skills.

## Dispatch table

| Env  | From | To   | Shape   | Sub-skill                 | Notes |
|------|------|------|---------|---------------------------|-------|
| test | 2.17 | 2.18 | swarm   | `/upgrade-test-to-2.18`   | Conf-TEST docker-stack.yml only. Compose-only instances must be migrated to swarm first via `/docker-swarm-migration`. |
| dev  | 2.17 | 2.18 | swarm   | _(unregistered)_          | Anomaly thresholds differ (`BUILD_TYPE=DEV`, `EREGISTRATIONS_VERSION=DEV`). Write `/upgrade-dev-to-2.18` from the test sub-skill template when needed. |
| preview | 2.17 | 2.18 | swarm | _(unregistered)_         | Same shape as test; same thresholds. Add `/upgrade-preview-to-2.18` when first preview instance is upgraded. |
| prelive | 2.17 | 2.18 | swarm | _(unregistered)_         | Same shape as test; same thresholds. Add `/upgrade-prelive-to-2.18` when first prelive instance is upgraded. |
| live | 2.17 | 2.18 | swarm   | _(unregistered)_          | Needs a LIVE confirmation rail (retype-country) before commit. Add `/upgrade-live-to-2.18` for the 8 live instances per TOBE-17813. |
| any  | any  | any  | compose | _(unregistered)_          | Compose-shape upgrades aren't handled here. Run `/docker-swarm-migration` first to convert the instance to swarm, then re-run this orchestrator. |
| any  | any  | any  | coolify | _(unregistered)_          | Coolify-managed instances aren't part of this repo. Out of scope. |

Add a row here when you write a new sub-skill. The orchestrator body otherwise stays unchanged. The shipped v1 of this skill (commit `55fb29a`, parametrised monolith) is the template body for any new env sub-skill — the five transformation rules and anomaly thresholds it documents are correct.

## Conventions

- **`<from>` and `<to>`** — platform versions, e.g. `2.17` and `2.18`. Defaults: `<from>=2.17`, `<to>=2.18`.
- **`<env>`** — one of `dev`, `test`, `preview`, `prelive`, `live`. Maps to `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE`.
- **`<country>`** — a folder name under `Conf-<UPPER_ENV>/compose/`, e.g. `lesotho`, `kenya`, `colombia`.
- **`<shape>`** — `compose` if `docker-compose.yml` is the authoritative file in the instance dir; `swarm` if `docker-stack.yml`; `coolify` is reserved for instances configured outside this repo.

## STEP 0: Pre-flight

Run these checks and abort on the first failure. Do not modify any files in this skill — sub-skills do their own write-side preconditions.

1. **Working tree is a git repo at the repo root.** `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Repo looks like eregistrations-v4.** `test -d Conf-TEST/compose`. If missing, abort: "This doesn't look like the eregistrations-v4 working tree (no `Conf-TEST/compose/` directory)."
3. **Current branch is `master`.** `git rev-parse --abbrev-ref HEAD`. If not `master`, abort: "Refusing to dispatch from branch `<branch>`. Switch to master first."
4. **No staged or modified tracked files.** `git status --porcelain --untracked-files=no`. Non-empty → abort and print the output verbatim.
5. **Origin host detected, CLI authenticated.** Run `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. The picked sub-skill will skip CLI-based PR creation and print a manual Bitbucket URL after push.
   - Otherwise abort: "Unsupported origin host: <url>."
6. **`master` is in sync with origin.** `git pull --ff-only origin master`. If it fails, abort and print the git error verbatim. Suggest: "Resolve divergence (e.g. `git pull --rebase`) and re-run."

When all six checks pass, proceed to STEP 1. Save `HOST` in conversation state — sub-skills will read it.

## STEP 1: Identify the instance

Resolve `<country>`, `<env>`, `<from>`, `<to>` from arguments and/or interactive prompts.

1. **Parse arguments.** If the skill was invoked with arguments, tokenize on whitespace and lowercase. Recognize:
   - Tokens matching one of `dev`, `test`, `preview`, `prelive`, `live` → set `<env>`.
   - Tokens of the form `<from>-to-<to>` (e.g. `2.17-to-2.18`) → set `<from>` and `<to>`.
   - The remaining token (if any) → candidate `<country>`.

2. **Ask for missing pieces** (in this order, only for fields not already set):
   - `<env>` missing: "Which environment? dev / test / preview / prelive / live."
   - `<country>` missing: list the directories under `Conf-<UPPER_ENV>/compose/` and ask: "Which country? Type the folder name."
   - `<from>`/`<to>` missing: print defaults `2.17 → 2.18` and ask: "Press Enter to use 2.17 → 2.18, or type `<from>-to-<to>`."

3. **Resolve `<env>` to a directory.** `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE` (uppercase the lowercase token).

4. **Validate `<country>` exists.** Run `test -d "Conf-<UPPER_ENV>/compose/<country>"`. If missing, list `ls Conf-<UPPER_ENV>/compose/` and abort: "`<country>` not found in `<env>`. Eligible: <list>." On the second invalid answer in this run, abort: "No valid instance picked, exiting."

Save the resolved `INSTANCE_DIR=Conf-<UPPER_ENV>/compose/<country>`.

## STEP 2: Detect deployment shape

Inspect `<INSTANCE_DIR>` and decide which **shape** applies. Use the first match in this order:

| Files present                                            | `<shape>` |
|----------------------------------------------------------|-----------|
| Both `docker-compose.yml` and `docker-stack.yml`         | ask the user which one is authoritative — do **not** guess. Wording: "Both `docker-compose.yml` and `docker-stack.yml` exist in `<INSTANCE_DIR>`. Which one is authoritative for the upgrade?" The answer determines the shape. |
| `docker-stack.yml` only                                  | `swarm` |
| `docker-compose.yml` only                                | `compose` |
| Neither                                                  | abort: "No docker-compose.yml or docker-stack.yml in `<INSTANCE_DIR>`. Don't know how to upgrade." |

Compute `TARGET=<INSTANCE_DIR>/<chosen-file>`.

## STEP 3: Sanity-check eligibility

Confirm the file actually contains `unctad/*:<from>` images. Build a fixed-string pattern from `<from>` (escape every `.`) and run:

```bash
grep -q "image:[[:space:]]*unctad/.*:${FROM_PATTERN}" "$TARGET"
```

If it errors (no matches), exit 0 cleanly: "`<country>` `<env>` has no `unctad/*:<from>` images — already on `<to>` or never on `<from>`. Nothing to upgrade."

Otherwise print: "Target: `<TARGET>` — upgrading `<from>` → `<to>` (shape: `<shape>`)." and proceed.

## STEP 4: Backup confirmation

The orchestrator will not deploy anything itself, but the picked sub-skill will produce a PR that, once merged, triggers a deploy. Before handing off, ask:

> "Is the current state of `<country>` `<env>` recoverable (snapshot, prior tag, manual export)? (y/N)"

If `N` (or empty), abort: "Resolve backups before re-running. The upgrade itself is mechanical, but rollback isn't free."

If `y`, continue.

## STEP 5: Dispatch

Look up `(<env>, <from>, <to>, <shape>)` in the dispatch table.

- **Match found.** Print the routing decision, then invoke the sub-skill via the `Skill` tool. Example for the only registered route today:
  > "Routing to `/upgrade-test-to-2.18` (test, swarm, 2.17 → 2.18)."
  Call `Skill(skill="upgrade-test-to-2.18")`. The sub-skill handles its own pre-flight (it duplicates a few checks so it can also be invoked standalone), anomaly scan, edits, and PR creation.

- **No match.** Print:
  > "No sub-skill registered for `(env=<env>, from=<from>, to=<to>, shape=<shape>)`.
  > This combination is tracked under TOBE-17814 (parent epic TOBE-17813). To unblock, either:
  > - extend the dispatch table in `upgrade-eregistrations-instance/SKILL.md` and write a new sub-skill (use `upgrade-test-to-2.18` and the v1 monolith body in commit `55fb29a` as templates — the five transformation rules are environment-invariant), or
  > - perform the upgrade manually for now."
  Exit 0 (clean — this is expected for unregistered combos, not a failure).

## STEP 6: Post-handoff (only when sub-skill returned a PR/branch URL)

After the sub-skill returns control, if it produced a PR or branch URL:

1. Print a short verification checklist tailored to the shape:
   - **swarm** (the only currently routed shape): "After the PR merges and CI redeploys: `docker stack ps <stack>` and `docker service ls` should show the new image digests for `bpa-frontend`, `bpa-backend`, `ds-backend`, `ds-frontend`. Hit the instance's `/health` (BPA, DS) and smoke a known service flow."
2. Offer (don't auto-execute) to post a Jira comment on TOBE-17814 with the PR URL and the routing decision.
   - If the user answers `y`, draft the comment in ADF (per project convention — markdown renders `\n` literally in Jira) and post via the Atlassian MCP tooling.
   - If `N` or empty, exit cleanly.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort | not eregistrations-v4; not on master; dirty tree; gh missing on GitHub origin; pull fails; instance dir missing; both shape files present and user gave neither; user mistypes country twice | Print reason, exit non-zero. Sub-skill not invoked. |
| Clean exit | no `unctad/*:<from>` images found; `(<env>, <from>, <to>, <shape>)` has no registered sub-skill; user said "N" to backup confirmation | Print reason, exit 0. |
| Sub-skill failure | sub-skill aborts mid-way (e.g. anomaly resolved with `a`) | The sub-skill restores its own files and exits. Orchestrator does not retry — let the user re-run. |

## Reference: extending the orchestrator

To add a new upgrade path:

1. Write the sub-skill under `plugins/devops/skills/<sub-skill-name>/SKILL.md`. Keep its scope narrow — one shape, one version pair, one env. Use `upgrade-test-to-2.18/SKILL.md` as the template.
2. Add a row to the **Dispatch table** above with the exact `(env, from, to, shape)` triple and the slash-command name.
3. Bump this skill's `metadata.version` (minor for a new route, patch for clarifications).
4. Update `plugins/devops/README.md` to list the new sub-skill.

Don't fold sub-skill logic into the orchestrator. Don't introduce env-specific branches in the orchestrator's STEP 5. Each new env or version pair is a new sub-skill row.
