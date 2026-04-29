# Lessons Learned: Migration Failures Analysis

This document captures critical failures encountered during migrations and their root causes. **READ THIS BEFORE EVERY MIGRATION.**

---

## Reference Migrations

**Start with the canonical template** ([`workflow-template.yml`](workflow-template.yml)) — it encodes the post-mule3-benin alignment with ds-backend and closes the 12 known structural gaps. Then consult the table below for repo-type-specific `<BUILD_STEP>` recipes.

| Reference | Best for | Workflow |
|-----------|---------|----------|
| **Canonical template** (this skill) | Default starting point — covers the 7 core jobs; uncomment optional add-ons as needed | [`workflow-template.yml`](workflow-template.yml) |
| **DS-Backend** (gold standard) | Python (Django); full pattern with helm-chart-update + run-tests + qodana + artifact-cleanup | [`UNCTAD-eRegistrations/ds-backend` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/ds-backend/blob/develop/.github/workflows/ci-cd.yml) |
| **mule3-benin** (post-`8ff9234`) | Java/Maven `<BUILD_STEP>` reference (`mvn package` + SSH agent + bitbucket clone of `eregistrations-tools`); also a known-good Mule3 ESB workflow | [`UNCTAD-eRegistrations/mule3-benin` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/mule3-benin/blob/develop/.github/workflows/ci-cd.yml) |
| BPA-Backend | Java / Spring Boot (Maven build); `standard-version` bump tooling syncs to `pom.xml` via `xml-js`. **Caveat:** workflow predates the alignment fix and may still embody some of the 12 gaps (see Critical Failure #9) — cross-check against the canonical template before copying. | [`UNCTAD-eRegistrations/BPA-Backend` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/BPA-Backend/blob/develop/.github/workflows/ci-cd.yml) |
| Mule4 | Maven `mule-application` shape + identical `standard-version`/`xml-js` tooling. Same caveat as BPA-Backend. | [`UNCTAD-eRegistrations/Mule4` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/Mule4/blob/develop/.github/workflows/ci-cd.yml) |
| ActiveMQ | **Only the helm-chart-update job pattern** is endorsed. Do NOT use the rest as a reference. | [`UNCTAD-eRegistrations/ActiveMQ` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/ActiveMQ/blob/develop/.github/workflows/ci-cd.yml) |

> ⚠️ The pre-alignment workflows (BPA-Backend, Mule4, ActiveMQ) were the previous "reference implementations" and likely still embody some of the 12 structural gaps documented in Critical Failure #9. Until those repos are separately audited and fixed, **prefer the canonical template + mule3-benin (post-fix) + ds-backend** as your sources.

---

## Critical Failure #1: Skipped BLOCKING Step 3.2.0 (Feature Parity Verification)

### What SKILL.md says (Phase 3, Step 3.2.0 — Feature Parity Verification):
```
### Step 3.2.0: BLOCKING - Feature Parity Verification
THIS STEP IS MANDATORY BEFORE GENERATING ANY WORKFLOW

BLOCKING: Do NOT proceed to Step 3.2.1 until:
- ALL stages are mapped to ci-cd.yml jobs/steps
- ALL git clone operations are accounted for
- ALL shell commands are translated
```

### What went wrong:
Skipped this step entirely, resulting in missing `eregistrations-tools` clone step.

### Impact:
Docker build failed with "eregistrations-tools/scripts/parse-docker-secret/script.sh not found"

### Prevention:
**NEVER generate ci-cd.yml without completing Feature Parity Table first.**

---

## Critical Failure #2: Wrong Git User Configuration

### What critical-patterns.md says (§9 Git User Configuration):
```yaml
git config --global user.email "github-actions[bot]@users.noreply.github.com"
git config --global user.name "GitHub Actions Bot"

# Never Use:
# git config user.email "actions@github.com" (wrong email)
# git config user.name "GitHub Actions" (inconsistent name)
# Non-global config (use --global flag)
```

### What went wrong:
```yaml
git config user.email "ci@github.com"  # WRONG email
git config user.name "GitHub Actions"  # WRONG name, no --global
```

### Impact:
Commits appeared as `gfidlab-ci-user` instead of `GitHub Actions Bot`

### Prevention:
**Copy git config EXACTLY from critical-patterns.md. Use --global flag.**

---

## Critical Failure #3: Wrong Version Bump Retry Pattern

### What critical-patterns.md says (§5 npm Version Bump Script Pattern):
```bash
for i in $(seq 0 $((MAX_RETRIES - 1))); do
  OLD_VERSION=$(node -p "require('./package.json').version")

  git checkout $BRANCH_NAME
  git reset --hard origin/$BRANCH_NAME
  git pull origin $BRANCH_NAME

  if npm run patch-release; then
    git pull origin $BRANCH_NAME  # Pull AFTER successful bump
    NEW_VERSION=$(node -p "require('./package.json').version")
    exit 0
  fi
done
```

### What went wrong:
Used `while` loop, different reset logic, no pull after bump.

### Impact:
Version bump succeeded but downstream jobs didn't get the bumped version.

### Prevention:
**Copy version bump pattern EXACTLY from critical-patterns.md.**

---

## Critical Failure #4: Ignored Reference Implementations

### What critical-patterns.md says (§16 Reference Implementations):
```
See existing workflows for correct style (pick closest precedent):
- UNCTAD-eRegistrations/Mule4       → .github/workflows/ci-cd.yml  (closest for Mule3 toolchain shape; runtime + helm differ)
- UNCTAD-eRegistrations/DS-Backend  → .github/workflows/ci-cd.yml  (Python/Django + standard-version bump)
- UNCTAD-eRegistrations/BPA-Backend → .github/workflows/ci-cd.yml  (Java/Spring Boot Maven build; xml-js syncs version to pom.xml)
```

### What went wrong:
Created custom patterns instead of copying from working references.

### Impact:
Every pattern deviation caused a different failure.

### Prevention:
**ALWAYS read DS-Backend ci-cd.yml first. Copy patterns verbatim.**

---

## Critical Failure #5: No Progress Tracking with TodoWrite

### What SKILL.md says (Progress Tracking table):
```
Initialize with TodoWrite at start of migration:
| # | Checkpoint | Phase |
|---|------------|-------|
| 1 | Complete pre-flight validation | Phase 0 |
| 2 | Capture state snapshot + detect repo type | Phase 0.5 |
| 7 | **BLOCKING: Feature parity verification** | Phase 3 |
| 11 | Apply branch deletion protection ruleset | Phase 4.5 |
| 13 | **MANDATORY: Run validation suite** | Phase 5.5 |
...
Mark each complete as you progress.
```

### What went wrong:
Used ad-hoc todo lists, not the prescribed checklist.

### Impact:
Lost track of mandatory steps, skipped BLOCKING verification.

### Prevention:
**Use EXACTLY the 13-item TodoWrite checklist from SKILL.md (the canonical list — never substitute an older count).**

---

## Critical Failure #6: Incomplete Branch Synchronization

### What happened:
When syncing ci-cd.yml from develop to release/2.17, only the workflow file was synced. Did NOT check what other files were different.

### What should have been done:
```bash
git diff develop..release/2.17 --name-only
```
This would have shown package.json was also different.

### Impact:
Version bump ran but never pushed because package.json on release/2.17 was missing the `git push` command in the release scripts.

### Why this is critical:
This failure occurred IMMEDIATELY after creating documentation about checking feature parity. The same principle (verify ALL differences) was not applied to branch synchronization.

### Prevention:
**ALWAYS diff branches before syncing. See ALL differences, not just the file you think matters.**

```bash
# Before ANY branch sync, run:
git diff source_branch..target_branch --name-only

# For each different file, understand WHY it's different:
git diff source_branch..target_branch -- <file>
```

---

## Critical Failure #7: Docker Tag Uses Pre-Bump Version (REPEATED 6+ TIMES)

### What happens:
When the workflow bumps version (e.g., 2.17.1 → 2.17.2), the Docker image gets tagged with the OLD version (2.17.1) instead of the NEW version (2.17.2).

### Why it happens:
The `set-build-variables` job runs FIRST and captures VERSION/TAG_NAME. Then `bump-version` runs and increments the version. But `build-and-push-docker` still uses the pre-computed TAG_NAME from `set-build-variables`.

### The broken pattern:
```yaml
# In set-build-variables (runs BEFORE bump):
VERSION=$(node -p "require('./package.json').version")  # 2.17.1
echo "tag_name=$VERSION" >> $GITHUB_OUTPUT  # Captures OLD version

# In build-and-push-docker (runs AFTER bump):
TAG_NAME: ${{ needs.set-build-variables.outputs.tag_name }}  # Still 2.17.1!
docker push unctad/clamav:$TAG_NAME  # Pushes wrong tag
```

### The correct pattern:
```yaml
# In build-and-push-docker, RECOMPUTE version after pulling bumped code:
- name: Pull latest (in case version was bumped)
  run: git pull || true

- name: Get current version and compute tag
  id: version
  env:
    BRANCH_NAME: ${{ needs.set-build-variables.outputs.branch_name }}
    PRE_TAG_NAME: ${{ needs.set-build-variables.outputs.tag_name }}
  run: |
    VERSION=$(node -p "require('./package.json').version")
    MINOR_TAG=$(node -p "require('./package.json').version.substring(0, require('./package.json').version.lastIndexOf('.'))")
    echo "version=$VERSION" >> $GITHUB_OUTPUT
    echo "minor_tag=$MINOR_TAG" >> $GITHUB_OUTPUT

    # For release/* and master, use fresh version; otherwise use pre-computed tag
    if [[ "$BRANCH_NAME" == release/* || "$BRANCH_NAME" == "master" ]]; then
      echo "tag_name=$VERSION" >> $GITHUB_OUTPUT
    else
      echo "tag_name=$PRE_TAG_NAME" >> $GITHUB_OUTPUT
    fi

- name: Build and push Docker image
  env:
    TAG_NAME: ${{ steps.version.outputs.tag_name }}  # Uses FRESH version
    VERSION: ${{ steps.version.outputs.version }}
    MINOR_TAG: ${{ steps.version.outputs.minor_tag }}
```

### Prevention:
**For release/* and master branches, ALWAYS recompute VERSION and TAG_NAME in the build job AFTER git pull, not from set-build-variables outputs.**

---

## Critical Failure #8: Docker Build Skipped When Version Bump Enabled

### What happens:
When the workflow bumps version on `develop` or `release/*`, the Docker build job is SKIPPED entirely because `SHOULD_BUILD` incorrectly depends on `SHOULD_BUMP`.

### Why it happens:
The workflow logic checks `SHOULD_BUMP == "false"` before setting `SHOULD_BUILD="true"`:
```bash
develop)
  if [[ "$SHOULD_BUMP" == "false" && "$SHOULD_HELM" == "false" ]]; then
    SHOULD_BUILD="true"
  fi
```

This means: if version bump is enabled, Docker build is disabled. But we want BOTH to happen.

### The difference from Jenkins:
In Jenkins, the pushed `chore(release):` commit would trigger a NEW pipeline where `SHOULD_BUMP=false`, so Docker builds in the second run. GitHub Actions doesn't trigger new runs from GITHUB_TOKEN commits (anti-loop protection), so Docker never builds.

### The correct pattern (from BPA-Backend):
`SHOULD_BUILD` and `SHOULD_BUMP` must be **independent flags**:
```bash
develop|feature/*)
  if [[ "$SHOULD_HELM" == "false" ]]; then
    SHOULD_BUILD="true"  # No SHOULD_BUMP check - job dependency handles order
  fi
```

### Why job dependencies handle the order:
```yaml
build-and-push-docker:
  needs: [set-build-variables, bump-version]
  if: |
    always() &&
    needs.set-build-variables.outputs.SHOULD_BUILD == 'true' &&
    (needs.bump-version.result == 'success' || needs.bump-version.result == 'skipped')
```

The `always()` + `needs.bump-version.result` check ensures:
- Build waits for version bump to complete
- Build proceeds even if bump was skipped (chore commits)
- Build uses the latest code (via git pull in the job)

### Prevention:
**NEVER make SHOULD_BUILD depend on SHOULD_BUMP. Use job dependencies to control execution order.**

---

## Critical Failure #9: Heavy Runner Missing Node + 12 Structural Gaps (mule3-benin migration, 2026-04)

### What happened:

The mule3-benin migration generated a `ci-cd.yml` that combined `mvn` build, `docker build`, and final `docker push` into a single `build-and-push-docker` job on `[self-hosted, linux, build, heavy]`. The first CI run on `develop` failed at step "Get current version" with `Process completed with exit code 127` — the heavy runner's image does NOT have `node` pre-installed, so `node -p "require('./package.json').version"` could not run.

The audit that followed (mule3-benin's `ci-cd.yml` vs ds-backend's `ci-cd.yml`) surfaced **12 distinct structural gaps**:

| # | Gap | Evidence in mule3-benin |
|---|---|---|
| A | Heavy runner missing node | `node -p` on `[..., heavy]` → exit 127 |
| B | Single build-and-push-docker job | one job did mvn + docker build + final push |
| C | `feature/*` collides with develop's `DEV` | `develop\|feature/*) TAG_NAME="DEV"` |
| D | `release/*` test-RC convention | `TAG_NAME="${RELEASE_VERSION}-RC"; ENV="test"` |
| E | Version bump only on develop | `if [[ "$BRANCH_NAME" == "develop" ]]` |
| F | Missing `actions/setup-node@v4` | implicit reliance on pre-installed node |
| G | Job named `tag-production` | (org convention is `tag-release`) |
| H | Master tag `X.Y.Z` (no prefix) | `git tag "$VERSION"` |
| I | No npm cache | bare `npm ci` per CI run |
| J | notify-failure didn't clean ephemeral | (ephemeral wasn't even used) |
| K | trigger-jenkins-deploy missed release/* | first conditional was `develop \|\| feature/*` |
| L | Final push from heavy worker | `docker push` directly from heavy job |

### Resolution:

Two commits on mule3-benin's `develop`:
- `877107f feat: split build/push, fix branch tagging, align with ds-backend TOBE-17420` — closed gaps A, B, C, D, E, F, G, J, K, L.
- `8ff9234 feat: cache npm in bump-version, prefix master tags with v TOBE-17420` — closed gaps H, I.

The skill itself was then updated (this PR) to bundle a canonical [`workflow-template.yml`](workflow-template.yml) that encodes all 12 fixes, plus updates to [`critical-patterns.md`](critical-patterns.md) §§24–31 and [`troubleshooting.md`](troubleshooting.md) "Symptom: exit code 127 in version-reading step".

### Root cause (skill-level):

The skill operated as a **step-by-step guide** rather than a **template generator**. SKILL.md Phase 3 listed job names but provided full templates for only 2 of 7 core jobs. Users were directed to copy from "reference implementations" (Mule4, ActiveMQ) that were themselves never audited against ds-backend's pattern. mule3-benin's broken patterns were a faithful copy of ActiveMQ's broken patterns.

### Prevention:

1. **Use the canonical template** — `cp reference/workflow-template.yml .github/workflows/ci-cd.yml` is now Step 3.2.1's first action. Hand-authoring is forbidden.
2. **Run the GATE 3-4 self-audit grep** — it checks for all 12 canonical patterns AND flags deprecated job names (`tag-production`, `build-and-push-docker`).
3. **Treat pre-alignment workflows (BPA-Backend, Mule4, ActiveMQ) as historical** — see "Reference Migrations" table at the top of this file. Use them only for `<BUILD_STEP>` recipes, not for full-workflow patterns.

---

## Root Cause Summary - DEEPER ANALYSIS

### Surface-Level Diagnosis (Previous)
"Treated skill documentation as guidelines instead of mandatory procedure."

### Actual Root Cause
**I don't read documentation BEFORE acting. I generate solutions from general knowledge, then fail, then get told about documentation.**

### Pattern of Failure
1. User requests task
2. I immediately start generating solution from my training
3. Solution fails
4. User points to documentation that would have prevented failure
5. I fix the specific issue
6. I move to next step and repeat the pattern

### Evidence
- Failure #1-5: Didn't read skill documentation before generating workflow
- Failure #6: Didn't diff branches before syncing (even after writing docs about verification)

### The Behavioral Loop
```
Task → Generate from memory → Fail → Get corrected → Fix → Next task → Generate from memory → Fail
```
The loop is never broken by READING FIRST.

### Why Documentation Doesn't Help
Creating lessons-learned.md is useless if it's not READ before the next action. The document was written, then immediately violated.

### What Must Change
**Before ANY action, the sequence must be:**
1. STOP
2. READ relevant documentation/diffs/state
3. THEN act

This is not about better documentation. It's about changing the order of operations from:
- `ACT → FAIL → READ → FIX`
to:
- `READ → ACT → VERIFY`

---

## Behavioral Corrective Measures

### The Core Fix: STOP → READ → ACT → VERIFY

Every task must follow this sequence. No exceptions.

### Measure 1: Before ANY Migration Task

```bash
# ALWAYS run first - no exceptions
Read the lessons-learned.md file in this skill's reference/ directory using the Read tool
```

### Measure 2: Before Syncing Branches

```bash
# See ALL differences, not just the file you think matters
git diff source_branch..target_branch --name-only

# For each different file, understand WHY it's different
git diff source_branch..target_branch -- <file>
```

### Measure 3: Before Generating ANY Workflow

```bash
# Extract what exists - don't assume
grep -E "stage\s*\(" Jenkinsfile
grep "git clone" Jenkinsfile
grep -E "sh\s+['\"]" Jenkinsfile | head -30
```

### Measure 4: Before Copying Patterns

```bash
# READ the reference first
Read the DS-Backend ci-cd.yml reference (clone UNCTAD-eRegistrations/DS-Backend locally, then read .github/workflows/ci-cd.yml)
```

### Measure 5: After ANY Change

```bash
# Verify it works (actionlint must be on PATH;
# install: go install github.com/rhysd/actionlint/cmd/actionlint@latest)
actionlint .github/workflows/ci-cd.yml
```

### The Rule
**If a READ command hasn't been run first, output shouldn't be generated.**

---

## Mandatory Pre-Generation Checklist

Before generating ANY ci-cd.yml, MUST run these commands and document output:

```bash
# 1. Extract ALL stages
grep -E "stage\s*\(" Jenkinsfile | sed "s/.*stage('\([^']*\)').*/\1/"

# 2. Extract ALL git clone operations (CRITICAL)
grep "git clone" Jenkinsfile

# 3. Extract ALL shell commands
grep -E "sh\s+['\"]" Jenkinsfile | head -30

# 4. Create Feature Parity Table and verify EVERY item
```

---

## Required TodoWrite Checklist

Initialize with EXACTLY these 13 items from SKILL.md (canonical list — see SKILL.md Progress Tracking table for source of truth):

1. Complete pre-flight validation
2. Capture state snapshot + detect repo type
3. Gather migration preferences
4. Verify project version
5. Push git history to GitHub
6. GATE: Verify branch/tag counts
7. **BLOCKING: Feature parity verification**
8. Convert CI/CD pipelines
9. GATE: Validate workflow syntax
10. Update file references
11. Apply branch deletion protection ruleset
12. Generate migration summary
13. **MANDATORY: Run validation suite**

If migration fails between phases, see SKILL.md Phase 6 (Rollback Procedure).

---

## Post-Generation Verification Commands

Run these after EVERY ci-cd.yml generation:

```bash
# GitHub Actions workflow validation (PREFERRED - use actionlint)
# Install: go install github.com/rhysd/actionlint/cmd/actionlint@latest
actionlint .github/workflows/ci-cd.yml

# Fallback YAML syntax check (if actionlint unavailable)
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"

# Required sections check
grep -q "permissions:" .github/workflows/ci-cd.yml
grep -q "contents: write" .github/workflows/ci-cd.yml

# Runner labels check
grep "runs-on:" .github/workflows/ci-cd.yml | sort | uniq -c
```

---

## Enforcement Rules

### Behavioral Rules (PRIMARY)
1. **STOP before acting** - Never generate from memory
2. **READ before writing** - Always examine current state first
3. **DIFF before syncing** - See ALL differences between branches/files
4. **VERIFY after changing** - Confirm the change works

### Technical Rules (SECONDARY)
5. **NEVER generate ci-cd.yml without Feature Parity Table**
6. **NEVER use custom patterns - always copy from DS-Backend reference**
7. **ALWAYS run verification commands after each phase**
8. **ALWAYS use the exact 13-item TodoWrite checklist (canonical: SKILL.md Progress Tracking table)**
9. **If a pattern is in critical-patterns.md, use it EXACTLY**

### The Test
Before any action, ask: "Have I READ the relevant state/docs/diffs?"
- If NO → READ first
- If YES → Proceed

---

## Correct Patterns Quick Reference

### Git Config:
```yaml
- name: Configure Git
  run: |
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git config --global user.name "GitHub Actions Bot"
```

### Bump Version:
```yaml
- name: Bump version with retry
  id: version_bump
  env:
    BRANCH_NAME: ${{ github.ref_name }}
  run: |
    MAX_RETRIES=5
    for i in $(seq 0 $((MAX_RETRIES - 1))); do
      OLD_VERSION=$(node -p "require('./package.json').version")

      git checkout $BRANCH_NAME
      git reset --hard origin/$BRANCH_NAME
      git pull origin $BRANCH_NAME

      if npm run patch-release; then
        git pull origin $BRANCH_NAME
        NEW_VERSION=$(node -p "require('./package.json').version")
        echo "old_version=$OLD_VERSION" >> $GITHUB_OUTPUT
        echo "new_version=$NEW_VERSION" >> $GITHUB_OUTPUT
        exit 0
      fi
      sleep 2
    done
    exit 1
```

### Build Job Checkout:
```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.ref_name }}
    fetch-depth: 0
    clean: false

- name: Pull latest after version bump
  run: |
    git pull origin ${{ github.ref_name }}
```

### Docker Tag for Release/Master (CRITICAL - Failure #7):
```yaml
# In build-and-push-docker job, AFTER git pull:
- name: Get current version and compute tag
  id: version
  env:
    BRANCH_NAME: ${{ needs.set-build-variables.outputs.branch_name }}
    PRE_TAG_NAME: ${{ needs.set-build-variables.outputs.tag_name }}
  run: |
    VERSION=$(node -p "require('./package.json').version")
    MINOR_TAG=$(node -p "require('./package.json').version.substring(0, require('./package.json').version.lastIndexOf('.'))")
    echo "version=$VERSION" >> $GITHUB_OUTPUT
    echo "minor_tag=$MINOR_TAG" >> $GITHUB_OUTPUT

    # For release/* and master, use FRESH version; otherwise use pre-computed tag
    if [[ "$BRANCH_NAME" == release/* || "$BRANCH_NAME" == "master" ]]; then
      echo "tag_name=$VERSION" >> $GITHUB_OUTPUT
    else
      echo "tag_name=$PRE_TAG_NAME" >> $GITHUB_OUTPUT
    fi

- name: Build and push Docker image
  env:
    TAG_NAME: ${{ steps.version.outputs.tag_name }}  # NOT from set-build-variables!
```

---

## Critical Failure #10: Library Publish Pipeline — Two Silent Transient-Error Traps (2026-04, mule-common + mule3-datamapping-connector)

Both library workflows hit master-only publish failures within hours of each other on self-hosted runners. The cleanup logic and the gh CLI installer each had a "looks-defensive but isn't" pattern that returned 0 despite leaving the runner in a broken state.

### Trap A — `git worktree remove --force` returns 0 without deleting

**Symptom in CI log:**
```
Preparing worktree (detached HEAD <sha>)
fatal: '/tmp/pkgs-wt' already exists
Error: Process completed with exit code 128.
```

**Original cleanup (looked correct):**
```bash
git worktree remove --force "$PKGS_WT" 2>/dev/null || rm -rf "$PKGS_WT"
git worktree prune 2>/dev/null || true
```

**Why it failed:** when the path was registered as a worktree but its physical state was inconsistent (cancelled mid-write by `concurrency.cancel-in-progress: true`, or stale registration from a prior workspace), `git worktree remove --force` returned **0** without deleting the filesystem path. The `||` short-circuited, `rm -rf` never ran, and the next `git worktree add` saw the leftover directory and exited with `fatal: 'X' already exists`.

**Fix (mandatory, both pre- AND post-publish):**
```bash
git worktree remove --force "$PKGS_WT" 2>/dev/null || true
git worktree prune 2>/dev/null || true
rm -rf "$PKGS_WT"
```

The `rm -rf` is now unconditional. Whatever happened above, the path is gone before `worktree add` runs.

### Trap B — `curl --retry` doesn't retry on partial downloads

**Symptom in CI log:**
```
Run if command -v gh >/dev/null 2>&1; then
gzip: stdin: unexpected end of file
tar: Unexpected EOF in archive
tar: Error is not recoverable: exiting now
Error: Process completed with exit code 2.
```

**Original installer:**
```bash
curl -fsSL --retry 5 --retry-delay 5 --retry-max-time 60 \
  "https://github.com/cli/cli/releases/download/v${GH_VERSION}/${TARBALL}" \
  -o "/tmp/${TARBALL}"
tar -xzf "/tmp/${TARBALL}" -C /tmp
```

**Why it failed:** `curl --retry` retries on connection errors and 5xx responses, **not** on a successfully-started response that gets truncated mid-stream (which can happen when the CDN omits `Content-Length` and the connection drops). curl returns 0 with a partial file; tar then chokes on a corrupt gzip header. mule-common didn't even have `--retry` — it had no resilience at all.

**Fix:** wrap download + integrity check in an explicit retry loop, validate the gzip stream before extracting:
```bash
TARBALL_PATH="/tmp/${TARBALL}"
URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/${TARBALL}"

for attempt in 1 2 3 4 5; do
  rm -f "$TARBALL_PATH"
  if curl -fsSL --retry 3 --retry-delay 3 "$URL" -o "$TARBALL_PATH" \
     && gzip -t "$TARBALL_PATH" 2>/dev/null; then
    break
  fi
  if [ "$attempt" = "5" ]; then
    echo "::error::gh CLI tarball download failed after 5 attempts"
    exit 1
  fi
  echo "::warning::gh CLI tarball download/validate attempt ${attempt} failed, retrying"
  sleep $((attempt * 3))
done

tar -xzf "$TARBALL_PATH" -C /tmp
```

`gzip -t` rejects truncated archives, so a partial download gets caught and re-attempted instead of poisoning `tar`.

### General lesson

**Bash `A || B` is not a fallback when `A` can lie.** Both bugs share the same root: a guard command (`git worktree remove`, `curl`) returned 0 without finishing the job it implied. Defensive cleanup must either (a) verify the post-condition explicitly, or (b) run the worst-case cleanup unconditionally. For both downloads and ephemeral filesystem state, prefer "always do the destructive thing" over "do it only on observed failure."

### Verification commands

```bash
# Library template must use unconditional rm + prune; remove||rm pattern is forbidden
grep -A1 "git worktree remove --force \"\$PKGS_WT\"" workflow-template-library.yml \
  | grep -q "|| rm -rf" && echo "FORBIDDEN: || rm -rf pattern still present"

# gh CLI installer must validate tarball
grep -q "gzip -t" workflow-template-library.yml || echo "MISSING gzip integrity check on gh tarball"
```

---

## Verification

To verify these measures are being followed in future migrations:

1. Check that Feature Parity Table was created before ci-cd.yml
2. Diff generated workflow against DS-Backend reference for pattern consistency
3. Verify all verification commands were run and passed
4. Confirm TodoWrite shows all 13 checkpoints marked complete (including Phase 0.5 snapshot, Phase 4.5 ruleset, Phase 5.5 validation)

---

## Files Referenced

- `plugins/devops/skills/bitbucket-jenkins-to-github-actions/SKILL.md` - Main procedure
- `plugins/devops/skills/bitbucket-jenkins-to-github-actions/reference/critical-patterns.md` - Pattern reference
- [`UNCTAD-eRegistrations/Mule4`](https://github.com/UNCTAD-eRegistrations/Mule4) — `.github/workflows/ci-cd.yml` (closest precedent for Mule3 toolchain shape; runtime differs CE 4.7 vs CE 3.9, and Mule4 has no helm chart)
- [`UNCTAD-eRegistrations/DS-Backend`](https://github.com/UNCTAD-eRegistrations/DS-Backend) — `.github/workflows/ci-cd.yml` (Python/Django; `package.json` + `standard-version` for version-bump)
- [`UNCTAD-eRegistrations/BPA-Backend`](https://github.com/UNCTAD-eRegistrations/BPA-Backend) — `.github/workflows/ci-cd.yml` (Java / Spring Boot Maven build; `standard-version` bump tooling syncs version to `pom.xml` via `xml-js`)
- [`UNCTAD-eRegistrations/ActiveMQ`](https://github.com/UNCTAD-eRegistrations/ActiveMQ) — `.github/workflows/ci-cd.yml` (helm-chart-update job pattern)
