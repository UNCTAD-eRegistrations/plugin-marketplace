---
name: bitbucket-jenkins-to-github-actions
description: >
  Migrate a repository from Bitbucket+Jenkins to GitHub+GitHub Actions, including git
  history, branches, tags, CI/CD pipeline conversion (Jenkinsfile → ci-cd.yml), helm
  chart updates, branch deletion ruleset, and post-migration validation. Asks clarifying
  questions and handles external dependencies interactively. Use when migrating
  UNCTAD-eRegistrations repos from Bitbucket to GitHub.
license: UNCTAD-Internal
compatibility: Requires `gh` CLI (≥2.13 recommended), git, ssh access to GitHub. UNCTAD-eRegistrations org assumed for helm umbrella repo and Jenkins job mappings.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(ls *), Bash(grep *), Bash(find *), Bash(mkdir *), Bash(cp *), Bash(mv *), Bash(rm *), Bash(cat *), Bash(echo *), Bash(date *), Bash(seq *), Bash(sleep *), Bash(awk *), Bash(sed *), Bash(base64 *), Bash(node *), Bash(npm *), Bash(mvn *), Bash(du *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-04-27"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[github-target-url] [--dry-run]"
---

You are a **Repository Migration Specialist** expert in migrating codebases from Bitbucket to GitHub. You handle git history preservation, CI/CD pipeline conversion, and file reference updates with precision and care.

## Invocation

This skill can be invoked with optional arguments:
- `/bitbucket-jenkins-to-github-actions` - Start interactive migration for current repo
- `/bitbucket-jenkins-to-github-actions git@github.com:org/repo.git` - Specify target GitHub URL directly
- `/bitbucket-jenkins-to-github-actions --dry-run` - Preview all changes without executing

### Dry-Run Mode

When `--dry-run` is detected in arguments:

**Phase 0-1:** Execute normally (read-only analysis)

**Phase 2:** Show git commands without executing:
```
[DRY-RUN] Would execute: git remote add github <url>
[DRY-RUN] Would execute: git push github 'refs/remotes/origin/*:refs/heads/*'
[DRY-RUN] Would execute: git push github --delete HEAD
[DRY-RUN] Would execute: git push github --tags
[DRY-RUN] Would execute: gh repo edit <owner/repo> --default-branch develop
```

**Phase 3:** Generate workflow to temp file, show content:
```
[DRY-RUN] Would create: .github/workflows/ci-cd.yml
[DRY-RUN] --- Content Preview (first 50 lines) ---
<workflow yaml>
```

**Phase 4:** Show file diffs without applying:
```
[DRY-RUN] Would update: package.json
[DRY-RUN] - "repository": "bitbucket.org/..."
[DRY-RUN] + "repository": "github.com/..."
```

**Phase 4.5:** Show ruleset payload without applying:
```
[DRY-RUN] Would POST to: repos/<owner/repo>/rulesets
[DRY-RUN] Ruleset name: "delete protection"
[DRY-RUN] Branches: main, master, develop, beta, release-candidate, release/*
[DRY-RUN] Rules: deletion (active enforcement)
```

**Phase 5 / 5.5:** Show what summary would contain and which validation checks would run (do not execute checks since nothing was actually migrated)

**Phase 6:** Not applicable in dry-run (nothing to roll back)

At end of dry-run, ask: "Execute migration for real now?"

---

## Progress Tracking

Initialize with TodoWrite at start of migration:

| # | Checkpoint | Phase |
|---|------------|-------|
| 1 | Complete pre-flight validation | Phase 0 |
| 2 | Capture state snapshot + detect repo type | Phase 0.5 |
| 3 | Gather migration preferences | Phase 1 |
| 4 | Verify project version | Phase 1 |
| 5 | Push git history to GitHub | Phase 2 |
| 6 | GATE: Verify branch/tag counts | Gate 2-3 |
| 7 | **BLOCKING: Feature parity verification** | Phase 3 |
| 8 | Convert CI/CD pipelines | Phase 3 |
| 9 | GATE: Validate workflow syntax | Gate 3-4 |
| 10 | Update file references | Phase 4 |
| 11 | Apply branch deletion protection ruleset | Phase 4.5 |
| 12 | Grant team access (v4-development [+ v4-fe-development if frontend]) | Phase 4.6 |
| 13 | Generate migration summary | Phase 5 |
| 14 | **MANDATORY: Run validation suite** | Phase 5.5 |

If migration fails, see Phase 6 (Rollback). Mark each complete as you progress. Use this exact list when calling TodoWrite.

---

## Phase 0: Pre-flight Validation

### Step 0.1: Environment Check

Check required tools:
```bash
# Required
which git || echo "MISSING: git"
which ssh || echo "MISSING: ssh"
which gh  || echo "MISSING: gh (required for Phase 4.5 rulesets and Phase 4.6 team grants)"

# Optional (for specific project types)
which npm 2>/dev/null && echo "Found: npm (Node.js)"
which mvn 2>/dev/null && echo "Found: mvn (Java/Maven)"
which python3 2>/dev/null && echo "Found: python3"
```

### Step 0.2: GitHub SSH Connectivity & gh CLI Auth

```bash
ssh -T git@github.com 2>&1 | head -5

# gh CLI auth — needed for Phase 4.5 (rulesets) and Phase 4.6 (team grants)
gh auth status 2>&1 | head -10
```

Expected success (SSH): "Hi <username>! You've successfully authenticated..."
Expected success (gh): "✓ Logged in to github.com account <user>"

If SSH fails: Ask user to configure SSH keys before proceeding.
If gh fails: Ask user to run `gh auth login` before proceeding (or the migration will succeed up to Phase 4.5 then fail there).

### Step 0.3: Repository State Check

```bash
# Check for uncommitted changes
git status --porcelain | head -10

# Check if github remote already exists
git remote -v | grep github && echo "WARNING: github remote already exists"

# Estimate migration scope
echo "Branches: $(git branch -a | wc -l)"
echo "Tags: $(git tag | wc -l)"
echo "Repository size: $(du -sh .git 2>/dev/null | cut -f1)"
```

### Step 0.4: Pre-flight Summary

Display findings and ask user:
- "Pre-flight checks complete. Found X branches, Y tags. Proceed with migration?"
- Options: "Yes, proceed" | "No, abort"

If uncommitted changes found:
- "WARNING: Uncommitted changes detected. Commit or stash before migration?"
- Options: "Continue anyway" | "Abort to handle changes"

---

## Phase 0.5: State Snapshot & Repository Type Detection

**Purpose**: Capture pre-migration state for rollback (Phase 6) AND detect special repository configurations (LFS, submodules, monorepo, large repos) that change downstream behavior.

### Step 0.5.1: Capture State Snapshot

Create a snapshot directory and persist all state needed for rollback:

```bash
# Derive repo name from current directory
REPO_NAME=$(basename "$(pwd)")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SNAPSHOT_PATH="/tmp/migration-snapshot/${REPO_NAME}-${TIMESTAMP}"
mkdir -p "$SNAPSHOT_PATH"

# Capture git state
git remote -v > "$SNAPSHOT_PATH/remotes.txt"
git branch -a > "$SNAPSHOT_PATH/branches.txt"
git branch --show-current > "$SNAPSHOT_PATH/current-branch.txt"
git config --list > "$SNAPSHOT_PATH/config.txt"
git config --get checkout.defaultRemote > "$SNAPSHOT_PATH/default-remote.txt" 2>/dev/null || echo "" > "$SNAPSHOT_PATH/default-remote.txt"

# Capture original origin URL (will be Bitbucket at this point)
git remote get-url origin > "$SNAPSHOT_PATH/origin-url.txt"

# Capture files that will be modified/removed during migration
[ -f Jenkinsfile ] && cp Jenkinsfile "$SNAPSHOT_PATH/Jenkinsfile.bak"
[ -d .github ] && cp -r .github "$SNAPSHOT_PATH/.github.bak"
[ -f package.json ] && cp package.json "$SNAPSHOT_PATH/package.json.bak"
[ -f pom.xml ] && cp pom.xml "$SNAPSHOT_PATH/pom.xml.bak"
[ -f helm/Chart.yaml ] && cp helm/Chart.yaml "$SNAPSHOT_PATH/Chart.yaml.bak"
[ -f README.md ] && cp README.md "$SNAPSHOT_PATH/README.md.bak"

# Persist snapshot path for downstream phases (sourceable)
cat > /tmp/migration-state.sh <<EOF
export SNAPSHOT_PATH="$SNAPSHOT_PATH"
export REPO_NAME="$REPO_NAME"
export ORIGINAL_REMOTE_URL="$(git remote get-url origin)"
EOF

echo "Snapshot saved to: $SNAPSHOT_PATH"
echo "State file: /tmp/migration-state.sh (source this in later phases or rollback)"
```

**Output to user**: "Snapshot path: `<SNAPSHOT_PATH>` — keep this path; needed if rollback is required."

> **CRITICAL — Shell state does NOT persist across Bash tool calls.** Each Bash invocation starts a fresh shell, so `export VAR=...` from Phase 0.5 is lost. **Every subsequent Bash block in Phases 1–6 that references `$SNAPSHOT_PATH`, `$REPO_NAME`, `$ORIGINAL_REMOTE_URL`, `$HAS_LFS`, `$HAS_SUBMODULES`, `$JENKINSFILE_COUNT`, `$REPO_SIZE_MB`, or `$HAS_GH_PAGES` MUST start with:**
>
> ```bash
> [ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh
> ```
>
> Without this, conditional checks (e.g., LFS validation in Phase 5.5, monorepo handling in Phase 3) silently default to "no" and skip silently.

### Step 0.5.2: Detect Special Repository Configurations

```bash
# LFS detection
HAS_LFS="no"
if [ -f .gitattributes ] && grep -q "filter=lfs" .gitattributes; then
  HAS_LFS="yes"
  echo "Git LFS DETECTED: $(grep -c "filter=lfs" .gitattributes) tracked patterns"
fi

# Submodule detection
HAS_SUBMODULES="no"
if [ -f .gitmodules ]; then
  HAS_SUBMODULES="yes"
  SUBMODULE_COUNT=$(grep -c '^\[submodule' .gitmodules)
  echo "Submodules DETECTED: $SUBMODULE_COUNT submodule(s)"
  grep -E '(path|url) =' .gitmodules
fi

# Monorepo detection (multiple Jenkinsfiles)
JENKINSFILE_COUNT=$(find . -name "Jenkinsfile*" -not -path "./.git/*" 2>/dev/null | wc -l)
[ "$JENKINSFILE_COUNT" -gt 1 ] && echo "MONOREPO PATTERN: $JENKINSFILE_COUNT Jenkinsfile(s) found"

# Large repo warning
REPO_SIZE_MB=$(du -sm .git 2>/dev/null | cut -f1)
[ "$REPO_SIZE_MB" -gt 1000 ] && echo "WARNING: Large repo (${REPO_SIZE_MB}MB) — push may be slow / chunked"

# Special branches
HAS_GH_PAGES=$(git branch -a 2>/dev/null | grep -q "gh-pages" && echo "yes" || echo "no")
[ "$HAS_GH_PAGES" = "yes" ] && echo "gh-pages branch DETECTED — GitHub Pages config required after migration"

# Persist flags
cat >> /tmp/migration-state.sh <<EOF
export HAS_LFS="$HAS_LFS"
export HAS_SUBMODULES="$HAS_SUBMODULES"
export JENKINSFILE_COUNT="$JENKINSFILE_COUNT"
export REPO_SIZE_MB="$REPO_SIZE_MB"
export HAS_GH_PAGES="$HAS_GH_PAGES"
EOF
```

### Step 0.5.3: Conditional Handling

Apply these conditional behaviors in downstream phases based on detection:

| Detection | Required Action |
|-----------|-----------------|
| `HAS_LFS=yes` | Verify `git lfs version` works. After Phase 2.3, run `git lfs push --all github`. After remote rename, run `git lfs ls-files \| head` and compare against bitbucket. |
| `HAS_SUBMODULES=yes` | After Phase 2, edit `.gitmodules` URLs from Bitbucket → GitHub. Run `git submodule sync && git submodule update --init --recursive`. Commit the `.gitmodules` change. |
| `JENKINSFILE_COUNT>1` | Phase 3 must iterate over each Jenkinsfile. Either generate one workflow per Jenkinsfile OR a single matrix workflow. Ask user which approach. |
| `REPO_SIZE_MB>1000` | Phase 2.3 push may hit GitHub's 2GB push limit. Push branches in chunks rather than refspec — iterate per branch. |
| `HAS_GH_PAGES=yes` | After migration, manually configure GitHub Pages in repo settings (Settings > Pages > Source: gh-pages branch). Add to Manual Steps Checklist. |

**Ask user before proceeding** if any flag is "yes":
- "Special configuration detected: [list flags]. Confirm understanding of additional steps?"
- Options: "Yes, proceed with conditional handling" | "Abort and review"

---

## Phase 1: Discovery & Clarification

### Step 1.1: Detect Current Configuration

Analyze the current repository:
```bash
git remote -v                    # Current remotes
git branch -a                    # All branches
git tag                          # All tags
```

Report findings to user:
- Current origin URL
- Number of branches and tags
- Detect if Jenkinsfile exists
- Detect if .github/workflows/ exists

### Step 1.2: Ask Clarifying Questions

Use AskUserQuestion to gather migration preferences:

**Question 1: Target Repository**
If not provided as argument, ask:
- "What is the target GitHub repository URL?"
- Format: `git@github.com:ORGANIZATION/REPOSITORY.git`

**Question 2: External Dependencies**
Scan for external Bitbucket repo references in CI/CD files, then ask:
- "Should external Bitbucket repos (e.g., helm charts, tools) also migrate to GitHub or stay on Bitbucket?"
- Options: "Migrate all to GitHub" | "Keep on Bitbucket" | "Already migrated"

**Question 3: Bitbucket Remote**
- "After migration, should Bitbucket be kept as a backup remote?"
- Options: "Keep as backup (recommended)" | "Remove entirely"

**Question 4: GitHub Setup Status**
- "Are GitHub secrets and self-hosted runners already configured?"
- Options: "Yes, all configured" | "Partially configured" | "Not yet configured"

### Step 1.3: Version Initialization

**Purpose**: Ensure the project version is correctly set before migration completes.

1. **Detect version files**:
```bash
ls package.json 2>/dev/null && echo "Found: package.json"
ls pom.xml 2>/dev/null && echo "Found: pom.xml"
ls pyproject.toml setup.py 2>/dev/null && echo "Found: Python version file"
```

2. **For each detected version file, show current version and ask**:

   **package.json** (Node.js):
   ```bash
   node -p "require('./package.json').version"
   ```
   - Ask: "Current version is `X.Y.Z`. Is this correct?"
   - Options: "Keep current version" | "Update version" | "Skip"
   - If "Update version": Ask for new version, then: `npm version <NEW_VERSION> --no-git-tag-version`

   **pom.xml** (Java/Maven):
   ```bash
   grep -m1 "<version>" pom.xml | sed 's/.*<version>\(.*\)<\/version>.*/\1/'
   ```
   - Same options as above
   - Update with: `mvn versions:set -DnewVersion=<NEW_VERSION> -DgenerateBackupPoms=false`

3. **If version was updated**:
   - Ask: "Commit version update now, or leave staged?"
   - Options: "Commit now" | "Leave staged"

---

## Phase 2: Git Migration

### Step 2.1: Add GitHub Remote
```bash
git remote add github <TARGET_GITHUB_URL>
```

### Step 2.2: Fetch Latest from Bitbucket
```bash
git fetch origin --prune
git fetch origin --tags
```

### Step 2.3: Push All Content to GitHub
```bash
# Push all branches using refspec (faster than iterating)
git push github 'refs/remotes/origin/*:refs/heads/*'

# Delete spurious HEAD branch created by origin/HEAD symbolic ref
git push github --delete HEAD 2>/dev/null || true

# Push all tags
git push github --tags
```

### Step 2.4: Verify Migration
```bash
ORIGIN_BRANCHES=$(git ls-remote --heads origin | wc -l)
GITHUB_BRANCHES=$(git ls-remote --heads github | wc -l)
ORIGIN_TAGS=$(git ls-remote --tags origin | wc -l)
GITHUB_TAGS=$(git ls-remote --tags github | wc -l)

echo "Branches: origin=$ORIGIN_BRANCHES, github=$GITHUB_BRANCHES"
echo "Tags: origin=$ORIGIN_TAGS, github=$GITHUB_TAGS"
```

### Step 2.5: Update Remotes

Based on user preference from Step 1.2:
```bash
# Keep Bitbucket as backup
git remote rename origin bitbucket
git remote rename github origin

# Set default remote
git config checkout.defaultRemote origin

# Update branch tracking
git branch -u origin/<current-branch>
```

### Step 2.6: Set Default Branch on GitHub

Set `develop` as the default branch (or `main`/`master` if develop doesn't exist):
```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh

# Extract owner/repo from GitHub URL and persist for downstream phases
GITHUB_REPO=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')
echo "export GITHUB_REPO=\"$GITHUB_REPO\"" >> /tmp/migration-state.sh

# Set default branch to develop
gh repo edit "$GITHUB_REPO" --default-branch develop
```

This ensures:
- New clones checkout `develop` by default
- PRs target `develop` by default
- GitHub UI shows `develop` as the main branch

---

## GATE 2-3: Git Migration Validation

**Before proceeding to Phase 3, validate:**

```bash
ORIGIN_BRANCHES=$(git ls-remote --heads bitbucket 2>/dev/null | wc -l || git ls-remote --heads origin | wc -l)
GITHUB_BRANCHES=$(git ls-remote --heads origin | wc -l)

if [ "$ORIGIN_BRANCHES" -ne "$GITHUB_BRANCHES" ]; then
  echo "MISMATCH: Branch count differs (source: $ORIGIN_BRANCHES, github: $GITHUB_BRANCHES)"
fi
```

**If mismatch:**
- Show remediation: "Re-push branches with: `git push github 'refs/remotes/origin/*:refs/heads/*'`"
- Ask: "Retry push or continue anyway?"

**If match:**
- Mark checkpoint complete
- Proceed to Phase 3

---

## Phase 3: CI/CD Migration (Interactive)

### Reference Migrations

**Pick the closest-precedent migration and read its `ci-cd.yml` BEFORE generating a new one. Copy patterns verbatim — custom patterns are the #1 source of CI failure (see `reference/lessons-learned.md` Critical Failure #4).**

| Migration | Closest match for | Workflow |
|-----------|-------------------|----------|
| **Mule4** | Mule3 — same Maven `mule-application` shape + identical `standard-version`/`xml-js` tooling; runtime differs (CE 4.7 vs CE 3.9). **Mule4 has no helm chart — for the helm-chart-update job, reference ActiveMQ instead.** | [`UNCTAD-eRegistrations/Mule4` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/Mule4/blob/develop/.github/workflows/ci-cd.yml) |
| DS-Backend | Python (Django) project with `package.json` + `standard-version` version-bump tooling | [`UNCTAD-eRegistrations/DS-Backend` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/DS-Backend/blob/develop/.github/workflows/ci-cd.yml) |
| BPA-Backend | Java / Spring Boot (Maven build); `standard-version` bump tooling syncs to `pom.xml` via `xml-js` | [`UNCTAD-eRegistrations/BPA-Backend` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/BPA-Backend/blob/develop/.github/workflows/ci-cd.yml) |
| ActiveMQ | Helm-chart-update job pattern | [`UNCTAD-eRegistrations/ActiveMQ` → `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/ActiveMQ/blob/develop/.github/workflows/ci-cd.yml) |

### CRITICAL WARNINGS CHECKLIST

**Before generating or reviewing any workflow, verify these patterns:**

| # | Issue | Verification | Impact |
|---|-------|--------------|--------|
| 1 | Missing `permissions: contents: write` | `grep "contents.*write" *.yml` | Silent push failure |
| 2 | Missing `clean: false` in checkout | `grep "clean: false" *.yml` | Version bump fails |
| 3 | Using `git fetch + reset` instead of `git pull` | `grep -B2 "git reset --hard" *.yml` | Stale version |
| 4 | Missing xml-js for Java projects | `grep "xml-js" package.json` | pom.xml not updated |
| 5 | GITHUB_TOKEN doesn't trigger new runs | N/A | Must continue same workflow |
| 6 | Missing retry logic in version bump | Check for `MAX_RETRIES` | Race condition failures |
| 7 | Missing git user config | `grep "git config.*user" *.yml` | Commits fail |
| 8 | Manual SSH key for Docker BuildKit | `grep "webfactory/ssh-agent" *.yml` | `--ssh default` fails |
| 9 | Missing GITHUB_STEP_SUMMARY | `grep "GITHUB_STEP_SUMMARY" *.yml` | No job summaries in UI |
| 10 | Wrong job dependency order | Check `needs:` for trigger-jenkins-deploy | Deploy before tag |
| 11 | Missing `fetch-depth: 0` + `clean: false` in build job | Check build job checkout config | Uses OLD version after bump |
| 12 | npm scripts missing git push | Check package.json scripts | Version bump not pushed |
| 13 | Missing BRANCH_NAME env var | Check `env:` in bump-version step | git push fails with invalid refspec |
| 14 | Emoji-heavy summaries | Check summary step formatting | Inconsistent style |
| 15 | Wrong runner labels | Check `runs-on:` values | Jobs fail or run on wrong runner |
| 16 | **FEATURE PARITY NOT VERIFIED** | Compare ALL Jenkinsfile stages | **Build failures from missing steps** |
| 17 | Missing ssh-keyscan for external repos (docker build) | Check for `ssh-keyscan` before SSH `git clone` | Host key verification failed |
| 18 | Artifact uploads not opt-in | Check `upload-artifact` conditions | Storage quota exceeded |
| 19 | Missing GHCR_TOKEN for helm chart job | Check for `GHCR_TOKEN` in helm-chart-update | Helm repo add / git clone fails |

**See [reference/critical-patterns.md](reference/critical-patterns.md) for detailed explanations.**

### Step 3.1: Detect CI/CD Files

Check for:
- `Jenkinsfile` - Legacy Jenkins pipeline
- `.github/workflows/*.yml` - Existing GitHub Actions

### Step 3.2: Jenkinsfile Handling

If Jenkinsfile exists, ask user:
- "Jenkinsfile detected. How should it be handled?"
- Options: "Convert to GitHub Actions (Recommended)" | "Keep for reference" | "Remove without replacement"

### Step 3.2.0: BLOCKING - Feature Parity Verification

**THIS STEP IS MANDATORY BEFORE GENERATING ANY WORKFLOW**

Before writing ANY ci-cd.yml, you MUST perform a complete feature extraction from the Jenkinsfile:

```bash
# 1. Extract ALL stages
echo "=== JENKINSFILE STAGES ==="
grep -E "stage\s*\(" Jenkinsfile | sed "s/.*stage('\([^']*\)').*/\1/"

# 2. Extract ALL git clone operations (CRITICAL - often missed!)
echo "=== GIT CLONE OPERATIONS ==="
grep "git clone" Jenkinsfile

# 3. Extract ALL shell commands
echo "=== SHELL COMMANDS ==="
grep -E "sh\s+['\"]" Jenkinsfile | head -30

# 4. Extract credentials/secrets usage
echo "=== CREDENTIALS ==="
grep -E "(sshagent|withCredentials|credentials)" Jenkinsfile

# 5. Extract post-build actions
echo "=== POST-BUILD ==="
grep -A 5 "post {" Jenkinsfile
```

**Create Feature Parity Table** before proceeding:

| Jenkinsfile Feature | ci-cd.yml Equivalent | Status |
|---------------------|---------------------|--------|
| (list each stage) | (corresponding job/step) | ✅/❌ |
| (list each clone) | (corresponding step) | ✅/❌ |
| (list each credential) | (corresponding secret) | ✅/❌ |

**BLOCKING**: Do NOT proceed to Step 3.2.1 until:
- ALL stages are mapped to ci-cd.yml jobs/steps
- ALL git clone operations are accounted for
- ALL shell commands are translated
- ALL post-build actions are included

**See [reference/critical-patterns.md#18-feature-parity-verification](reference/critical-patterns.md#18-feature-parity-verification) for detailed guidance.**

### Step 3.2.1: Generate GitHub Actions Workflow

**If user selected "Convert to GitHub Actions", you MUST create `.github/workflows/ci-cd.yml`.**

1. **Analyze Jenkinsfile structure**:
   ```bash
   cat Jenkinsfile
   ```
   Identify: stages, environment variables, branch conditions, credentials

2. **Ask for project-specific values**:
   - "What is the Docker image name?" (e.g., `unctad/bpa-websocket`)
   - "What is the Helm chart name?" (if helm stage exists)
   - "Should Jenkins deploy triggers be included?"

3. **Generate workflow with standard jobs**:

   | Job | Purpose | When to Include |
   |-----|---------|-----------------|
   | `set-build-variables` | TAG_NAME, VERSION, conditional flags | Always |
   | `helm-chart-update` | Lint, package, push helm chart | If Jenkinsfile has helm stage |
   | `bump-version` | Patch release with retry logic | If Jenkinsfile has version bump |
   | `build-and-push-docker` | Docker build and push | Always (if Docker stage exists) |
   | `tag-production` | Git tag on master | If Jenkinsfile tags releases |
   | `trigger-jenkins-deploy` | Trigger Jenkins jobs | If deploy integration needed |
   | `notify-failure` | Slack notification | Always |

4. **Required workflow structure**:
   ```yaml
   name: CI/CD Pipeline
   on:
     push:
       branches: [master, develop, beta, test, release-candidate, release/**, feature/**]
     workflow_dispatch:
       inputs:
         FORCE_BUILD: ...

   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true

   permissions:
     contents: write      # CRITICAL
     checks: write
     pull-requests: write
     statuses: write
     actions: write

   jobs:
     # Jobs here...
   ```

5. **Add GITHUB_STEP_SUMMARY for EVERY job** (MANDATORY):

   Each job MUST have a summary step that writes to `$GITHUB_STEP_SUMMARY`:
   ```yaml
   - name: <Job> summary
     run: |
       echo "## 📋 <Title>" >> $GITHUB_STEP_SUMMARY
       echo "" >> $GITHUB_STEP_SUMMARY
       echo "- **Key:** \`value\`" >> $GITHUB_STEP_SUMMARY
       echo "" >> $GITHUB_STEP_SUMMARY
       echo "✅ <Success message>" >> $GITHUB_STEP_SUMMARY
   ```

   Required summaries per job (NO emojis in headers):
   | Job | Title |
   |-----|-------|
   | set-build-variables | Build Configuration (with subsections: Branch Information, Build Variables, Pipeline Decisions) |
   | helm-chart-update | Helm Chart Update |
   | bump-version | Version Bumped |
   | build-and-push-docker | Docker Build Summary |
   | tag-production | Production Release Tagged |
   | trigger-jenkins-deploy | Jenkins Deployment Triggered |
   | notify-failure | Pipeline Failed |

   See [reference/critical-patterns.md#16-summary-style-guidelines](reference/critical-patterns.md#16-summary-style-guidelines) for style rules.

7. **Create workflow and remove Jenkinsfile**:
   ```bash
   mkdir -p .github/workflows
   # Write ci-cd.yml
   git rm Jenkinsfile
   ```

8. **Show summary of generated workflow** with required secrets list

### Step 3.2.2: Jenkins Deployment Trigger Job

**MANDATORY for ALL CI/CD workflows** - include this job with ALL branch-specific steps.

**Job Configuration:**
- `needs: [set-build-variables, build-and-push-docker]` - simplified dependencies
- `if: needs.build-and-push-docker.result == 'success'` - runs when docker build succeeds
- Branch filtering is done at the STEP level, not the job level

**Jenkins Job Mapping:**
| Branch | Jenkins Job |
|--------|-------------|
| develop, feature/* | develop-deploy |
| beta | beta-deploy |
| release-candidate | test-deploy |

```yaml
  trigger-jenkins-deploy:
    runs-on: [self-hosted, linux, jenkins]
    needs: [set-build-variables, build-and-push-docker]
    if: |
      always() &&
      needs.build-and-push-docker.result == 'success'
    steps:
      - name: Load and mask Jenkins credentials
        run: |
          JENKINS_URL="${JENKINS_URL:-${{ secrets.JENKINS_URL }}}"
          JENKINS_USER="${JENKINS_USER:-${{ secrets.JENKINS_USER }}}"
          JENKINS_API_TOKEN="${JENKINS_API_TOKEN:-${{ secrets.JENKINS_API_TOKEN }}}"
          echo "::add-mask::${JENKINS_URL}"
          echo "::add-mask::${JENKINS_USER}"
          echo "::add-mask::${JENKINS_API_TOKEN}"
          echo "JENKINS_URL=${JENKINS_URL}" >> $GITHUB_ENV
          echo "JENKINS_USER=${JENKINS_USER}" >> $GITHUB_ENV
          echo "JENKINS_API_TOKEN=${JENKINS_API_TOKEN}" >> $GITHUB_ENV
          echo "✓ Jenkins credentials loaded and masked"

      - name: Trigger Jenkins deploy for develop/feature branches
        if: github.ref_name == 'develop' || startsWith(github.ref_name, 'feature/')
        run: |
          echo "Triggering Jenkins deployment for ${{ github.ref_name }} branch..."
          HTTP_STATUS=$(curl -X POST \
            -u ${JENKINS_USER}:${JENKINS_API_TOKEN} \
            -w "%{http_code}" \
            -o /dev/null \
            -s \
            "${JENKINS_URL}/job/develop-deploy/build?delay=0sec")

          if [ $HTTP_STATUS -eq 201 ] || [ $HTTP_STATUS -eq 200 ]; then
            echo "✓ Jenkins job triggered successfully (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Triggered" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** develop-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Success (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
          else
            echo "✗ Failed to trigger Jenkins job (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Failed" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** develop-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Failed (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
            exit 1
          fi

      - name: Trigger Jenkins deploy for beta
        if: github.ref_name == 'beta'
        run: |
          echo "Triggering Jenkins deployment for beta branch..."
          HTTP_STATUS=$(curl -X POST \
            -u ${JENKINS_USER}:${JENKINS_API_TOKEN} \
            -w "%{http_code}" \
            -o /dev/null \
            -s \
            "${JENKINS_URL}/job/beta-deploy/build?delay=0sec")

          if [ $HTTP_STATUS -eq 201 ] || [ $HTTP_STATUS -eq 200 ]; then
            echo "✓ Jenkins job triggered successfully (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Triggered" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** beta" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** beta-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Success (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
          else
            echo "✗ Failed to trigger Jenkins job (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Failed" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** beta" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** beta-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Failed (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
            exit 1
          fi

      - name: Trigger Jenkins deploy for release-candidate
        if: github.ref_name == 'release-candidate'
        run: |
          echo "Triggering Jenkins deployment for release-candidate branch..."
          HTTP_STATUS=$(curl -X POST \
            -u ${JENKINS_USER}:${JENKINS_API_TOKEN} \
            -w "%{http_code}" \
            -o /dev/null \
            -s \
            "${JENKINS_URL}/job/test-deploy/build?delay=0sec")

          if [ $HTTP_STATUS -eq 201 ] || [ $HTTP_STATUS -eq 200 ]; then
            echo "✓ Jenkins job triggered successfully (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Triggered" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** release-candidate" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** test-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Success (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
          else
            echo "✗ Failed to trigger Jenkins job (HTTP $HTTP_STATUS)"
            echo "## Jenkins Deployment Failed" >> $GITHUB_STEP_SUMMARY
            echo "- **Branch:** release-candidate" >> $GITHUB_STEP_SUMMARY
            echo "- **Jenkins Job:** test-deploy" >> $GITHUB_STEP_SUMMARY
            echo "- **Status:** Failed (HTTP $HTTP_STATUS)" >> $GITHUB_STEP_SUMMARY
            exit 1
          fi
```

**Key Implementation Details:**
1. **Credential masking step runs FIRST** - masks secrets before any curl commands
2. **Per-step branch conditions** - each branch type has its own step with `if:` condition
3. **No parameters passed** - just `?delay=0sec` query param
4. **HTTP status validation** - checks for 200 or 201, exits 1 on failure
5. **Both success and failure summaries** - documented in GITHUB_STEP_SUMMARY

### Step 3.2.3: Helm Chart Update Job

**Include this job when the Jenkinsfile has a helm chart packaging/push stage.**

**Job Configuration:**
- `needs: [set-build-variables]` - depends only on build variables
- `if: SHOULD_HELM == 'true' && (develop || feature/kubernetes)` - runs only on helm commits for eligible branches
- Runner: `[self-hosted, linux, build]` (NOT `build, normal` -- helm jobs use the `build` runner without the `normal` label)

**Parameterization:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `CHART_NAME` | Helm chart name (matches Chart.yaml name) | `activemq`, `eregcms` |

**Required Secret:**
| Secret | Purpose |
|--------|---------|
| `GHCR_TOKEN` | GitHub PAT for helm repo auth and Eregistrations-Helm clone |

```yaml
  helm-chart-update:
    name: Update Helm Chart
    runs-on: [self-hosted, linux, build]
    needs: set-build-variables
    if: |
      needs.set-build-variables.outputs.SHOULD_HELM == 'true' &&
      (github.ref_name == 'develop' || github.ref_name == 'feature/kubernetes')
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Helm
        uses: azure/setup-helm@v4
        with:
          version: 'latest'

      - name: Lint and package Helm chart
        env:
          CHART_NAME: <CHART_NAME>
        run: |
          cd helm
          helm repo add eregistrations-helm https://raw.githubusercontent.com/UNCTAD-eRegistrations/Eregistrations-Helm/master --username x-access-token --password ${{ secrets.GHCR_TOKEN }}
          helm dependency update .
          helm lint .
          helm template . > /dev/null
          helm package ./

      - name: Update Helm chart repository
        env:
          CHART_NAME: <CHART_NAME>
        run: |
          cd helm
          TGZ_FILE=$(ls ${CHART_NAME}-*.tgz | head -1)
          git clone https://x-access-token:${{ secrets.GHCR_TOKEN }}@github.com/UNCTAD-eRegistrations/Eregistrations-Helm.git umbrella-repo
          cd umbrella-repo
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git config user.name "GitHub Actions Bot"

          # Remove old chart archives from git tracking
          git rm -f ${CHART_NAME}-*.tgz || true
          cp ../$TGZ_FILE ./

          # Regenerate Helm repository index
          helm repo index ./ --url https://raw.githubusercontent.com/UNCTAD-eRegistrations/Eregistrations-Helm/master

          git add $TGZ_FILE index.yaml
          if git diff --cached --quiet; then
            echo "No changes to commit — chart already up to date"
            echo "- **Skipped**: Chart already up to date in umbrella repo" >> $GITHUB_STEP_SUMMARY
          else
            git commit -m "helm: update $CHART_NAME chart with $TGZ_FILE"
            for i in 1 2 3 4 5; do
              git push origin master && break
              echo "Push failed, retrying ($i/5)..."
              git pull --no-rebase origin master || {
                # Resolve index.yaml merge conflicts by regenerating
                helm repo index ./ --url https://raw.githubusercontent.com/UNCTAD-eRegistrations/Eregistrations-Helm/master
                git add index.yaml
                git commit --no-edit
              }
            done
          fi

      - name: Summary
        run: |
          echo "## Helm Chart Update" >> $GITHUB_STEP_SUMMARY
          echo "- Helm chart repository updated on GitHub" >> $GITHUB_STEP_SUMMARY
```

**Key Implementation Details:**
1. **Runner is `[self-hosted, linux, build]`** -- NOT `[self-hosted, linux, build, normal]`
2. **Uses `azure/setup-helm@v4`** to install Helm CLI (self-hosted runners may not have it)
3. **Uses `GHCR_TOKEN`** for both helm repo authentication and GitHub clone (HTTPS, not SSH)
4. **`helm dependency update`** runs before lint (handles chart dependencies from the umbrella repo)
5. **Clone target is GitHub HTTPS** -- `UNCTAD-eRegistrations/Eregistrations-Helm.git` (NOT Bitbucket)
6. **Git user config required** before commit operations
7. **`git rm`** removes old chart tgz files (clean git history, not just filesystem delete)
8. **Idempotency check** -- `git diff --cached --quiet` skips commit when chart is unchanged
9. **Push retry (5 attempts)** with index.yaml merge conflict resolution via regeneration
10. **Commit message format** -- `helm: update $CHART_NAME chart with $TGZ_FILE`

**Reference implementation:** [`UNCTAD-eRegistrations/ActiveMQ` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/ActiveMQ/blob/develop/.github/workflows/ci-cd.yml)

### Step 3.3: GitHub Actions Updates

If .github/workflows/ exists, for EACH workflow file:
1. Scan for Bitbucket references
2. Show user what changes are needed
3. Check for version bump -> build patterns
4. Check runner labels
5. Ask for approval before each change

### Step 3.4: Release Branch Support

1. **Ask user** (even if detection shows it's missing):
   - "Add release branch support? This enables parallel maintenance branches"
   - Options: "Yes, add full support" | "No, skip"

2. **If "Yes", apply these patterns** (ask before each):
   - Add `release/**` to push triggers
   - Add `minor_tag` output for version tagging
   - Add release/* branch tag calculation case
   - Update version bump condition
   - Add Docker minor tag push

---

## GATE 3-4: CI/CD Validation

**Before proceeding to Phase 4, validate the generated workflow:**

```bash
# GitHub Actions workflow validation (actionlint must be on PATH;
# install: go install github.com/rhysd/actionlint/cmd/actionlint@latest)
# Use config file for custom runner labels: ~/.config/actionlint.yaml
actionlint -config-file ~/.config/actionlint.yaml .github/workflows/ci-cd.yml

# Required sections check
grep -q "permissions:" .github/workflows/ci-cd.yml && echo "Permissions: Found"
grep -q "contents: write" .github/workflows/ci-cd.yml && echo "Contents write: Found"
grep -q "^jobs:" .github/workflows/ci-cd.yml && echo "Jobs: Found"
```

### Actionlint Configuration

Custom runner labels (build, normal, heavy, jenkins) require a config file. Store at `~/.config/actionlint.yaml`:

```yaml
self-hosted-runner:
  labels:
    - build
    - normal
    - heavy
    - jenkins
```

Then use: `actionlint -config-file ~/.config/actionlint.yaml <workflow.yml>`

Optionally add a shell alias:
```bash
alias actionlint='actionlint -config-file ~/.config/actionlint.yaml'
```

**If invalid:**
- Show errors
- Offer to fix: "Fix workflow issues or skip validation?"

**If valid:**
- Mark checkpoint complete
- Proceed to Phase 4

---

## Phase 4: File Reference Updates

### Step 4.1: Scan for Bitbucket URLs

```bash
grep -r "bitbucket.org" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.md" .
```

### Step 4.2: Update Each File (Interactive)

For each file with Bitbucket URLs referencing THIS repository:

**package.json**:
- `repository.url` -> GitHub URL
- `homepage` -> GitHub URL

**helm/Chart.yaml**:
- `sources` -> GitHub URL (keep external Bitbucket URLs if deps stay there)

**README.md**:
- Badge URLs
- Clone instructions
- Links

Ask user before each file update:
- "Update <filename>? Changes: <show diff preview>"

---

## Phase 4.5: Branch Deletion Protection

**Purpose**: Apply standard "delete protection" ruleset to prevent accidental deletion of long-lived branches. Uses GitHub's modern Rulesets API (preferred over legacy branch protection).

**Scope**: This is the ONLY protection automatically applied. PR review requirements, status checks, and force-push protection are intentionally NOT applied here — they should be configured per-repo by the team.

**Protected branches**: `main`, `master`, `develop`, `beta`, `release-candidate`, and all `release/*` branches (e.g. `release/2.17`, `release/2.18`)

### Step 4.5.1: Check for Existing Ruleset (Idempotency)

```bash
# Restore migration state (see "CRITICAL" note in Phase 0.5.1)
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh

# $GITHUB_REPO was exported by Step 2.6; fall back to local derivation if missing
: "${GITHUB_REPO:=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')}"

# Filter by source_type=="Repository" to avoid matching org-inherited rulesets.
# An org-level "delete protection" ruleset would falsely satisfy a repo-name-only match,
# leaving the repo dependent on org policy with no dedicated repo-scoped protection.
EXISTING_RULESET_ID=$(gh api "repos/$GITHUB_REPO/rulesets" \
  --jq '.[] | select(.name=="delete protection" and .source_type=="Repository") | .id' 2>/dev/null)

if [ -n "$EXISTING_RULESET_ID" ]; then
  echo "Repo-scoped ruleset 'delete protection' already exists (id=$EXISTING_RULESET_ID) — skipping creation"
else
  echo "No existing repo-scoped 'delete protection' ruleset — will create"
  # Note: an org-level ruleset of the same name may still preempt; that is detected at POST time (HTTP 422)
fi
```

### Step 4.5.2: Apply Delete Protection Ruleset

Only run if `EXISTING_RULESET_ID` is empty:

```bash
gh api -X POST "repos/$GITHUB_REPO/rulesets" \
  --input - <<'EOF'
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
  "rules": [
    {
      "type": "deletion"
    }
  ],
  "bypass_actors": []
}
EOF
```

**Note**: `refs/heads/release/*` uses fnmatch wildcard syntax — it matches every direct child like `release/2.17`, `release/2.18` but NOT nested like `release/2.17/hotfix`. If you need nested matching, use `refs/heads/release/**`.

### Step 4.5.3: Verify Ruleset

```bash
# Confirm ruleset is active and has correct configuration (repo-scoped only)
RULESET_ID=$(gh api "repos/$GITHUB_REPO/rulesets" \
  --jq '.[] | select(.name=="delete protection" and .source_type=="Repository") | .id')

gh api "repos/$GITHUB_REPO/rulesets/$RULESET_ID" \
  --jq '{name, enforcement, conditions: .conditions.ref_name.include, rules: [.rules[].type]}'
```

**Expected output**:
```json
{
  "name": "delete protection",
  "enforcement": "active",
  "conditions": ["refs/heads/main", "refs/heads/master", "refs/heads/develop", "refs/heads/beta", "refs/heads/release-candidate", "refs/heads/release/*"],
  "rules": ["deletion"]
}
```

### Step 4.5.4: Failure Handling

| Failure | Likely Cause | Action |
|---------|--------------|--------|
| HTTP 403 | Insufficient permissions | Verify `gh auth status` user has admin on the repo |
| HTTP 404 | Wrong repo path | Re-check `GITHUB_REPO` value |
| HTTP 422 (already exists) | Ruleset by that name exists | Skip — handled by Step 4.5.1 idempotency check |
| HTTP 422 (validation) | Org-level ruleset preempts | Inspect with `gh api repos/$GITHUB_REPO/rulesets --jq '.[].source_type'` — org rulesets take precedence; coordinate with org admin |

If unrecoverable, do NOT abort migration — note in summary that ruleset must be applied manually.

---

## Phase 4.6: Repository Team Access

**Purpose**: Grant the standard org teams `write` (push) access to the migrated repo so developers don't need individual-collaborator grants.

**Teams granted**:
- `v4-development` — always, on every migrated repo
- `v4-fe-development` — only on frontend-related repos (heuristic + user confirmation)

**Scope**: Only these teams. Per-user collaborators (e.g. admins) are intentionally NOT added — those are managed manually per repo.

### Step 4.6.1: Detect Frontend Classification

Heuristic — any one signal counts as frontend:

```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh

IS_FRONTEND="no"
FE_SIGNALS=""

# Signal 1: package.json with frontend framework deps
if [ -f package.json ] && grep -qE '"(react|vue|@angular/core|@angular/cli|svelte|next|nuxt|vite|@vue/cli|preact|solid-js)"\s*:' package.json; then
  IS_FRONTEND="yes"
  FE_SIGNALS="$FE_SIGNALS package.json-deps"
fi

# Signal 2: telltale frontend config files
for pattern in vite.config.* next.config.* nuxt.config.* angular.json svelte.config.* astro.config.* remix.config.*; do
  if compgen -G "$pattern" > /dev/null 2>&1; then
    IS_FRONTEND="yes"
    FE_SIGNALS="$FE_SIGNALS config:$pattern"
    break
  fi
done

# Signal 3: HTML entry point in conventional locations
if [ -f index.html ] || [ -f public/index.html ] || [ -f src/index.html ]; then
  IS_FRONTEND="yes"
  FE_SIGNALS="$FE_SIGNALS html-entry"
fi

echo "Frontend detection: IS_FRONTEND=$IS_FRONTEND (signals:$FE_SIGNALS)"

# Persist for downstream steps
cat >> /tmp/migration-state.sh <<EOF
export IS_FRONTEND="$IS_FRONTEND"
export FE_SIGNALS="$FE_SIGNALS"
EOF
```

Then ask user to confirm using AskUserQuestion (matches Phase 1.2 style):

- Question: "Detected frontend classification: **$IS_FRONTEND** (signals:$FE_SIGNALS). Should `v4-fe-development` team be granted write access?"
- Options: "Yes — grant v4-fe-development" | "No — skip v4-fe-development"

Set `GRANT_FE_TEAM` to `yes`/`no` based on the user's answer (NOT solely the heuristic — user confirmation is authoritative). Persist:

```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh
echo "export GRANT_FE_TEAM=\"$GRANT_FE_TEAM\"" >> /tmp/migration-state.sh
```

### Step 4.6.2: Grant Team Access

`PUT /orgs/{org}/teams/{team}/repos/{owner}/{repo}` is upsert — but a blind PUT with `permission=push` would silently DOWNGRADE a team that already holds `admin` or `maintain`. Use the helper below to guard against that case (relevant when re-running the skill on an already-migrated repo where someone manually elevated team permissions):

```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh

# $GITHUB_REPO was exported by Step 2.6; fall back to local derivation if missing
: "${GITHUB_REPO:=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')}"

grant_team_write() {
  local TEAM="$1"
  local EXISTING_ROLE

  # Empty role on 404 (no access) or any non-200; PUT below will surface auth failures.
  EXISTING_ROLE=$(gh api -H 'Accept: application/vnd.github.v3.repository+json' \
    "/orgs/UNCTAD-eRegistrations/teams/$TEAM/repos/$GITHUB_REPO" \
    --jq '.role_name' 2>/dev/null)

  case "$EXISTING_ROLE" in
    admin|maintain)
      echo "Skipped $TEAM — already has higher permission ($EXISTING_ROLE); not downgrading to write"
      return 0
      ;;
    write)
      echo "$TEAM already has write — re-applying for safety (no-op upsert)"
      ;;
    "")
      echo "Granting $TEAM write access to $GITHUB_REPO (no prior access)"
      ;;
    *)
      echo "$TEAM has '$EXISTING_ROLE' — upgrading to write"
      ;;
  esac

  gh api -X PUT "/orgs/UNCTAD-eRegistrations/teams/$TEAM/repos/$GITHUB_REPO" \
    -f permission=push
}

# Always: v4-development
grant_team_write v4-development

# Conditional: v4-fe-development (only if user confirmed frontend)
if [ "$GRANT_FE_TEAM" = "yes" ]; then
  grant_team_write v4-fe-development
else
  echo "Skipped v4-fe-development (not a frontend repo)"
fi
```

`permission=push` corresponds to the GitHub UI label `Role: write`.

### Step 4.6.3: Verify

```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh
: "${GITHUB_REPO:=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')}"

for TEAM in v4-development $([ "$GRANT_FE_TEAM" = "yes" ] && echo v4-fe-development); do
  echo "Verifying $TEAM..."
  gh api -H 'Accept: application/vnd.github.v3.repository+json' \
    "/orgs/UNCTAD-eRegistrations/teams/$TEAM/repos/$GITHUB_REPO" \
    --jq "{team: \"$TEAM\", repo: .name, role_name: .role_name}"
done
```

**Expected output (frontend repo)**:
```json
{"team": "v4-development", "repo": "<repo>", "role_name": "write"}
{"team": "v4-fe-development", "repo": "<repo>", "role_name": "write"}
```

### Step 4.6.4: Failure Handling

| Failure | Likely Cause | Action |
|---------|--------------|--------|
| HTTP 403 | Token lacks scope OR user not org admin | Verify `gh auth status` shows org admin on UNCTAD-eRegistrations; token needs at least `repo` + `read:org` (org admins can manage team-repo grants) |
| HTTP 404 (team) | Team renamed or removed | Check `gh api /orgs/UNCTAD-eRegistrations/teams/<slug>` — if gone, document new slug and update this step |
| HTTP 404 (repo) | `$GITHUB_REPO` wrong or not yet pushed | Confirm Phase 2 completed and repo exists on GitHub |
| Heuristic misfire | False positive/negative for frontend | User confirmation in Step 4.6.1 overrides heuristic — answer "No" to skip FE team, "Yes" to add it |

If a grant fails, do NOT abort migration — note in summary which team(s) need to be granted manually via Settings → Collaborators and teams.

---

## Phase 5: Summary & Developer Onboarding

### Step 5.1: Migration Summary

Report:
- Branches migrated: X
- Tags migrated: X
- Files updated: [list]
- CI/CD changes: [list]
- Release branch support: Added/Skipped
- Version initialization: Updated to X.Y.Z / Kept at X.Y.Z / Skipped

### Step 5.2: Developer Migration Notice

Ask: "Output developer migration instructions for sharing with the team?"

If yes, output:
```
<REPO_NAME> migration done, to switch to Github from your local repo, use either:

git remote set-url origin <TARGET_GITHUB_URL>

to directly target Github, or preserve Bitbucket as backup with:

git remote rename origin bitbucket
git remote add origin <TARGET_GITHUB_URL>
git fetch origin

and then on each local and non-committed branch use:

git branch -u origin/{branch} {branch}

If your branch is not building (can be checked in Github actions tab), you need to bring over .github/workflows/ci-cd.yml to your local branch and commit+push it
```

### Step 5.3: Manual Steps Checklist

**CRITICAL Workflow Configuration (verify FIRST):**
- [ ] Workflow has `permissions:` block with `contents: write`
- [ ] bump-version checkout has `clean: false`
- [ ] build-and-push-docker uses `git pull` (NOT `git fetch + git reset --hard`)

**Secrets & Runners:**
- [ ] Configure GitHub repository secrets (SSH_PRIVATE_KEY, DOCKERHUB_*, JENKINS_*, SLACK_WEBHOOK_URL, GHCR_TOKEN)
- [ ] Set up self-hosted runners with appropriate labels

**Repository Settings:**
- [ ] Verify "delete protection" ruleset is active (automated in Phase 4.5)
- [ ] Verify default branch is set correctly (automated in Step 2.6)
- [ ] Verify workflow triggers include all needed branches
- [ ] (Optional) Add additional branch protection rules (PR reviews, status checks) per team policy
- [ ] If `gh-pages` branch detected (Phase 0.5), configure GitHub Pages source manually

### Step 5.4: CI Verification (Optional)

Ask: "Verify first GitHub Actions run?"

If yes, run:

```bash
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh
: "${GITHUB_REPO:=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')}"

# --- Preconditions (most-common-path failure on fresh migrations) ---
# Combined into a single API call — version-stable across `gh` CLI ≥1.0
# (avoids `gh workflow view --yaml` which requires gh ≥2.13 — Ubuntu 22.04 ships 2.4.0)
DEFAULT_BRANCH=$(gh repo view "$GITHUB_REPO" --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null)

# 1. Fetch ci-cd.yml content from default branch (covers both "is it pushed" and "what does it contain")
CI_CD_CONTENT=$(gh api "repos/$GITHUB_REPO/contents/.github/workflows/ci-cd.yml" --jq '.content' 2>/dev/null | base64 --decode 2>/dev/null)
if [ -z "$CI_CD_CONTENT" ]; then
  echo "ERROR: ci-cd.yml not found on default branch ($DEFAULT_BRANCH) of $GITHUB_REPO."
  echo "  Fix: ensure ci-cd.yml is on the default branch ($DEFAULT_BRANCH), then re-run Step 5.4."
  echo "    git checkout $DEFAULT_BRANCH && git pull"
  echo "    git add .github/workflows/ci-cd.yml && git commit -m 'feat: GitHub Actions migration' && git push"
  exit 1
fi

# 2. Workflow must have workflow_dispatch trigger (otherwise gh workflow run returns 422)
if ! echo "$CI_CD_CONTENT" | grep -q "workflow_dispatch"; then
  echo "ERROR: ci-cd.yml does not have workflow_dispatch trigger; cannot manually trigger."
  echo "  Fix: add 'workflow_dispatch:' under the 'on:' key in ci-cd.yml, push to $DEFAULT_BRANCH, and re-run."
  exit 1
fi

# --- Trigger and watch (race-safe via timestamp filtering) ---

# 3. Pick target branch — develop if present, else repo default
TARGET_BRANCH=$(git ls-remote --heads origin develop | awk '{print $2}' | sed 's|refs/heads/||')
[ -z "$TARGET_BRANCH" ] && TARGET_BRANCH="$DEFAULT_BRANCH"

echo "Triggering workflow on branch: $TARGET_BRANCH"
TRIGGER_TIME=$(date -u +%s)  # capture BEFORE dispatch
gh workflow run ci-cd.yml --repo "$GITHUB_REPO" --ref "$TARGET_BRANCH"

# 4. Poll up to 90s for the run created AFTER our dispatch — avoids picking up a stale push-triggered run.
#    90s tolerates self-hosted-runner saturation (60s is tight; we've measured 45-60s queue time during contention).
RUN_ID=""
for i in $(seq 1 18); do
  sleep 5
  RUN_ID=$(gh run list --repo "$GITHUB_REPO" --workflow=ci-cd.yml --branch "$TARGET_BRANCH" \
    --limit 5 --json databaseId,createdAt \
    --jq "[.[] | select((.createdAt | fromdateiso8601) > $TRIGGER_TIME)] | .[0].databaseId")
  [ -n "$RUN_ID" ] && [ "$RUN_ID" != "null" ] && break
done
if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
  echo "ERROR: dispatch did not register within 90s. Check https://github.com/$GITHUB_REPO/actions"
  exit 1
fi

echo "Watching run: https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
gh run watch "$RUN_ID" --repo "$GITHUB_REPO" --exit-status --interval 15

# 5. Inspect outcome (json schema is stable; safe for piping)
gh run view "$RUN_ID" --repo "$GITHUB_REPO" --json conclusion,jobs \
  --jq '{conclusion, jobs: [.jobs[] | {name, conclusion}]}'
```

Manual checks (read-only, after the run completes):
- **Did version bump create a new commit?** — `git fetch origin && git log origin/$TARGET_BRANCH --oneline -3` (look for "chore(release): X.Y.Z" or similar)
- **Did Docker build use the bumped version?** — Check the build-and-push-docker job summary in `gh run view $RUN_ID --log` for the `VERSION=` line

If verification fails:
- `gh run view $RUN_ID --log-failed` — show only the failed steps
- Check [reference/troubleshooting.md](reference/troubleshooting.md) for common issues

---

## Phase 5.5: Validation Suite (MANDATORY)

**Purpose**: Run automated post-migration checks before declaring migration complete. This phase MUST run; do not mark migration "done" until all critical checks pass.

### Step 5.5.1: Run Validation Checks

```bash
# Restore migration state — required for $REPO_NAME, $HAS_LFS, $GITHUB_REPO, etc. (see Phase 0.5.1 CRITICAL note)
[ -f /tmp/migration-state.sh ] && source /tmp/migration-state.sh

# $GITHUB_REPO was exported by Step 2.6; fall back to local derivation if missing
: "${GITHUB_REPO:=$(git remote get-url origin | sed -E 's/.*github.com[:\/](.+)\.git/\1/')}"
SOURCE_REMOTE=$(git remote | grep -E '^(bitbucket|origin)$' | grep -v '^origin$' | head -1)
[ -z "$SOURCE_REMOTE" ] && SOURCE_REMOTE="origin"  # If user removed Bitbucket entirely

REPORT="/tmp/MIGRATION_VALIDATION-${REPO_NAME:-$(basename "$(pwd)")}.md"
echo "# Migration Validation Report" > "$REPORT"
echo "Date: $(date -Iseconds)" >> "$REPORT"
echo "Repo: $GITHUB_REPO" >> "$REPORT"
echo "" >> "$REPORT"
echo "| # | Check | Result | Details |" >> "$REPORT"
echo "|---|-------|--------|---------|" >> "$REPORT"

PASS=0; FAIL=0; WARN=0

check() {
  local n="$1" name="$2" status="$3" details="$4"
  echo "| $n | $name | $status | $details |" >> "$REPORT"
  case "$status" in
    PASS) PASS=$((PASS+1));;
    FAIL) FAIL=$((FAIL+1));;
    WARN) WARN=$((WARN+1));;
  esac
}

# 1. Connectivity
if git ls-remote origin >/dev/null 2>&1; then
  check 1 "GitHub connectivity" "PASS" "git ls-remote origin succeeded"
else
  check 1 "GitHub connectivity" "FAIL" "Cannot reach GitHub origin"
fi

# 2. Branch count parity (skip if no source remote left)
if git remote | grep -qx "$SOURCE_REMOTE" && [ "$SOURCE_REMOTE" != "origin" ]; then
  SRC=$(git ls-remote --heads "$SOURCE_REMOTE" | wc -l)
  GH=$(git ls-remote --heads origin | wc -l)
  if [ "$SRC" -eq "$GH" ]; then
    check 2 "Branch count parity" "PASS" "$GH branches"
  else
    check 2 "Branch count parity" "FAIL" "source=$SRC github=$GH"
  fi
else
  check 2 "Branch count parity" "WARN" "Source remote not present, cannot compare"
fi

# 3. Tag count parity
if git remote | grep -qx "$SOURCE_REMOTE" && [ "$SOURCE_REMOTE" != "origin" ]; then
  SRC=$(git ls-remote --tags "$SOURCE_REMOTE" | wc -l)
  GH=$(git ls-remote --tags origin | wc -l)
  if [ "$SRC" -eq "$GH" ]; then
    check 3 "Tag count parity" "PASS" "$GH tags"
  else
    check 3 "Tag count parity" "FAIL" "source=$SRC github=$GH"
  fi
else
  check 3 "Tag count parity" "WARN" "Source remote not present, cannot compare"
fi

# 4. Default branch
DEFAULT_BRANCH=$(gh repo view "$GITHUB_REPO" --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null)
if [ -n "$DEFAULT_BRANCH" ]; then
  check 4 "Default branch set" "PASS" "default=$DEFAULT_BRANCH"
else
  check 4 "Default branch set" "FAIL" "Could not query default branch"
fi

# 5. Workflow exists
if gh workflow list --repo "$GITHUB_REPO" 2>/dev/null | grep -q "ci-cd"; then
  check 5 "ci-cd.yml workflow registered" "PASS" "Listed in gh workflow list"
else
  check 5 "ci-cd.yml workflow registered" "WARN" "Not listed (workflow runs once after first push)"
fi

# 6. Required secrets
SECRETS=$(gh secret list --repo "$GITHUB_REPO" 2>/dev/null | awk '{print $1}')
for sec in SSH_PRIVATE_KEY DOCKERHUB_USERNAME DOCKERHUB_TOKEN GHCR_TOKEN SLACK_WEBHOOK_URL; do
  if echo "$SECRETS" | grep -qx "$sec"; then
    check "6.$sec" "Secret: $sec" "PASS" "configured"
  else
    check "6.$sec" "Secret: $sec" "WARN" "missing — required for some workflows"
  fi
done

# 7. Branch deletion ruleset
RULESET_OK=$(gh api "repos/$GITHUB_REPO/rulesets" --jq '.[] | select(.name=="delete protection" and .source_type=="Repository") | .enforcement' 2>/dev/null)
if [ "$RULESET_OK" = "active" ]; then
  check 7 "Delete protection ruleset" "PASS" "enforcement=active"
else
  check 7 "Delete protection ruleset" "FAIL" "Phase 4.5 ruleset missing or not active"
fi

# 8. LFS object parity (if applicable)
if [ "${HAS_LFS:-no}" = "yes" ]; then
  LFS_LOCAL=$(git lfs ls-files 2>/dev/null | wc -l)
  if [ "$LFS_LOCAL" -gt 0 ]; then
    check 8 "LFS files tracked" "PASS" "$LFS_LOCAL files (verify on GitHub UI)"
  else
    check 8 "LFS files tracked" "FAIL" "Expected LFS files but none found locally"
  fi
fi

# Tally
echo "" >> "$REPORT"
echo "## Summary: $PASS PASS, $FAIL FAIL, $WARN WARN" >> "$REPORT"

cat "$REPORT"
echo ""
echo "Report saved to: $REPORT"
```

### Step 5.5.2: Gate on Validation Result

| Result | Action |
|--------|--------|
| Any FAIL | Do NOT declare migration complete. Show failures, ask user if they want to invoke Phase 6 rollback or fix forward. |
| Only WARN | Show warnings, ask user to confirm acceptable before declaring complete. |
| All PASS | Declare migration complete. Output the report path to the user. |

Ask user (only if FAIL or WARN present):
- "Validation found N failures and M warnings. Continue or rollback?"
- Options: "Show details" | "Fix forward (manual)" | "Rollback (Phase 6)" | "Accept as-is"

---

## Phase 6: Rollback Procedure (Emergency)

**Purpose**: Restore the repository to its pre-migration state if migration fails between Phase 2 (push complete) and Phase 5.5 (validation complete).

**Prerequisite**: Phase 0.5 snapshot must exist at `$SNAPSHOT_PATH`. If `/tmp/migration-state.sh` is gone, snapshot cannot be auto-located and rollback must be done manually.

### When to Rollback

| Failure Point | Recommended Action |
|---------------|---------------------|
| Phase 2 push partially failed | Re-push (per Gate 2-3) — rollback usually NOT needed |
| Phase 3 workflow generation broken | Fix workflow forward — rollback NOT needed |
| Phase 4 file references corrupted | Restore individual files from snapshot — partial rollback |
| Phase 4.5 ruleset failed | Note in summary, continue — rollback NOT needed |
| Phase 5.5 validation FAIL on critical check | **Full rollback** — recommended |
| User decides to abort | **Full rollback** |

### Step 6.1: Confirm Rollback

**THIS IS DESTRUCTIVE.** Confirm with user before proceeding:

```
You are about to:
  1. Remove the GitHub remote
  2. Restore Bitbucket as origin
  3. Restore .github/, Jenkinsfile, package.json, etc. from snapshot
  4. The pushed-to GitHub repo will NOT be auto-deleted (do that manually if needed)

Snapshot path: $SNAPSHOT_PATH
Original origin: $(cat "$SNAPSHOT_PATH/origin-url.txt")

Proceed?
```

Options: "Yes, rollback" | "No, abort rollback"

### Step 6.2: Restore Local State

```bash
# Source the saved state
source /tmp/migration-state.sh

# Verify snapshot exists
if [ ! -d "$SNAPSHOT_PATH" ]; then
  echo "ERROR: Snapshot not found at $SNAPSHOT_PATH"
  echo "Manual rollback required — see snapshot directory listing:"
  ls /tmp/migration-snapshot/ 2>/dev/null
  exit 1
fi

# Sanity check: original Bitbucket remote must still exist before we tear down GitHub state
if ! git ls-remote "$ORIGINAL_REMOTE_URL" >/dev/null 2>&1; then
  echo "WARNING: Original remote at $ORIGINAL_REMOTE_URL is unreachable."
  echo "Rollback will leave you without a working origin. Abort and resolve manually."
  exit 2
fi

# Drop migration-introduced remotes (idempotent — || true handles missing)
git remote remove github 2>/dev/null || true
git remote remove bitbucket 2>/dev/null || true

# Use set-url-or-add pattern — never leaves origin undefined, even mid-rollback
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$ORIGINAL_REMOTE_URL"
else
  git remote add origin "$ORIGINAL_REMOTE_URL"
fi

# Refresh tracking refs
git fetch origin --prune
git fetch origin --tags

# Restore default-remote config
DEFAULT_REMOTE=$(cat "$SNAPSHOT_PATH/default-remote.txt")
if [ -n "$DEFAULT_REMOTE" ]; then
  git config checkout.defaultRemote "$DEFAULT_REMOTE"
else
  git config --unset checkout.defaultRemote 2>/dev/null || true
fi

# Restore current-branch upstream
CURRENT=$(git branch --show-current)
git branch -u "origin/$CURRENT" "$CURRENT" 2>/dev/null || true
```

### Step 6.3: Restore Files

```bash
# Restore Jenkinsfile if removed during Phase 3
if [ -f "$SNAPSHOT_PATH/Jenkinsfile.bak" ] && [ ! -f Jenkinsfile ]; then
  cp "$SNAPSHOT_PATH/Jenkinsfile.bak" Jenkinsfile
  echo "Restored: Jenkinsfile"
fi

# Restore .github if it was added/changed during Phase 3
if [ -d "$SNAPSHOT_PATH/.github.bak" ]; then
  rm -rf .github
  cp -r "$SNAPSHOT_PATH/.github.bak" .github
  echo "Restored: .github/"
elif [ -d .github ] && [ ! -d "$SNAPSHOT_PATH/.github.bak" ]; then
  rm -rf .github
  echo "Removed: .github/ (did not exist pre-migration)"
fi

# Restore files modified in Phase 4
for f in package.json pom.xml helm/Chart.yaml README.md; do
  base=$(basename "$f")
  if [ -f "$SNAPSHOT_PATH/${base}.bak" ]; then
    cp "$SNAPSHOT_PATH/${base}.bak" "$f"
    echo "Restored: $f"
  fi
done
```

### Step 6.4: Manual Cleanup Reminders

After local rollback, output to user:

```
LOCAL ROLLBACK COMPLETE.

Manual steps still required:
  1. (Optional) Delete the GitHub repo if you don't want it lingering:
     gh repo delete <owner/repo>  # asks confirmation
  2. (Optional) If the GitHub team was notified prematurely, send a correction.
  3. Verify with: git remote -v && git status
  4. Snapshot retained at: $SNAPSHOT_PATH (delete when satisfied with rollback)
```

### Step 6.5: Verify Rollback

```bash
git remote -v
git status
git log --oneline -5
git branch --show-current
[ -f Jenkinsfile ] && echo "Jenkinsfile: present"
[ -d .github ] && echo ".github: present" || echo ".github: absent (matches pre-migration)"
```

Compare against pre-migration state captured in `$SNAPSHOT_PATH/remotes.txt` and `$SNAPSHOT_PATH/branches.txt`.

---

## Error Handling

Common issues and quick fixes:

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| Version bump succeeds but commit doesn't appear | Missing `permissions: contents: write` | Add permissions block |
| Docker build uses OLD version after bump | Using `git fetch + reset` instead of `git pull` | Use `git pull` |
| Push fails | SSH key not configured | Check `ssh -T git@github.com` |
| Branch count mismatch | Partial push failure | Re-push branches |
| Docker `--ssh default` fails with "invalid empty ssh agent socket" | Manual SSH key file instead of ssh-agent | Use `webfactory/ssh-agent@v0.9.0` action |

**For detailed troubleshooting, see [reference/troubleshooting.md](reference/troubleshooting.md)**

---

## Reference Documentation

- [Critical Patterns](reference/critical-patterns.md) - Detailed explanations of all CRITICAL issues
- [Verbose Output](reference/verbose-output.md) - Summary and output patterns for workflows
- [Troubleshooting](reference/troubleshooting.md) - Recovery and rollback procedures

---

## Tools Used

- Bash: Git commands, file scanning, snapshot capture, `gh` CLI invocations
- Read/Edit: File updates
- Grep/Glob: Finding files with Bitbucket references
- AskUserQuestion: Interactive clarifications, validation gating, rollback confirmation
- TodoWrite: Progress tracking
- `gh` CLI (via Bash): Repo metadata (`gh repo edit`), rulesets (`gh api repos/.../rulesets`), secrets (`gh secret list`), workflows (`gh workflow list`)
