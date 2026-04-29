---
name: upgrade-eregistrations-instance
description: >
  Mechanical platform-version upgrade of a single eRegistrations instance —
  e.g. 2.17 → 2.18. Use when the user asks to upgrade an instance in any
  environment (dev/test/preview/prelive/live), references the upgrade plan
  for a new platform version, or asks to bump unctad image tags, swap minio
  to pgsty, rewrite the minio healthcheck, or remove deprecated env vars
  (EREGISTRATIONS_VERSION, BUILD_TYPE) for a known country. The user
  identifies the instance with a natural phrase like "lesotho test" or
  "kenya live"; the skill resolves to Conf-<ENV>/compose/<country>/. Strict
  mode — pauses on any anomaly. Refuses docker-stack.yml; use
  docker-swarm-migration first.
license: UNCTAD-Internal
compatibility: Requires the eRegistrations deployment-config repo on disk and an authenticated CLI for the host VCS (gh for GitHub origins; for Bitbucket origins the PR is opened manually after push).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(test *), Bash(grep *), Bash(for *), Bash(basename *), Bash(dirname *), Bash(gh *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-04-29"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country> <env>] [<from>-to-<to>]"
---

# Upgrade an eRegistrations instance

You are performing a mechanical platform-version upgrade of a single eRegistrations instance. The target file is `Conf-<ENV>/compose/<country>/docker-compose.yml`. The upgrade applies five fixed transformations (image bumps, minio swap, healthcheck rewrite, two env-var deletions). Operate in **strict mode**: any anomaly pauses for explicit user confirmation, with `abort` as the default.

The skill is invoked as `/upgrade-eregistrations-instance` with optional free-text arguments — e.g. `lesotho test`, `kenya live 2.17-to-2.18`, `colombia preview`. Missing arguments are asked interactively.

When the upgrade is approved, the skill commits on a fresh branch, pushes it, and opens a pull request against `master`. PR creation uses `gh` if the origin is GitHub; for Bitbucket origins the skill stops at push and tells the user to open the PR via the Bitbucket web UI.

## When to Use

- The user asks to upgrade `<country>` from version X to Y, or refers to a platform-version upgrade plan.
- `git grep -l 'unctad/.*:<from>' Conf-*/compose/<country>/` lists at least one `docker-compose.yml`. The skill resolves the candidate file at runtime in STEP 1.
- The user mentions any of: bumping unctad image tags between platform versions, swapping minio to `pgsty/minio`, rewriting the minio healthcheck to `CMD-SHELL`, or removing `EREGISTRATIONS_VERSION` / `BUILD_TYPE`.

**Don't use** for HAProxy config, remote-host operations, or any file other than `docker-compose.yml`. If the only file under `Conf-<ENV>/compose/<country>/` is `docker-stack.yml`, refuse and tell the user to run `docker-swarm-migration` first (or upgrade the stack file by hand for now — stack-file support is out of scope for v1).

## Conventions

- **`<from>` and `<to>`** — the platform versions, e.g. `2.17` and `2.18`. Default `<from>=2.17`, `<to>=2.18`.
- **`<env>`** — one of `dev`, `test`, `preview`, `prelive`, `live`. Maps to `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE`.
- **`<country>`** — a folder name under `Conf-<UPPER_ENV>/compose/`, e.g. `lesotho`, `kenya`, `colombia`.
- **Expected anomaly thresholds (per environment):**
  - `BUILD_TYPE=` value: `DEV` if `<env>=dev`, `LIVE` otherwise.
  - `EREGISTRATIONS_VERSION=` value: literal `DEV` if `<env>=dev`, the value of `<from>` otherwise.

## STEP 0: Pre-flight git checks

Before doing anything else, verify the repository is in a state where the upgrade can proceed. Run these checks in order. If any fails, print the failure reason and stop — do not proceed to STEP 1 and do not modify any files.

1. **Working tree is a git repo at the repo root.** Run `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Current branch is `master`.** Run `git rev-parse --abbrev-ref HEAD`. If the result is not exactly `master`, abort and print: "Refusing to run on branch <branch-name>. Switch to master first."
3. **No staged or modified tracked files.** Run `git status --porcelain --untracked-files=no`. If the output is non-empty, abort and print: "There are staged or modified tracked files. Resolve the changes below first." followed by the same output. Untracked files are ignored — the skill only `git add`s the single target file, so stray untracked files cannot be bundled into the upgrade commit.
4. **Origin host detected, CLI authenticated.** Run `git remote get-url origin`.
   - If it returns a URL containing `github.com`, set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - If it returns a URL containing `bitbucket.org`, set `HOST=bitbucket`. The skill will skip CLI-based PR creation and tell the user to open it manually after the push (`gh` does not work against Bitbucket).
   - Otherwise abort: "Unsupported origin host: <url>."
5. **`master` is in sync with origin.** Run `git pull --ff-only origin master`. If it fails, abort and print the git error verbatim. Suggest: "Resolve divergence (e.g. `git pull --rebase`) and re-run."

When all five checks pass, proceed to STEP 1.

## STEP 1: Identify the instance

Resolve `<country>`, `<env>`, `<from>`, and `<to>` from arguments and/or interactive prompts.

1. **Parse arguments.** If the skill was invoked with arguments, tokenize on whitespace and lowercase. Recognize:
   - Tokens matching one of `dev`, `test`, `preview`, `prelive`, `live` → set `<env>`.
   - Tokens of the form `<from>-to-<to>` (e.g. `2.17-to-2.18`) → set `<from>` and `<to>`.
   - The remaining token (if any) → candidate `<country>`.

2. **Ask for missing pieces.** For each of `<country>`, `<env>` not yet set, prompt:
   - `<env>` missing: "Which environment? dev / test / preview / prelive / live."
   - `<country>` missing: "Which country? Type the folder name as it appears under `Conf-<UPPER_ENV>/compose/`."
   - `<from>`/`<to>` missing: default `<from>=2.17`, `<to>=2.18`. Print the defaults and ask: "Press Enter to use 2.17 → 2.18, or type `<from>-to-<to>`."

3. **Resolve `<env>` to a directory.** `Conf-DEV`, `Conf-TEST`, `Conf-PREVIEW`, `Conf-PRELIVE`, `Conf-LIVE` (uppercase the user's lowercase token).

4. **Compute target.** `TARGET=Conf-<UPPER_ENV>/compose/<country>/docker-compose.yml`.

5. **Refuse stack-only instances.** If `docker-compose.yml` does not exist but `docker-stack.yml` does, abort and print:
   "`<country>` in `<env>` is on docker-stack.yml (Swarm). This skill only handles docker-compose.yml. Run `/docker-swarm-migration` if you intended to migrate, or upgrade the stack file by hand."

6. **Refuse missing instances.** If neither file exists, list the actual contents of `Conf-<UPPER_ENV>/compose/` and abort: "`<country>` not found in `<env>`. Eligible: <list>."

7. **Sanity-check eligibility.** Run `grep -q 'unctad/.*:<from>' "$TARGET"`. If it errors (no matches), print "`<country> <env>` has no `unctad/*:<from>` images — already on `<to>` or never on `<from>`?" and exit 0 cleanly.

8. **Print a one-line confirmation:** "Target: `<TARGET>` — upgrading `<from>` → `<to>`." and proceed to STEP 2.

## STEP 2: Pre-transformation strict scan

Before applying any edits, scan the target file for **anomalies**. Each anomaly pauses for explicit user input. Do not silently proceed.

For every anomaly, print:

```
ANOMALY: <kind>
  File: <TARGET>:<line-number>
  Line: <verbatim-line>
  (c)ontinue / (s)kip / (a)bort   [default: abort]
```

Read the user's single-character answer. Empty input means abort. The behaviour:

- `c` — apply the relevant transformation rule to this occurrence.
- `s` — leave this occurrence untouched (it will surface again in STEP 4 if it leaves a `<from>` token behind).
- `a` — stop the skill, no edits made.

If the user picks `s` for an anomaly kind, remember the choice for that kind only — do not re-prompt for further occurrences of the same kind in the same run.

**The anomaly kinds (run all five scans, collect the list, then prompt one anomaly at a time):**

1. **Mixed unctad versions.** A line matching `image:\s*unctad/[^:]+:[^ ]+` whose tag is neither `<from>` nor `<to>`. Examples for a 2.17→2.18 upgrade: `unctad/mule3-kenya:DEV`, `unctad/mule4-kenya:DEV`, `unctad/cas-backend:beta`, `unctad/bpa-backend:3.6.8-53`. Country mule images on `:DEV` are expected on test/dev instances and the user typically answers `s`.

2. **Already-`<to>` unctad services.** A line matching `image:\s*unctad/[^:]+:<to>`. This usually means a previous partial upgrade. Flag every occurrence.

3. **Non-standard minio.** Either:
   - the file contains no `minio:` service block (search for `^  minio:` at indent 2), OR
   - the `minio:` block's `image:` is not exactly `image: minio/minio:latest`, OR
   - the `minio:` block's `test:` line is not exactly the expected `test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]` (allow whitespace variation around brackets and commas).

4. **Unexpected `EREGISTRATIONS_VERSION` value.** Any line matching `EREGISTRATIONS_VERSION=` whose RHS, after stripping surrounding double quotes, is not the **expected value for this environment** (`DEV` for `<env>=dev`, otherwise `<from>`).

5. **Unexpected `BUILD_TYPE` value.** Any line matching `BUILD_TYPE=` whose RHS, after stripping surrounding double quotes, is not the **expected value for this environment** (`DEV` for `<env>=dev`, otherwise `LIVE`).

If no anomalies are detected, print "No anomalies. Applying transformations." and proceed.

If anomalies were detected and the user resolved them all (no `a` answer), proceed to STEP 3 and apply the transformations only to the expected occurrences. Do not auto-rewrite anomalous lines.

## STEP 3: Apply the five transformations

Edit `<TARGET>` in place. Apply each rule across the whole file. Preserve indentation and line endings exactly. Do not reformat anything else.

**Rule 1 — Bump unctad image tags.** For every line matching `^(\s*)image:\s*unctad/([^:\s]+):<from>\s*$`, replace `:<from>` with `:<to>`. Keep the leading whitespace and the image name verbatim. Country-specific images on non-`:<from>` tags (e.g. `unctad/mule3-kenya:DEV`) do not match and are not touched.

**Rule 2 — Swap minio image.** Replace the line `    image: minio/minio:latest` (within the `minio:` service block) with `    image: pgsty/minio:latest`. Preserve the existing indentation.

**Rule 3 — Replace minio healthcheck.** Within the `minio:` service block, find the `test:` line containing `["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]` and replace it with `test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/9000'"]`. Preserve the leading indentation of the original `test:` line.

**Rule 4 — Remove `EREGISTRATIONS_VERSION` line.** Delete every line whose stripped content is exactly `- EREGISTRATIONS_VERSION=<expected-value>` or the same with surrounding double quotes around the value. The expected-value is `DEV` for `<env>=dev`, otherwise `<from>`. Typical sites: `bpa-frontend` and `ds-backend`. Remove the entire line including its leading whitespace and trailing newline — do not leave a blank line behind.

**Rule 5 — Remove `BUILD_TYPE` line.** Delete every line whose stripped content is exactly `- BUILD_TYPE=<expected-value>` or the same with surrounding double quotes around the value. The expected-value is `DEV` for `<env>=dev`, otherwise `LIVE`. Same line-removal rules as Rule 4.

**Apply order:** rules 1 → 2 → 3 → 4 → 5. Each rule operates on the file produced by the previous rule.

**Tooling.** Apply the edits using your file-editing tool of choice (Edit/Write). Do not shell out to `sed -i` — macOS and Linux disagree on the `-i` flag, and the skill must work on both.

When all five rules are applied, proceed to STEP 4.

## STEP 4: Post-transformation safety scan

After applying the five rules, scan the modified `<TARGET>` for any remaining `<from>` token. Build a fixed-string pattern from `<from>` (escape every `.`) and run:

```bash
grep -nF "$FROM" "$TARGET" || true
```

For every match, present it as an anomaly with the same `(c)ontinue / (s)kip / (a)bort` prompt. `c` here means "leave it as is, this `<from>` is intentional"; `s` is identical (anomaly is left untouched); `a` rolls back: run `git restore -- "$TARGET"` and exit.

The standard upgrade should leave **zero** `<from>` matches. A non-zero count usually indicates either a comment, a non-standard env value, or a missed image line — pausing for the user is correct.

When the user has resolved all matches (or there were none), proceed to STEP 5.

## STEP 5: Diff review

Show the user the diff and ask for explicit approval before committing.

1. Run `git --no-pager diff --no-color -- "$TARGET"` and print the output verbatim (do not summarise).
2. Ask: "Commit, push, and open PR? (y/N)"
3. Read the answer.
   - `y` (case-insensitive) — proceed to STEP 5.5 if `<env>=live`, otherwise STEP 6.
   - Anything else — run `git restore -- "$TARGET"` and exit cleanly: "Aborted. No commit made."

### STEP 5.5: LIVE confirmation rail (only if `<env>=live`)

Production safety check. Print:

```
This will upgrade a LIVE production instance: <country>.
To confirm, type the country name exactly as you see it in the path
(<TARGET>) — anything else aborts.
```

Read the answer. If it does not match `<country>` exactly, run `git restore -- "$TARGET"` and exit cleanly: "Aborted. No commit made." Otherwise proceed to STEP 6.

## STEP 6: Branch, commit, push, open PR

1. **Compute the branch name.** `BRANCH=chore/upgrade-<env>-<country>-<from>-to-<to>` (e.g. `chore/upgrade-test-kenya-2.17-to-2.18`).

2. **Check the branch does not already exist.**
   - Local: `git rev-parse --verify "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort: "Branch $BRANCH already exists locally. Resolve manually."
   - Remote: `git ls-remote --exit-code --heads origin "$BRANCH" 2>/dev/null` should fail. If it succeeds, abort the same way.
   - On either failure, run `git restore -- "$TARGET"` so the working tree is clean again before exiting.

3. **Create the branch and commit.**

   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade <env>.<country> from <from> to <to>"
   ```

4. **Push the branch.**

   ```bash
   git push -u origin "$BRANCH"
   ```

   If the push is rejected, leave the local commit in place, return to `master` (`git checkout master`), and tell the user: "Push rejected. The local branch $BRANCH still has the commit; investigate and push manually."

5. **Open the PR — branch on `HOST`.**

   - If `HOST=github`: compose the body using the *PR body template* below (replace `<env>`, `<country>`, `<from>`, `<to>`, `<skipped>`, and `<expected-value>`). Then run:

     ```bash
     gh pr create \
       --base master \
       --head "$BRANCH" \
       --title "Upgrade <env>.<country> from <from> to <to>" \
       --body "<body>"
     ```

     If `gh pr create` fails, leave the branch pushed and the local commit in place. Print the gh error and tell the user: "PR creation failed; the branch is pushed. Open the PR manually."

   - If `HOST=bitbucket`: skip CLI PR creation. Parse `<workspace>/<repo>` from `git remote get-url origin` (formats: `git@bitbucket.org:<workspace>/<repo>.git` or `https://bitbucket.org/<workspace>/<repo>.git`) and print:

     ```
     Branch pushed: $BRANCH
     Open the PR via the Bitbucket web UI at:
     https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master
     ```

6. **Print the PR URL** returned by `gh pr create` (GitHub) or the constructed Bitbucket URL on its own line.

7. **Switch back to master.**

   ```bash
   git checkout master
   ```

8. Done.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort (no edits made) | not in git repo; not on master; dirty tree; `gh` missing on a GitHub origin; pull fails; user mistypes country/env twice; target missing; instance is on docker-stack.yml only; branch already exists locally or on origin | Print failure reason, exit non-zero. |
| Clean exit (no edits made) | selected file has zero `unctad/*:<from>` lines | Print "`<country> <env>` is already on `<to>` or never on `<from>`", exit 0. |
| Soft pause | any anomaly (pre-scan or post-scan); diff-review answered `N`; LIVE confirmation rail mistyped | Wait for user input; on abort/restore, run `git restore -- "$TARGET"` and exit cleanly. |

Never retry, never silently fall back. Any unexpected failure: print the error, exit, let the user re-run.

## Reference: PR body template

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-compose.yml`
from eRegistrations <from> to <to>.

## Transformations applied

- Bumped every `unctad/<*>:<from>` image tag to `:<to>`.
- Swapped `minio/minio:latest` for `pgsty/minio:latest`.
- Replaced minio healthcheck with `CMD-SHELL bash -c 'echo > /dev/tcp/localhost/9000'`.
- Removed `EREGISTRATIONS_VERSION=<expected-value>` from `bpa-frontend` and `ds-backend`.
- Removed `BUILD_TYPE=<expected-value>` from `bpa-frontend` and `ds-backend`.

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against a known-good <to> upgrade for the same environment — same shape, only country-specific lines differ.
```
