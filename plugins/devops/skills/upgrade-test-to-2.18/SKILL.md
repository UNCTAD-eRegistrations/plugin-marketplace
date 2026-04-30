---
name: upgrade-test-to-2.18
description: >
  Upgrade a test instance under Conf-TEST/compose/<country>/docker-compose.yml from
  eRegistrations 2.17 to 2.18. Bumps standard unctad images, swaps the minio image and
  healthcheck, and removes deprecated env vars. Strict mode — aborts on anything
  unexpected. Commits on a fresh feature branch, pushes, and opens a pull request
  against master (gh on GitHub origins, manual link on Bitbucket origins).
  Compose-shape instances only — swarm stacks (docker-stack.yml) are out of scope and
  must be routed elsewhere by the upgrade-eregistrations-instance orchestrator.
license: UNCTAD-Internal
compatibility: Run from the eregistrations-v4 working tree on master with a clean tracked tree. Requires an authenticated CLI for the host VCS (gh for GitHub origins; Bitbucket origins skip CLI PR creation and print a manual link).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(grep *), Bash(test *), Bash(ls *), Bash(basename *), Bash(dirname *), AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  jira: "TOBE-17814"
---

# Upgrade test instance from 2.17 to 2.18

You are performing a mechanical eRegistrations 2.17 → 2.18 upgrade of a single test instance. The target file is `Conf-TEST/compose/<country>/docker-compose.yml`. The upgrade applies five fixed transformations (image bumps, minio swap, healthcheck rewrite, two env-var deletions). Operate in **strict mode**: any anomaly pauses for explicit user confirmation, with `abort` as the default.

The skill is invoked as `/upgrade-test-to-2.18` with no arguments. It is also routed to by the `upgrade-eregistrations-instance` orchestrator when it detects a `Conf-TEST` compose-shape instance on `unctad/*:2.17` images.

When the upgrade is approved, the skill commits on a fresh branch `chore/upgrade-test-<country>-2.18`, pushes it, and opens a pull request against `master` via `gh`.

## Scope (intentionally narrow)

- **In scope:** a single `Conf-TEST/compose/<country>/docker-compose.yml` whose `unctad/*` images are pinned at `:2.17`.
- **Out of scope:** any `docker-stack.yml` (swarm), Coolify-managed instances, anything outside `Conf-TEST`, simultaneous upgrades of multiple instances, version pairs other than 2.17 → 2.18.

If the target file is a `docker-stack.yml`, abort and tell the user to use the orchestrator (`/upgrade-eregistrations-instance`) — swarm stacks need a different sub-skill that doesn't exist yet.

## STEP 0: Pre-flight git checks

Before doing anything else, verify the repository is in a state where
the upgrade can proceed. Run these checks in order. If any fails,
print the failure reason and stop — do not proceed to STEP 1 and do
not modify any files.

1. **Working tree is a git repo at the repo root.** Run
   `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git
   working tree."
2. **Current branch is `master`.** Run
   `git rev-parse --abbrev-ref HEAD`. If the result is not exactly
   `master`, abort and print: "Refusing to run on branch
   <branch-name>. Switch to master first."
3. **No staged or modified tracked files.** Run
   `git status --porcelain --untracked-files=no`. If the output is
   non-empty, abort and print:
   "There are staged or modified tracked files. Resolve the changes
   below first." followed by the same output. Untracked files are
   ignored — the skill only `git add`s the single target file, so
   stray untracked files cannot be bundled into the upgrade commit.
4. **Origin host detected, CLI authenticated.** If the orchestrator
   already set `HOST` in conversation state (it does so in its own
   pre-flight), reuse that value. Otherwise resolve it now: run
   `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run
     `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not
     installed or not authenticated. Install gh and run `gh auth login`
     before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. The skill
     will skip CLI-based PR creation and print a manual Bitbucket URL
     after push.
   - Otherwise abort: "Unsupported origin host: <url>."
5. **`master` is in sync with origin.** Run
   `git pull --ff-only origin master`. If it fails, abort and print
   the git error verbatim. Suggest: "Resolve divergence (e.g.
   `git pull --rebase`) and re-run."

When all five checks pass, proceed to STEP 1.

## STEP 1: Pick the instance

Build the list of upgrade candidates and ask the user which one to
upgrade.

1. **Find candidates.** Run:

   ```bash
   for f in Conf-TEST/compose/*/docker-compose.yml; do
     if grep -q 'unctad/.*:2\.17' "$f"; then
       echo "$(basename "$(dirname "$f")")"
     fi
   done | sort
   ```

2. **No candidates found.** If the loop produced zero lines, print:
   "Nothing to upgrade — no Conf-TEST compose-shape instance contains
   `unctad/*:2.17`. Note: `docker-stack.yml` (swarm) instances are
   intentionally not handled by this skill — see
   `/upgrade-eregistrations-instance`." Exit 0. Do not abort.

3. **Present the list.** Print one country per line, prefixed with
   `- `, then ask:
   "Which test instance? Type the country folder name."

4. **Read the user's answer.** Trim whitespace.

5. **Validate.** If the answer is not in the candidate list, print
   "`<answer>` is not a valid choice. Eligible: <list>." and ask
   again. On the second consecutive invalid answer, abort: "No valid
   instance picked, exiting."

6. **Confirm the target file exists.** Compute
   `TARGET=Conf-TEST/compose/<answer>/docker-compose.yml`. Run
   `test -f "$TARGET"`. If missing, abort: "$TARGET not found." (This
   should not happen if the candidate list was built correctly.)

7. **Save the picked country in conversation state** as `<country>`
   for the rest of the run.

Proceed to STEP 2.

## STEP 2: Pre-transformation strict scan

Before applying any edits, scan the target file for **anomalies**.
Each anomaly pauses for explicit user input. Do not silently proceed.

For every anomaly, print:

```
ANOMALY: <kind>
  File: <TARGET>:<line-number>
  Line: <verbatim-line>
  (c)ontinue / (s)kip / (a)bort   [default: abort]
```

Read the user's single-character answer. Empty input means abort. The
behaviour:

- `c` — apply the relevant transformation rule to this occurrence.
- `s` — leave this occurrence untouched (it will surface again in
  STEP 4 if it leaves a `2.17` token behind).
- `a` — stop the skill, no edits made.

If the user picks `s` for an anomaly kind, remember the choice for
that kind only — do not re-prompt for further occurrences of the same
kind in the same run.

**The anomaly kinds (run all five scans, collect the list, then
prompt one anomaly at a time):**

1. **Mixed unctad versions.** A line matching
   `image:\s*unctad/[^:]+:[^ ]+` whose tag is neither `2.17` nor
   `2.18`. Examples: `unctad/mule3-kenya:DEV`, `unctad/mule4-kenya:DEV`,
   `unctad/cas-backend:beta`, `unctad/bpa-backend:3.6.8-53`. Country
   mule images on `:DEV` are expected and the user typically answers
   `s`.

2. **Already-2.18 unctad services.** A line matching
   `image:\s*unctad/[^:]+:2\.18`. This usually means a previous
   partial upgrade. Flag every occurrence.

3. **Non-standard minio.** Either:
   - the file contains no `minio:` service block (search for
     `^  minio:` at indent 2), OR
   - the `minio:` block's `image:` is not exactly
     `image: minio/minio:latest`, OR
   - the `minio:` block's `test:` line is not exactly the expected
     `test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]`
     (allow whitespace variation around brackets and commas).

4. **Unexpected `EREGISTRATIONS_VERSION` value.** Any line matching
   `EREGISTRATIONS_VERSION=` whose RHS, after stripping surrounding
   double quotes, is not `2.17`.

5. **Unexpected `BUILD_TYPE` value.** Any line matching `BUILD_TYPE=`
   whose RHS, after stripping surrounding double quotes, is not
   `LIVE`.

If no anomalies are detected, print "No anomalies. Applying
transformations." and proceed.

If anomalies were detected and the user resolved them all (no `a`
answer), proceed to STEP 3 and apply the transformations only to the
expected occurrences (i.e. `unctad/*:2.17` lines, the standard minio
image/healthcheck, exactly `EREGISTRATIONS_VERSION=2.17`, and exactly
`BUILD_TYPE=LIVE`). Do not auto-rewrite anomalous lines.

## STEP 3: Apply the five transformations

Edit `<TARGET>` in place. Apply each rule across the whole file.
Preserve indentation and line endings exactly. Do not reformat
anything else.

**Rule 1 — Bump unctad image tags.**
For every line matching `^(\s*)image:\s*unctad/([^:\s]+):2\.17\s*$`,
replace `:2.17` with `:2.18`. Keep the leading whitespace and the
image name verbatim. Country-specific images on non-`:2.17` tags
(e.g. `unctad/mule3-kenya:DEV`) do not match and are not touched.

**Rule 2 — Swap minio image.**
Replace the line `    image: minio/minio:latest` (within the `minio:`
service block) with `    image: pgsty/minio:latest`. Preserve the
existing indentation (two-space, four-space, however it appears).

**Rule 3 — Replace minio healthcheck.**
Within the `minio:` service block, find the `test:` line that
contains `["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]`
and replace it with
`test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/9000'"]`.
Preserve the leading indentation of the original `test:` line.

**Rule 4 — Remove `EREGISTRATIONS_VERSION=2.17`.**
Delete every line whose stripped content is exactly
`- EREGISTRATIONS_VERSION=2.17` or `- "EREGISTRATIONS_VERSION=2.17"`
(with or without surrounding double quotes around the value). Typical
sites: `bpa-frontend` and `ds-backend`. Remove the entire line
including its leading whitespace and trailing newline — do not leave
a blank line behind.

**Rule 5 — Remove `BUILD_TYPE=LIVE`.**
Delete every line whose stripped content is exactly
`- BUILD_TYPE=LIVE` or `- "BUILD_TYPE=LIVE"`. Same line-removal rules
as Rule 4.

**Apply order:** rules 1 → 2 → 3 → 4 → 5. Each rule operates on the
file produced by the previous rule.

**Tooling.** Apply the edits using your file-editing tool of choice
(Edit/Write). Do not shell out to `sed -i` — macOS and Linux disagree
on the `-i` flag, and the skill must work on both.

When all five rules are applied, proceed to STEP 4.

## STEP 4: Post-transformation safety scan

After applying the five rules, scan the modified `<TARGET>` for any
remaining `2.17` token.

Run:

```bash
grep -n '2\.17' "$TARGET" || true
```

For every match, present it as an anomaly with the same
`(c)ontinue / (s)kip / (a)bort` prompt. `c` here means "leave it as
is, this `2.17` is intentional"; `s` is identical (anomaly is left
untouched); `a` rolls back: run
`git restore -- "$TARGET"` and exit.

The standard upgrade should leave **zero** `2.17` matches. A non-zero
count usually indicates either a comment, a non-standard env value,
or a missed image line — pausing for the user is correct.

When the user has resolved all matches (or there were none), proceed
to STEP 5.

## STEP 5: Diff review

Show the user the diff and ask for explicit approval before
committing.

1. Run `git --no-pager diff --no-color -- "$TARGET"` and print the
   output verbatim (do not summarise).
2. Ask: "Commit, push, and open PR? (y/N)"
3. Read the answer.
   - `y` (case-insensitive) — proceed to STEP 6.
   - Anything else — run `git restore -- "$TARGET"` and exit cleanly:
     "Aborted. No commit made."

## STEP 6: Branch, commit, push, open PR

1. **Compute the branch name.** `BRANCH=chore/upgrade-test-<country>-2.18`
   (use the country folder name from STEP 1).

2. **Check the branch does not already exist.**
   - Local: `git rev-parse --verify "$BRANCH" 2>/dev/null` should
     fail. If it succeeds, abort: "Branch $BRANCH already exists
     locally. Resolve manually."
   - Remote:
     `git ls-remote --exit-code --heads origin "$BRANCH" 2>/dev/null`
     should fail. If it succeeds, abort the same way.
   - On either failure, run `git restore -- "$TARGET"` so the working
     tree is clean again before exiting.

3. **Create the branch and commit.**

   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade test.<country> to 2.18"
   ```

4. **Push the branch.**

   ```bash
   git push -u origin "$BRANCH"
   ```

   If the push is rejected, leave the local commit in place, return
   to `master` (`git checkout master`), and tell the user: "Push
   rejected. The local branch $BRANCH still has the commit;
   investigate and push manually."

5. **Open the PR — branch on `HOST`.**

   Compose the body using the template in the *PR body template*
   reference at the bottom of this skill. Replace `<country>` and
   `<skipped>` (the list of anomaly kinds the user answered `s` for,
   if any — empty bullet "(none)" if zero).

   - If `HOST=github`:

     ```bash
     gh pr create \
       --base master \
       --head "$BRANCH" \
       --title "Upgrade test.<country> to 2.18" \
       --body "<body>"
     ```

     If `gh pr create` fails, leave the branch pushed and the local
     commit in place. Print the gh error and tell the user: "PR
     creation failed; the branch is pushed. Open the PR manually."

   - If `HOST=bitbucket`: skip CLI PR creation. Parse
     `<workspace>/<repo>` from `git remote get-url origin` (formats
     `git@bitbucket.org:<workspace>/<repo>.git` or
     `https://bitbucket.org/<workspace>/<repo>.git`) and print:

     ```
     Branch pushed: $BRANCH
     Open the PR via the Bitbucket web UI at:
     https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master
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
| Hard abort (no edits made) | not in git repo; not on master; dirty tree; `gh` missing on a GitHub origin; unsupported origin host; pull fails; user mistypes country twice; target file missing; branch already exists locally or on origin | Print failure reason, exit non-zero. |
| Clean exit (no edits made) | candidate scan finds zero files; selected file has zero `unctad/*:2.17` lines | Print "Nothing to upgrade" / "<country> is already on 2.18", exit 0. |
| Soft pause | any anomaly (pre-scan or post-scan); diff-review answered `N` | Wait for user input; on abort/restore, run `git restore -- "$TARGET"` and exit cleanly. |

Never retry, never silently fall back. Any unexpected failure: print
the error, exit, let the user re-run.

## Reference: PR body template

```
## Summary

Mechanical upgrade of `Conf-TEST/compose/<country>/docker-compose.yml`
from eRegistrations 2.17 to 2.18.

## Transformations applied

- Bumped every `unctad/<*>:2.17` image tag to `:2.18`.
- Swapped `minio/minio:latest` for `pgsty/minio:latest`.
- Replaced minio healthcheck with `CMD-SHELL bash -c 'echo > /dev/tcp/localhost/9000'`.
- Removed `EREGISTRATIONS_VERSION=2.17` from `bpa-frontend` and `ds-backend`.
- Removed `BUILD_TYPE=LIVE` from `bpa-frontend` and `ds-backend`.

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against the gambia 2.18 commit (`74c3b6c5`) — same shape, only country-specific lines differ.
```
