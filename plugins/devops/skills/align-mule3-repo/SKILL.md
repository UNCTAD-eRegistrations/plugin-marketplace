---
name: align-mule3-repo
description: >
  Align a freshly-imported `mule3-<country>` GitHub repo with the conventions
  shared by `mule3-benin` / `mule3-colombia`: GitHub Actions CI/CD (replacing
  any Jenkinsfile), Dockerfile that consumes a host-built artifact, npm
  `standard-version` sourced from the propagator's packages-branch tarball,
  `develop` as the default branch with a delete-protection ruleset, the
  `v4-development` org team with push, a one-time `mule-common` /
  `mule3-datamapping-connector` pom bump to current packages-branch versions,
  and PRs against `mule-common` and `mule3-datamapping-connector` adding the
  repo to their `propagate-version` consumer matrices so future bumps land
  automatically. Idempotent — detects what is already aligned and skips it.
  Use immediately after a mule3-<country> repo is created/imported on GitHub
  and before its first dev push, or whenever a mule3-<country> CI build fails
  with `mule-common <old> not found in packages branch`.
license: UNCTAD-Internal
compatibility: Run from inside a `mule3-<country>` working tree on GitHub origin (UNCTAD-eRegistrations org). Requires `gh` CLI (≥2.13) authenticated as a UNCTAD-eRegistrations org admin (needed for ruleset + team-grant + propagator-PR steps), git, and ssh access to GitHub. Does NOT migrate from Bitbucket — use `/bitbucket-jenkins-to-github-actions` first if the repo is still on Bitbucket.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(ls *), Bash(grep *), Bash(find *), Bash(mkdir *), Bash(cp *), Bash(mv *), Bash(rm *), Bash(diff *), Bash(sed *), Bash(awk *), Bash(base64 *), Bash(node *), Bash(sort *), Bash(head *), Bash(tail *), Bash(wc *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-06"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[--dry-run] [--reference=<repo>]"
  jira: "TOBE-17420"
---

# Align a `mule3-<country>` repo with the GitHub propagator ecosystem

You are aligning a freshly-imported `mule3-<country>` GitHub repository with the conventions shared by every other already-aligned `mule3-*` repo (canonical references: `mule3-benin`, `mule3-colombia`). The skill performs the **structural** work that turns "imported on GitHub but CI is broken / propagator doesn't know about us" into "first push to develop builds green and future mule-common / datamapping releases auto-bump us alongside the others".

This is **not** a Bitbucket → GitHub migration. If the repo is still on Bitbucket, run `/bitbucket-jenkins-to-github-actions` first; come back here once the GitHub remote exists.

## Invocation

```
/align-mule3-repo                        # Run inside the mule3-<country> working tree
/align-mule3-repo --dry-run              # Preview every change without mutating local files, GitHub, or other repos
/align-mule3-repo --reference=mule3-benin # Override the reference repo (default: mule3-benin)
```

The skill auto-detects the country slug from `package.json` `name` (`mule3-<country>`) and is idempotent — every step checks current state first and skips work that has already been done.

## Reference repo policy

Default reference is `mule3-benin`. It typically carries the latest TOBE-17420 propagated workflow fixes (git-lfs install/retry, mule-common + datamapping fetch via the dependency-propagator App). `mule3-colombia` is a valid alternative; older mule3-* repos are not because they may still be on Jenkins. If the reference repo's local clone is stale, `git -C <reference> fetch` it before reading.

The reference repo is the **only** source of truth for:
- `.github/workflows/ci-cd.yml` (scaffolded with country-name substitutions)
- `Dockerfile` shape (multi-stage builder removed, host-built artifact)
- `package.json` / `package-lock.json` `standard-version` source (`file:./vendor/standard-version.tgz`)

Do NOT invent these from memory — copy from disk.

## Phases

| # | Phase | Purpose |
|---|-------|---------|
| 0 | Pre-flight | gh auth, cwd is a mule3 repo on GitHub, reference repo exists |
| 1 | Discovery | Detect country slug, current default branch, presence of Jenkinsfile / workflow / pom versions; check propagator matrices |
| 2 | Local repo alignment | Generate workflow, drop Jenkinsfile, adapt Dockerfile, switch standard-version source, bump pom versions; one commit, push to develop |
| 3 | GitHub repo settings | `main` → `develop` rename; default branch; delete-protection ruleset; v4-development team push |
| 4 | Propagator integration | Open PR in `mule-common` and `mule3-datamapping-connector` adding the repo to each `propagate-version` consumer matrix |
| 5 | Verification | Watch the resulting CI run; report green/red; report propagator-PR URLs |

Mark each phase complete with `TodoWrite` as you progress.

---

## Phase 0: Pre-flight

### 0.1 Tool + auth check

```bash
# Required tools
which git gh node || { echo "MISSING tool — abort"; exit 1; }

gh auth status 2>&1 | head -5   # expect "Logged in to github.com"
ssh -T git@github.com 2>&1 | head -1   # expect "Hi <user>!"
```

### 0.2 Cwd sanity

Resolve the absolute path of the cwd, verify it's a git working tree, that the origin remote points at `github.com:UNCTAD-eRegistrations/mule3-*`, and that the current branch is clean (no uncommitted changes).

```bash
REPO_DIR=$(git rev-parse --show-toplevel)
cd "$REPO_DIR"

ORIGIN=$(git remote get-url origin)
case "$ORIGIN" in
  *github.com:UNCTAD-eRegistrations/mule3-*|*github.com/UNCTAD-eRegistrations/mule3-*) : ;;
  *) echo "Origin '$ORIGIN' is not a UNCTAD-eRegistrations GitHub mule3-* repo — abort"; exit 1 ;;
esac

git diff --quiet && git diff --cached --quiet || { echo "Working tree dirty — commit or stash first"; exit 1; }
```

If the origin is a Bitbucket remote, abort with: "Repo is still on Bitbucket. Run `/bitbucket-jenkins-to-github-actions` first."

### 0.3 Reference repo

The reference repo defaults to `mule3-benin`. Resolve its local path:

```bash
REFERENCE=${REFERENCE:-mule3-benin}     # picked up from --reference=<repo> arg
REF_DIR=$(dirname "$REPO_DIR")/$REFERENCE
[ -d "$REF_DIR/.github/workflows" ] || { echo "Reference repo $REF_DIR not found — clone it next to $REPO_DIR or pass --reference"; exit 1; }
git -C "$REF_DIR" fetch --quiet origin
```

### 0.4 Org admin probe (advisory)

```bash
gh api /user/memberships/orgs/UNCTAD-eRegistrations --jq '.role' 2>/dev/null \
  | grep -q admin || echo "WARNING: not an org admin — Phase 3 ruleset, default-branch change, and team grant may fail"
```

Non-admins can still complete Phase 2 (local repo alignment) and Phase 4 (PRs in other repos).

---

## Phase 1: Discovery

Detect the current state. Every fact gathered here is used to decide which Phase 2/3/4 steps actually need to run.

### 1.1 Country slug

```bash
COUNTRY=$(node -p "require('./package.json').name.replace(/^mule3-/, '')")
[ -n "$COUNTRY" ] || { echo "package.json 'name' did not start with mule3- — abort"; exit 1; }
echo "Country slug: $COUNTRY"
```

`COUNTRY` is the kebab-case suffix used in: `mule3-${COUNTRY}` (Docker image, package.json, pom artifactId, workflow cache keys, target zip), and the matrix entry in propagator workflows.

### 1.2 Default branch

```bash
CURRENT_DEFAULT=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
LOCAL_BRANCH=$(git branch --show-current)
echo "Default branch (remote): $CURRENT_DEFAULT"
echo "Local branch: $LOCAL_BRANCH"
```

Other mule3-* repos default to `develop`. If `CURRENT_DEFAULT=main`, Phase 3.1 will rename.

### 1.3 Workflow + Jenkinsfile presence

```bash
HAS_WORKFLOW=$([ -f .github/workflows/ci-cd.yml ] && echo yes || echo no)
HAS_JENKINSFILE=$([ -f Jenkinsfile ] && echo yes || echo no)
```

### 1.4 Dockerfile shape

The aligned Dockerfile has **no** `FROM ... as builder` stage and copies the artifact via `COPY ./target/mule3-${COUNTRY}-$VERSION.zip ./apps`.

```bash
HAS_BUILDER_STAGE=$(grep -q '^FROM .* as builder' Dockerfile && echo yes || echo no)
DOCKERFILE_USES_HOST_ARTIFACT=$(grep -q "^COPY \./target/mule3-${COUNTRY}-\$VERSION\.zip" Dockerfile && echo yes || echo no)
```

### 1.5 `package.json` standard-version source

```bash
SV_SOURCE=$(node -p "require('./package.json').devDependencies['standard-version']")
case "$SV_SOURCE" in
  file:./vendor/standard-version.tgz) PKG_ALIGNED=yes ;;
  *bitbucket.org*|*) PKG_ALIGNED=no ;;
esac
```

### 1.6 Pom versions vs packages-branch availability

```bash
MULE_COMMON_VER=$(grep -A6 '<artifactId>mule-common</artifactId>' pom.xml | grep '<version>' | head -1 | sed -E 's/.*<version>(.+)<\/version>.*/\1/')
DATAMAPPING_VER=$(grep -A6 '<artifactId>datamapping</artifactId>' pom.xml | grep '<version>' | head -1 | sed -E 's/.*<version>(.+)<\/version>.*/\1/')

# Latest published in packages branch
LATEST_MC=$(gh api repos/UNCTAD-eRegistrations/mule-common/contents/org/unctad/eregistrations/mule-common?ref=packages \
              --jq '.[].name' | grep -E '^[0-9]' | sort -V | tail -1)
LATEST_DM=$(gh api repos/UNCTAD-eRegistrations/mule3-datamapping-connector/contents/org/unctad/eregistrations/mule/modules/datamapping?ref=packages \
              --jq '.[].name' | grep -E '^[0-9]' | sort -V | tail -1)

echo "mule-common:    pom=$MULE_COMMON_VER  packages-latest=$LATEST_MC"
echo "datamapping:    pom=$DATAMAPPING_VER  packages-latest=$LATEST_DM"
```

Phase 2 will bump if `pom < latest` AND `pom` is not in the packages branch (the CI fetch would fail). The decision rule: bump iff the pom version cannot be `gh api ...?ref=packages`-resolved.

### 1.7 Propagator matrix membership

```bash
gh api repos/UNCTAD-eRegistrations/mule-common/contents/.github/workflows/ci-cd.yml \
  --jq .content | base64 -d | grep -q "          - mule3-${COUNTRY}$" \
  && IN_MC_MATRIX=yes || IN_MC_MATRIX=no

gh api repos/UNCTAD-eRegistrations/mule3-datamapping-connector/contents/.github/workflows/ci-cd.yml \
  --jq .content | base64 -d | grep -q "          - mule3-${COUNTRY}$" \
  && IN_DM_MATRIX=yes || IN_DM_MATRIX=no
```

### 1.8 GitHub-side state (default branch already covered in 1.2)

```bash
HAS_DELETE_RULESET=$(gh api repos/UNCTAD-eRegistrations/mule3-${COUNTRY}/rulesets \
                       --jq '.[] | select(.name=="delete protection") | .id' \
                     | head -1 | grep -q . && echo yes || echo no)

HAS_V4_TEAM=$(gh api repos/UNCTAD-eRegistrations/mule3-${COUNTRY}/teams \
                --jq '.[] | select(.slug=="v4-development") | .permission' \
              | grep -q . && echo yes || echo no)
```

### 1.9 Print discovery report and the planned actions

Show the user a compact table:

| Concern | State | Will do |
|---|---|---|
| Country slug | `${COUNTRY}` | — |
| Default branch | `${CURRENT_DEFAULT}` | rename to `develop` if `main` |
| `.github/workflows/ci-cd.yml` | `${HAS_WORKFLOW}` | scaffold from `${REFERENCE}` if missing |
| `Jenkinsfile` | `${HAS_JENKINSFILE}` | delete if present |
| Dockerfile builder stage | `${HAS_BUILDER_STAGE}` | drop if present |
| Dockerfile host artifact | `${DOCKERFILE_USES_HOST_ARTIFACT}` | rewrite COPY if missing |
| `package.json` standard-version | `${SV_SOURCE}` | switch to file:./vendor if not |
| `pom.xml` mule-common | `${MULE_COMMON_VER}` | bump to `${LATEST_MC}` if outside packages branch |
| `pom.xml` datamapping | `${DATAMAPPING_VER}` | bump to `${LATEST_DM}` if outside packages branch |
| mule-common matrix | `${IN_MC_MATRIX}` | open PR if no |
| datamapping matrix | `${IN_DM_MATRIX}` | open PR if no |
| delete-protection ruleset | `${HAS_DELETE_RULESET}` | create if no |
| v4-development team push | `${HAS_V4_TEAM}` | grant if no |

Confirm with the user before continuing (skip the prompt under `--dry-run`).

---

## Phase 2: Local repo alignment

All 2.x sub-steps are idempotent. Run only the ones flagged "yes" in the Phase 1 plan. Stage everything together and commit once at the end of Phase 2.

### 2.1 Scaffold `.github/workflows/ci-cd.yml`

If `HAS_WORKFLOW=no`:

```bash
mkdir -p .github/workflows
sed "s/mule3-${REFERENCE#mule3-}/mule3-${COUNTRY}/g" \
  "$REF_DIR/.github/workflows/ci-cd.yml" > .github/workflows/ci-cd.yml
```

Verify the substitution was complete:

```bash
grep -n "mule3-${REFERENCE#mule3-}" .github/workflows/ci-cd.yml \
  && { echo "Reference repo name leaked through — abort"; exit 1; }
grep -nE "mule3-${COUNTRY}" .github/workflows/ci-cd.yml | head    # should hit DOCKER_IMAGE, cache key, ephemeral image
```

Self-check the YAML with `actionlint` if available; warnings about custom self-hosted labels (`linux,build,normal`, `linux,build,heavy`, `linux,jenkins`) are expected — they match the org's runner pool and are present in the reference workflow too.

### 2.2 Delete `Jenkinsfile`

```bash
[ -f Jenkinsfile ] && rm Jenkinsfile
```

### 2.3 Adapt `Dockerfile`

Two targeted edits:

**a)** Drop the multi-stage builder. The pre-aligned shape is:

```Dockerfile
FROM maven:3-eclipse-temurin-8 as builder
WORKDIR /usr/src/app
COPY pom.xml mule-project.xml ./
COPY src ./src
RUN mvn -DlightweightPackage -Dfile.encoding=UTF-8 clean package


FROM eclipse-temurin:8-jre-jammy
```

becomes:

```Dockerfile
FROM eclipse-temurin:8-jre-jammy
```

**b)** Change the artifact COPY from the builder stage to the host:

```Dockerfile
COPY --from=builder /usr/src/app/target/mule3-${COUNTRY}-$VERSION.zip ./apps
```

becomes:

```Dockerfile
COPY ./target/mule3-${COUNTRY}-$VERSION.zip ./apps
```

After both edits, the Dockerfile should diff-clean against `$REF_DIR/Dockerfile` modulo the country-suffixed zip filename.

### 2.4 Switch `standard-version` source in `package.json` + lock

In `package.json`:

```diff
-    "standard-version": "git+ssh://git@bitbucket.org/unctad/standard-version.git",
+    "standard-version": "file:./vendor/standard-version.tgz",
```

In `package-lock.json` two corresponding edits:

```diff
-        "standard-version": "git+ssh://git@bitbucket.org/unctad/standard-version.git",
+        "standard-version": "file:./vendor/standard-version.tgz",
```

```diff
-      "resolved": "git+ssh://git@bitbucket.org/unctad/standard-version.git#<sha>",
+      "resolved": "file:vendor/standard-version.tgz",
```

Both lockfile edits are needed — without the second, `npm ci` would resolve from the SSH URL and fail in the runner. Do not regenerate the lockfile (no local network calls); the surgical edits keep the rest of the dep tree exactly as the reference repo has it.

### 2.5 Bump `pom.xml` `mule-common` and `datamapping` if outside packages branch

The pom comments say "Do not update this version manually!!!". That rule assumes the propagator ran. For a freshly-imported repo that the propagator does not yet know about (Phase 4 fixes that going forward), the **first** alignment is a one-time bump to whatever the packages branch currently publishes. Keep the comments intact.

```bash
# Only bump if pom version isn't in the packages branch
if ! gh api repos/UNCTAD-eRegistrations/mule-common/contents/org/unctad/eregistrations/mule-common/${MULE_COMMON_VER}?ref=packages >/dev/null 2>&1; then
  sed -i "s|<version>${MULE_COMMON_VER}</version>|<version>${LATEST_MC}</version>|" pom.xml
fi
if ! gh api repos/UNCTAD-eRegistrations/mule3-datamapping-connector/contents/org/unctad/eregistrations/mule/modules/datamapping/${DATAMAPPING_VER}?ref=packages >/dev/null 2>&1; then
  sed -i "s|<version>${DATAMAPPING_VER}</version>|<version>${LATEST_DM}</version>|" pom.xml
fi
```

Use the surrounding XML context for `sed` so you don't accidentally rewrite an unrelated `<version>` line that happens to match. Safer pattern: read both relevant `<dependency>` blocks (each is artifactId + comment + version) with `Edit` rather than `sed`.

> **Compatibility note:** Across mule3-* repos that this skill targets, the source code is XML flows + properties + at most a single `JMXMetric.java` (with no mule-common imports) — so a mule-common minor-version jump is mechanical. If the target repo grows Java code that imports `org.unctad.eregistrations.mule_common.*`, this assumption breaks and the user must manually validate. Print a warning if `find src/main/java -name '*.java' | xargs grep -l 'mule_common\|mule.common'` returns anything.

### 2.6 Commit + push

Stage the changed files explicitly (never `git add -A`):

```bash
git add .github/workflows/ci-cd.yml Dockerfile package.json package-lock.json pom.xml
[ "$HAD_JENKINSFILE" = yes ] && git rm Jenkinsfile
git pull --ff-only

git commit -m "feat: align repo with mule3-* GH structure (CI/CD, Docker, deps) TOBE-17420"

# Push goes to current branch (likely 'main' until Phase 3.1 renames it).
# If we are still on main, Phase 3.1 will perform the rename + push.
# If we are already on develop, push now.
[ "$LOCAL_BRANCH" = develop ] && git push origin develop
```

> Under `--dry-run`, print the staged diff via `git diff --cached --stat` and stop here without committing.

---

## Phase 3: GitHub repo settings

### 3.1 `main` → `develop` (and create master if asked)

If `CURRENT_DEFAULT=main`:

```bash
git branch -m main develop
git push -u origin develop
gh repo edit "UNCTAD-eRegistrations/mule3-${COUNTRY}" --default-branch develop
git push origin --delete main
git remote set-head origin -a
```

> `master` is the live-release branch in mule3-* convention but creating it from a freshly-imported `develop` is a separate decision (it should hold the first live release commit, not a placeholder). Do **not** push `master` as part of this skill — surface it as a follow-up in the final report.

### 3.2 Delete-protection ruleset

If `HAS_DELETE_RULESET=no`, POST the canonical payload:

```bash
gh api repos/UNCTAD-eRegistrations/mule3-${COUNTRY}/rulesets -X POST --input - <<'EOF'
{
  "name": "delete protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "refs/heads/main",
        "refs/heads/master",
        "refs/heads/develop",
        "refs/heads/beta",
        "refs/heads/release-candidate",
        "refs/heads/release/*"
      ]
    }
  },
  "rules": [{"type": "deletion"}],
  "bypass_actors": []
}
EOF
```

The include list intentionally still mentions `main` — it costs nothing to keep, matches benin/colombia, and protects accidentally-recreated `main` branches.

### 3.3 `v4-development` team push permission

If `HAS_V4_TEAM=no`:

```bash
gh api -X PUT \
  orgs/UNCTAD-eRegistrations/teams/v4-development/repos/UNCTAD-eRegistrations/mule3-${COUNTRY} \
  -f permission=push
```

This single call cascades write access to every member of the team (typically 3-5 mule developers who otherwise show up as `read` on a fresh repo).

> Frontend repos additionally grant `v4-fe-development` push — but mule3-* are pure backend, so only `v4-development` applies here.

---

## Phase 4: Propagator integration (PRs in other repos)

Both source libraries (`mule-common` and `mule3-datamapping-connector`) keep a hardcoded `consumer:` matrix in their `propagate-version` job. We open one PR each, adding `mule3-${COUNTRY}` in alphabetical position. Both base against `develop`.

### 4.1 mule-common PR

If `IN_MC_MATRIX=no`:

```bash
MC_DIR=$(dirname "$REPO_DIR")/mule-common
# Clone if missing
[ -d "$MC_DIR" ] || git clone git@github.com:UNCTAD-eRegistrations/mule-common.git "$MC_DIR"

git -C "$MC_DIR" checkout develop
git -C "$MC_DIR" pull --ff-only
git -C "$MC_DIR" checkout -b "feature/add-mule3-${COUNTRY}-consumer"
```

Edit `$MC_DIR/.github/workflows/ci-cd.yml` — find the `consumer:` block under the `propagate-version` job and add `- mule3-${COUNTRY}` in alphabetical position. The block is uniquely identifiable by its preceding "Only repos already on GitHub" comment block; don't grep for `consumer:` blindly because matrix definitions appear elsewhere.

```bash
git -C "$MC_DIR" add .github/workflows/ci-cd.yml
git -C "$MC_DIR" commit -m "feat: add mule3-${COUNTRY} to propagate-version consumer matrix"
git -C "$MC_DIR" push -u origin "feature/add-mule3-${COUNTRY}-consumer"

gh pr create -R UNCTAD-eRegistrations/mule-common \
  --base develop --head "feature/add-mule3-${COUNTRY}-consumer" \
  --title "feat: add mule3-${COUNTRY} to propagate-version consumer matrix" \
  --body "$(see body template below)"
```

PR body template (substitute `${COUNTRY}`, `${LATEST_MC}`):

```markdown
## Summary
Adds `mule3-${COUNTRY}` to the `propagate-version` matrix so future mule-common releases auto-bump its `pom.xml` alongside benin and colombia.

## Why
mule3-${COUNTRY} has been migrated to GitHub Actions but was never in the propagator matrix, so its pom was stuck at the version it was forked at. CI fails because that old version is no longer in the `packages` branch (only recent versions retained). Burundi's pom has been one-time bumped to ${LATEST_MC} in mule3-${COUNTRY}'s own repo (separate commit); this PR closes the loop so propagation works automatically going forward.

## Test plan
- [ ] Next mule-common master push opens a propagator PR in mule3-${COUNTRY} as well as in the existing consumers
```

### 4.2 mule3-datamapping-connector PR

Mirror Phase 4.1 against `mule3-datamapping-connector`, substituting the artifact id, latest version, and clone URL accordingly. Same branch name, same body shape (replace "mule-common" with "mule3-datamapping-connector" and `${LATEST_MC}` with `${LATEST_DM}`).

### 4.3 Merging

By default, **do not** auto-merge. The user merges the PRs manually after CI passes on each. Surface the PR URLs in the final report.

If the user explicitly asks to merge ("merge the PRs"), squash-merge with branch deletion:

```bash
gh pr merge <pr-number> -R UNCTAD-eRegistrations/mule-common --squash --delete-branch
gh pr merge <pr-number> -R UNCTAD-eRegistrations/mule3-datamapping-connector --squash --delete-branch
```

Switch the local clones back to `develop` afterwards (the feature branches will have been deleted on the remote).

---

## Phase 5: Verification

### 5.1 Watch the CI run on develop

```bash
sleep 5    # let the push register
gh run list -R "UNCTAD-eRegistrations/mule3-${COUNTRY}" -L 1
```

If the build is `in_progress`, do **not** poll-loop locally — trust the run notification or ask the user. If the build has already finished and is `failure`, examine the failed job:

```bash
gh run view <run-id> -R "UNCTAD-eRegistrations/mule3-${COUNTRY}"
```

The most common failure on a freshly-aligned repo is "mule-common <version> not found in packages branch" — this means the Phase 2.5 pom bump didn't fire (or was bumped to a version that's not in the packages branch). Fix: re-run Phase 1.6 → 2.5.

### 5.2 Final report

Print to the user:

- Summary of what was changed locally (commit SHA, files touched)
- Summary of GitHub repo settings updates (default branch, ruleset id, team)
- The two propagator-PR URLs (mule-common, datamapping)
- Any **deferred** items the user should decide:
  - Whether to push a `master` branch now (skill does not push it autonomously)
  - Whether to merge the two propagator PRs immediately or wait for review
  - Any pre-existing items the skill found but did not touch (e.g. legacy `release/*` branches missing protection that benin/colombia have)
- The CI run URL

---

## Notes & gotchas

- **`v4-development` cascade.** After Phase 3.3, users like `MrJarkko`, `krixerx`, `aigark` flip from `read` to `write` on the repo. If they don't, double-check the team slug — it really is `v4-development`, not `v4-developers` or `v4-dev`.
- **Lockfile mismatch tolerated by colombia.** As of 2026-05, `mule3-colombia/package-lock.json` still references the bitbucket SSH URL for `standard-version` while the package.json points at the vendor tarball. CI works because the vendor tarball is downloaded before `npm ci` runs and `npm ci` happens to tolerate this specific kind of `file:` mismatch. **Benin's lockfile is correctly updated and is the better template** — Phase 2.4 mirrors benin, not colombia.
- **`vendor/standard-version.tgz` is not in the repo.** The CI workflow fetches it on demand from `UNCTAD-eRegistrations/standard-version` `packages` branch via the dependency-propagator App. Anyone running `npm ci` outside CI must fetch it first.
- **Pom comments stay.** Even though Phase 2.5 ignores the "Do not update manually!!!" comment for the one-time alignment, leave the comments intact — once the PRs in Phase 4 are merged, the propagator owns subsequent bumps and the comments accurately describe the steady state.
- **`actionlint` warnings.** The reference workflow uses self-hosted runner labels (`linux, build, normal`, `linux, build, heavy`, `linux, jenkins`) that `actionlint` doesn't know unless you ship an `actionlint.yaml`. Don't fix these — they're load-bearing.
- **Concurrency.** This skill is safe to run twice on the same repo — every step is gated on the discovery flags. The second run is a no-op except for the final verification pass.

## Argument summary

| Argument | Effect |
|---|---|
| `--dry-run` | All Phase 2/3/4 mutations become previews (`git diff --cached --stat`, `gh api ... --silent --include` to see status without effect, no commits, no PRs). Discovery and final report run normally. |
| `--reference=<repo>` | Use a different reference repo than `mule3-benin`. Must be a sibling clone with an aligned workflow. |

## Out of scope (use other skills/manual steps)

- Bitbucket → GitHub history migration → `/bitbucket-jenkins-to-github-actions`
- Helm chart bumps for the new repo → manual edit in `eregistrations-helm`
- First `master` branch / first live release → manual, after the first release/* branch is cut
- Source-code-level mule-common API migration (would only matter if the repo grows Java code) → manual
- Adding the repo to `eregistrations-helm` umbrella — this skill stays inside the mule3 repo + the two propagator source repos.
