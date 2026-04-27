# Critical Patterns Reference

This document contains detailed explanations of critical patterns for GitHub Actions workflows. These are the most common causes of CI/CD failures after migration.

## Table of Contents

1. [Workflow Permissions Block](#1-workflow-permissions-block)
2. [Checkout Configuration](#2-checkout-configuration)
3. [Git Sync Method](#3-git-sync-method)
4. [GITHUB_TOKEN Push Limitation](#4-github_token-push-limitation)
5. [npm Version Bump Script Pattern](#5-npm-version-bump-script-pattern)
6. [Version Bump Pattern Verification](#6-version-bump-pattern-verification)
7. [Docker Build After Version Bump](#7-docker-build-after-version-bump)
8. [Java Project Version Sync](#8-java-project-version-sync)
9. [Git User Configuration](#9-git-user-configuration)
10. [Docker BuildKit SSH Agent](#10-docker-buildkit-ssh-agent)
11. [GITHUB_STEP_SUMMARY Required](#11-github_step_summary-required)
12. [Job Dependency Ordering](#12-job-dependency-ordering)
13. [Checkout Configuration for Jobs After Version Bump](#13-checkout-configuration-for-jobs-after-version-bump)
14. [npm Version Scripts Must Include git push](#14-npm-version-scripts-must-include-git-push)
15. [BRANCH_NAME Environment Variable](#15-branch_name-environment-variable)
16. [Summary Style Guidelines](#16-summary-style-guidelines)
17. [Runner Labels](#17-runner-labels)
18. [Feature Parity Verification](#18-feature-parity-verification)
19. [TAG_NAME Stale for Version-Based Tags](#19-tag_name-stale-for-version-based-tags)
20. [SSH Host Key Verification for External Repositories](#20-ssh-host-key-verification-for-external-repositories)
21. [Docker Hub Authentication Secret Names](#21-docker-hub-authentication-secret-names)
22. [Artifact Uploads Must Be Opt-In](#22-artifact-uploads-must-be-opt-in)
23. [Helm Chart Update Job Pattern](#23-helm-chart-update-job-pattern)

---

## 1. Workflow Permissions Block

**Root Cause ID:** PERM-001
**Severity:** CRITICAL
**Symptom:** Version bump job shows SUCCESS but new version commit never appears in repository

### Problem

GitHub Actions workflows MUST have explicit `permissions:` block to allow `GITHUB_TOKEN` to push commits. Without `contents: write`, the `git push` command fails silently (especially when npm scripts use `; exit 0;`).

### Required Pattern

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [...]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write      # CRITICAL: Required for git push
  checks: write
  pull-requests: write
  statuses: write
  actions: write

jobs:
  ...
```

### Symptoms of Missing Permissions

- Version bump job shows SUCCESS checkmark
- But new version commit never appears in repository
- npm script's `; exit 0;` masks the push failure
- Docker build uses OLD version instead of NEW version

### Verification Commands

```bash
# Check if workflow has permissions block
grep -A 5 "permissions:" .github/workflows/*.yml || echo "MISSING: permissions block!"

# Specifically check for contents: write
grep -E "contents:\s*write" .github/workflows/*.yml || echo "MISSING: contents: write permission!"
```

---

## 2. Checkout Configuration

**Root Cause ID:** CHECKOUT-001
**Severity:** CRITICAL
**Symptom:** Version bump retry fails or working directory becomes inconsistent

### Problem

The bump-version job checkout MUST include `clean: false` to prevent checkout from cleaning working directory state needed for retry logic.

### Required Pattern

```yaml
bump-version:
  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GITHUB_TOKEN }}
        clean: false  # CRITICAL: Prevents checkout from cleaning working directory
```

### Why `clean: false` Matters

- Without it, checkout may reset uncommitted changes
- Can interfere with version bump retry logic
- Working examples (BPA-Backend, camunda-boot) all use `clean: false`

---

## 3. Git Sync Method

**Root Cause ID:** SYNC-001
**Severity:** CRITICAL
**Symptom:** Docker build uses stale/old version after successful version bump

### Problem

Using `git fetch` followed by `git reset --hard origin/branch` does NOT properly update the remote tracking ref.

### WRONG Pattern (causes stale version)

```yaml
- name: Pull latest after version bump
  run: |
    git fetch origin ${{ github.ref_name }}
    git reset --hard origin/${{ github.ref_name }}
```

### Why It Fails

1. `git fetch origin <branch>` stores ref in `FETCH_HEAD`
2. BUT it does **NOT** update `refs/remotes/origin/<branch>`
3. `git reset --hard origin/<branch>` uses the stale remote tracking ref
4. Result: Working directory shows OLD version

### CORRECT Pattern

```yaml
- name: Pull latest after version bump
  run: |
    git pull origin ${{ github.ref_name }}
    echo "Pulled latest from origin/${{ github.ref_name }}"
```

### Why `git pull` Works

1. `git pull` = `git fetch` + `git merge` in one operation
2. Properly updates remote tracking refs
3. Working directory gets the NEW version

---

## 4. GITHUB_TOKEN Push Limitation

**Root Cause ID:** TOKEN-001
**Severity:** HIGH
**Symptom:** Workflow pattern that worked in Jenkins breaks in GitHub Actions

### Problem

Unlike Jenkins, GitHub Actions workflows triggered by pushes using `GITHUB_TOKEN` will NOT trigger new workflow runs. This is by design to prevent infinite loops.

### Impact

If Jenkins pipeline had separate stages like:
1. Bump version -> push commit -> trigger new build
2. New build picks up bumped version

This pattern BREAKS in GitHub Actions. The workflow must continue in the SAME run after version bump.

### WRONG Pattern (expecting new workflow after bump)

```yaml
develop)
  if [[ "$SHOULD_BUMP_VERSION" == "false" ]]; then
    SHOULD_BUILD_DOCKER="true"  # Only builds on chore commits
  fi
  ;;
```

### CORRECT Pattern (continue build after bump in same workflow)

```yaml
develop)
  SHOULD_BUILD_DOCKER="true"  # Always build, pull latest after bump
  ;;
```

### Build Job Requirements

1. Depend on bump-version job: `needs: [set-build-variables, bump-version]`
2. Pull latest after bump: `git pull origin ${{ github.ref_name }}`
3. Use condition: `bump-version.result == 'success' || bump-version.result == 'skipped'`

---

## 5. npm Version Bump Script Pattern

**Root Cause ID:** NPM-001
**Severity:** HIGH
**Symptom:** NEW_VERSION equals OLD_VERSION after bump

### Problem

npm scripts like `patch-release` often include built-in git push AND `exit 0`:

```json
"patch-release": "standard-version ...; git push origin HEAD:${BRANCH_NAME}; exit 0;"
```

The `exit 0` masks failures, and the script already pushes.

### WRONG Pattern (causes NEW_VERSION == OLD_VERSION)

```yaml
if npm run patch-release; then
  # WRONG: npm script already pushed, this is redundant
  if git push origin HEAD:$BRANCH_NAME; then
    # WRONG: Reading local package.json without pulling pushed changes
    NEW_VERSION=$(node -p "require('./package.json').version")
  fi
fi
```

### CORRECT Pattern (with retry logic)

```yaml
- name: Bump version with retry
  id: version_bump
  env:
    BRANCH_NAME: ${{ github.ref_name }}
  run: |
    MAX_RETRIES=5
    RETRY_DELAY=5

    for i in $(seq 0 $((MAX_RETRIES - 1))); do
      # Capture old version before bumping
      OLD_VERSION=$(node -p "require('./package.json').version")
      echo "Old version: $OLD_VERSION"

      # CRITICAL: Ensure clean state before bump attempt
      git checkout $BRANCH_NAME
      git reset --hard origin/$BRANCH_NAME
      git pull origin $BRANCH_NAME

      # Run version bump (npm script handles commit and push)
      if npm run patch-release; then
        echo "Version bump successful and pushed."

        # CRITICAL: Pull to get the changes we just pushed
        git pull origin $BRANCH_NAME
        NEW_VERSION=$(node -p "require('./package.json').version")
        echo "Successfully bumped version to $NEW_VERSION"

        # Set outputs
        echo "old_version=$OLD_VERSION" >> $GITHUB_OUTPUT
        echo "new_version=$NEW_VERSION" >> $GITHUB_OUTPUT
        echo "commit_hash=$(git rev-parse HEAD)" >> $GITHUB_OUTPUT

        exit 0
      else
        echo "Version bump failed on attempt $((i + 1))"
        if [ $i -lt $((MAX_RETRIES - 1)) ]; then
          echo "Retrying in $RETRY_DELAY seconds..."
          sleep $RETRY_DELAY
        fi
      fi
    done

    echo "Version bump failed after $MAX_RETRIES attempts"
    exit 1
```

### Key Rules

1. **NO redundant `git push`** - npm script already handles it
2. **Reset to clean state** before each attempt: `git checkout && git reset --hard && git pull`
3. **MUST `git pull`** after npm script succeeds to fetch pushed changes
4. **Read NEW_VERSION after pull** - local package.json now has correct bumped version
5. **ALWAYS install standard-version** - don't rely on npm cache
6. **Include retry logic** - concurrent pushes can cause race conditions

---

## 6. Version Bump Pattern Verification

**Root Cause ID:** VERIFY-001
**Severity:** MEDIUM
**Symptom:** Various version bump failures

### Verification Commands

```bash
# Check for missing clean state reset (CRITICAL BUG)
grep -A 30 "bump.*version" .github/workflows/*.yml | grep -E "git (checkout|reset)" || echo "MISSING: Clean state reset before version bump!"

# Check for proper retry loop structure
grep -A 30 "bump.*version" .github/workflows/*.yml | grep -E "for .* in \$\(seq|while.*RETRY" || echo "Check retry loop structure"
```

### Common Anti-Patterns to Fix

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| `git pull --rebase` on retry | Doesn't reset local changes | Use `git reset --hard origin/$BRANCH` |
| OLD_VERSION captured once at start | Stale if retry needed | Capture inside loop |
| `while [ $ATTEMPT -le ... ]` | Works but less readable | Use `for i in $(seq ...)` |
| No clean state before attempt | Dirty working tree breaks bump | Add `git checkout && git reset --hard && git pull` |

### Verification Questions

- "Does the version bump reset to clean state before each retry attempt?"
- "Is OLD_VERSION captured fresh inside the retry loop?"
- "Does it pull after successful bump to get the pushed changes?"

---

## 7. Docker Build After Version Bump

**Root Cause ID:** DOCKER-001
**Severity:** CRITICAL
**Symptom:** Docker build shows old version (e.g., 2.18.0) even though bump succeeded (2.18.0 -> 2.18.1)

### Problem

Docker build job uses old version because:
1. Checkout uses default ref (detached HEAD at trigger commit)
2. Pull is conditional or missing
3. Version is read before pulling latest

### CORRECT Pattern

```yaml
build-and-push-docker:
  needs: [set-build-variables, bump-version]
  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        ref: ${{ github.ref_name }}  # CRITICAL: checkout the branch, not trigger commit
        fetch-depth: 0

    - name: Pull latest after version bump
      run: |
        git pull origin ${{ github.ref_name }}  # ALWAYS pull, not conditional
        echo "Pulled latest changes"

    - name: Get current version
      id: version
      run: |
        VERSION=$(node -p "require('./package.json').version")  # Now has bumped version
        echo "version=${VERSION}" >> $GITHUB_OUTPUT
```

### Key Rules

1. **`ref: ${{ github.ref_name }}`** - Checkout the branch HEAD, not the trigger commit
2. **Unconditional pull** - Always pull, even if bump was skipped (harmless no-op)
3. **Read version AFTER pull** - Ensures bumped version is used

### Always Install Standard-Version

```yaml
# WRONG: Conditional install (cache may not include standard-version)
- name: Install dependencies
  if: steps.npm-cache.outputs.cache-hit != 'true'
  run: npm install

# CORRECT: Always install standard-version
- name: Install minimal dependencies for version bump
  run: |
    npm install --no-save standard-version
```

---

## 8. Java Project Version Sync

**Root Cause ID:** JAVA-001
**Severity:** HIGH
**Symptom:** JAR not found error in Docker build

### Problem

Java/Maven projects that also use npm for versioning need BOTH `pom.xml` and `package.json` to stay in sync. If only `package.json` is bumped, the Maven build creates a JAR with the old version.

### Detection

```bash
ls pom.xml package.json 2>/dev/null && echo "Java project with npm versioning detected"
```

### Required Configuration

#### 1. `.versionrc.js` must update BOTH files

```javascript
var xmlEngine = require('xml-js');

let bumpFiles = [
  {
    filename: "package.json",
    type: "json"
  },
  {
    filename: "pom.xml",
    type: "xml",
    updater: {
      readVersion: (contents) => {
        return xmlEngine.xml2js(contents).elements.filter(e => e.name === 'project')[0].elements.filter(e => e.name === 'version')[0].elements[0].text;
      },
      writeVersion: (contents, version) => {
        let xml = xmlEngine.xml2js(contents);
        xml.elements.filter(e => e.name === 'project')[0].elements.filter(e => e.name === 'version')[0].elements[0].text = version;
        return xmlEngine.js2xml(xml, { compact: false, spaces: "\t" });
      }
    }
  }
]

module.exports = {
  bumpFiles,
  releaseCommitMessageFormat: 'chore(release): {{currentTag}} [skip ci]'
}
```

#### 2. Install xml-js for version bump (MANDATORY for Java projects)

```yaml
# WRONG: Only installs standard-version
- name: Install dependencies for version bump
  run: npm install --no-save standard-version

# CORRECT: Includes xml-js for pom.xml parsing
- name: Install dependencies for version bump
  run: npm install --no-save standard-version xml-js
```

#### 3. Verification step during migration

```bash
if [ -f pom.xml ] && [ -f package.json ]; then
  if [ -f .versionrc.js ]; then
    grep -q "pom.xml" .versionrc.js || echo "WARNING: .versionrc.js does not include pom.xml!"
  else
    echo "WARNING: No .versionrc.js found for Java project with npm versioning!"
  fi
fi
```

### Common Symptom

Docker build fails with "JAR not found" because:
- package.json shows `2.18.0`
- pom.xml still shows `2.17.1`
- Maven builds `dataweave-2.17.1.jar`
- Docker looks for `dataweave-2.18.0.jar`

### Migration Checklist for Java Projects

- [ ] Verify `.versionrc.js` exists and includes pom.xml updater
- [ ] Verify `xml-js` is in devDependencies
- [ ] Update CI/CD to install `xml-js` alongside `standard-version`
- [ ] Verify both package.json and pom.xml have the same version

---

## 9. Git User Configuration

**Root Cause ID:** GIT-001
**Severity:** MEDIUM
**Symptom:** Commits fail with "Author identity unknown"

### Problem

All jobs that perform git operations (commit, push, tag) MUST configure the git user correctly.

### Required Pattern

```yaml
- name: Configure git
  run: |
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git config --global user.name "GitHub Actions Bot"
```

### Jobs Requiring Git Config

- Version bump jobs
- Production tag jobs
- Helm chart update jobs
- Any job that commits or pushes

### Never Use

- `git config user.email "actions@github.com"` (wrong email)
- `git config user.name "GitHub Actions"` (inconsistent name)
- Non-global config (use `--global` flag)

---

## 10. Docker BuildKit SSH Agent

**Root Cause ID:** SSH-001
**Severity:** CRITICAL
**Symptom:** Docker build fails with "invalid empty ssh agent socket: make sure SSH_AUTH_SOCK is set"

### Problem

Docker BuildKit's `--ssh default` option requires a running SSH agent with `SSH_AUTH_SOCK` environment variable set. Simply writing an SSH key to `~/.ssh/id_rsa` does NOT work.

### WRONG Pattern (causes SSH_AUTH_SOCK error)

```yaml
- name: Build docker image
  env:
    SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
  run: |
    mkdir -p ~/.ssh
    echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts

    docker build --ssh default --target common .  # FAILS!
```

### CORRECT Pattern (use webfactory/ssh-agent)

```yaml
- name: Set up SSH agent
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

- name: Add hosts to known_hosts
  run: |
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts
    ssh-keyscan -H bitbucket.org >> ~/.ssh/known_hosts

- name: Build docker image
  env:
    DOCKER_BUILDKIT: 1
  run: |
    docker build --ssh default --target common .  # Works!
```

### Why webfactory/ssh-agent Works

1. Starts an actual `ssh-agent` process
2. Adds the private key to the agent via `ssh-add`
3. Sets `SSH_AUTH_SOCK` environment variable
4. Docker BuildKit can now access the SSH agent socket

### When This Applies

- Any Docker build using `--ssh default` flag
- Dockerfiles with `RUN --mount=type=ssh` instructions
- Builds that need to clone private repos during image build

### Verification

```bash
# Check if workflow uses ssh-agent action for Docker builds
grep -B 10 "docker build.*--ssh" .github/workflows/*.yml | grep -q "webfactory/ssh-agent" || echo "WARNING: Missing ssh-agent for Docker BuildKit!"
```

---

## 11. GITHUB_STEP_SUMMARY Required

**Root Cause ID:** SUMMARY-001
**Severity:** HIGH
**Symptom:** No job summaries visible in GitHub Actions UI, poor visibility into pipeline status

### Problem

GitHub Actions workflows should write rich markdown summaries to `$GITHUB_STEP_SUMMARY` for every job. Without these summaries, users must dig through logs to understand what happened.

### WRONG Pattern (no summaries)

```yaml
jobs:
  build:
    steps:
      - name: Build
        run: docker build .
      # No summary step - users see nothing in the UI
```

### CORRECT Pattern (with summary)

```yaml
jobs:
  build:
    steps:
      - name: Build
        run: docker build .

      - name: Build summary
        run: |
          echo "## 🐳 Docker Build Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Image:** \`myapp:${{ steps.version.outputs.tag }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Branch:** \`${{ github.ref_name }}\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "✅ Docker image built and pushed successfully" >> $GITHUB_STEP_SUMMARY
```

### Required Summaries Per Job

| Job | Emoji | Title |
|-----|-------|-------|
| set-build-variables | 📋 | Build Configuration |
| helm-chart-update | ⎈ | Helm Chart Updated |
| bump-version | 🔢 | Version Bumped |
| build-and-push-docker | 🐳 | Docker Build Summary |
| tag-production | 🏷️ | Production Release Tagged |
| trigger-jenkins-deploy | 🚀 | Jenkins Deployment Triggered |
| notify-failure | ❌ | Pipeline Failed |

### Summary Content Guidelines

1. **Always include:**
   - Branch name
   - Version/tag
   - Key outputs from the job

2. **Use consistent formatting:**
   - Heading with emoji
   - Bulleted list of key-value pairs
   - Success/failure indicator at the end

3. **For conditional jobs:**
   - Show what was skipped and why
   - Use ⏭️ for skipped items, ✅ for enabled

### Verification

```bash
# Check if all jobs have summaries
grep -c "GITHUB_STEP_SUMMARY" .github/workflows/ci-cd.yml
# Should return number >= number of jobs
```

---

## 12. Job Dependency Ordering

**Root Cause ID:** ORDER-001
**Severity:** CRITICAL
**Symptom:** Deployment triggers before production tagging completes, race conditions

### Problem

The `trigger-jenkins-deploy` job MUST wait for `tag-production` to complete. Otherwise, deployment might trigger before the production tag is created.

### WRONG Pattern (missing dependency)

```yaml
trigger-jenkins-deploy:
  needs: [set-build-variables, build-and-push-docker]
  # Missing tag-production! Deploy might start before tag is created
```

### CORRECT Pattern (proper dependency chain)

```yaml
trigger-jenkins-deploy:
  needs: [set-build-variables, build-and-push-docker, tag-production]
  if: |
    always() &&
    needs.build-and-push-docker.result == 'success' &&
    (needs.tag-production.result == 'success' || needs.tag-production.result == 'skipped') &&
    (github.ref_name == 'develop' || startsWith(github.ref_name, 'feature/'))
```

### Why This Matters

1. **tag-production** creates the version tag on master
2. **trigger-jenkins-deploy** notifies Jenkins to deploy
3. If deploy triggers first, Jenkins might pull untagged code
4. Using `skipped` check allows deploy to proceed on non-master branches

### Correct Job Execution Order

```
set-build-variables
       │
       ├──► helm-chart-update (if helm commit)
       │
       ├──► bump-version (if develop/release)
       │         │
       │         ▼
       └──► build-and-push-docker
                   │
                   ▼
             tag-production (master only)
                   │
                   ▼
          trigger-jenkins-deploy
```

### Verification

```bash
# Check trigger-jenkins-deploy depends on tag-production
grep -A 3 "trigger-jenkins-deploy:" .github/workflows/ci-cd.yml | grep -q "tag-production" || echo "WARNING: Missing tag-production dependency!"
```

---

## 13. Checkout Configuration for Jobs After Version Bump

**Root Cause ID:** FETCH-001
**Severity:** CRITICAL
**Symptom:** Docker build or tag job uses OLD version even though version bump succeeded

### Problem

Jobs that run after version bump need to pull the latest commit. The checkout configuration must include both `fetch-depth: 0` AND `clean: false` for `git pull` to work correctly.

### CORRECT Pattern (from DS-Backend - proven working)

```yaml
build-and-push-docker:
  needs: [set-build-variables, bump-version]
  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        ref: ${{ github.ref_name }}
        fetch-depth: 0
        clean: false

    - name: Pull latest after version bump
      run: |
        git pull origin ${{ github.ref_name }}

    - name: Get current version
      id: version
      run: |
        VERSION=$(node -p "require('./package.json').version")
        echo "version=$VERSION" >> $GITHUB_OUTPUT
```

### Key Requirements

1. **`ref: ${{ github.ref_name }}`** - Checkout the branch, not the trigger commit
2. **`fetch-depth: 0`** - Fetch full history (needed for git operations)
3. **`clean: false`** - Don't clean working directory
4. **`git pull origin ${{ github.ref_name }}`** - Pull latest AFTER checkout
5. **Read version AFTER pull** - Ensures bumped version is used

### Working Examples

**DS-Backend** (build-docker-images job):
```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.ref_name }}
    fetch-depth: 0
    clean: false

- name: Pull latest changes after version bump
  run: |
    git pull origin ${{ github.ref_name }}
```

### Verification

```bash
# Check build job has correct checkout config
grep -A 8 "build.*docker" .github/workflows/ci-cd.yml | grep -E "(fetch-depth|clean|ref:)"

# Should show:
# ref: ${{ github.ref_name }}
# fetch-depth: 0
# clean: false
```

---

## 14. npm Version Scripts Must Include git push

**Root Cause ID:** PUSH-001
**Severity:** CRITICAL
**Symptom:** Version bump job succeeds but new version commit never appears in repository, downstream jobs use OLD version

### Problem

The `package.json` version bump scripts (patch-release, minor-release, etc.) must include an explicit `git push` command. Without it, `standard-version` only creates a local commit that never reaches the remote repository.

### WRONG Pattern (version not pushed)

```json
{
  "scripts": {
    "patch-release": "standard-version --skip.tag=true --skip.changelog --no-verify --release-as patch"
  }
}
```

### CORRECT Pattern (includes push)

```json
{
  "scripts": {
    "bump-version": "standard-version --skip.tag=true --skip.changelog --no-verify; git push origin HEAD:${BRANCH_NAME}; exit 0;",
    "patch-release": "standard-version --skip.tag=true --skip.changelog --no-verify --release-as patch; git push origin HEAD:${BRANCH_NAME}; exit 0;",
    "minor-release": "standard-version --skip.tag=true --skip.changelog --no-verify --release-as minor; git push origin HEAD:${BRANCH_NAME}; exit 0;",
    "major-release": "standard-version --skip.tag=true --skip.changelog --no-verify --release-as major; git push origin HEAD:${BRANCH_NAME}; exit 0;"
  }
}
```

### Key Components

1. **`git push origin HEAD:${BRANCH_NAME}`** - Pushes the version bump commit to the remote
2. **`${BRANCH_NAME}`** - Environment variable set by the workflow (e.g., `develop`, `release/2.17`)
3. **`; exit 0;`** - Ensures the script exits successfully even if there are minor issues

### Why This Is Critical

1. `standard-version` only creates a LOCAL commit
2. Without `git push`, the commit stays local to the runner
3. Downstream jobs checkout from remote, which has the OLD version
4. Even with `git pull` in downstream jobs, there's nothing new to pull

### Verification During Migration

```bash
# Check if version scripts include git push
grep -E "(patch|minor|major)-release" package.json | grep -q "git push" || echo "WARNING: Version scripts missing git push!"

# Working example check
grep "git push origin HEAD" package.json && echo "OK: Scripts include git push"
```

### Common Symptoms

- bump-version job shows SUCCESS with new version in logs
- Build job shows OLD version even after `git pull`
- Debug output shows same commit SHA before and after pull
- Version in summary: bump shows 2.18.1→2.18.2, Docker build shows 2.18.1

---

## 15. BRANCH_NAME Environment Variable

**Root Cause ID:** ENV-001
**Severity:** CRITICAL
**Symptom:** Version bump commits locally but git push fails with "fatal: invalid refspec"

### Problem

npm version scripts use `${BRANCH_NAME}` which is a Jenkins environment variable. In GitHub Actions, this variable is NOT automatically available and must be explicitly set.

### WRONG Pattern (BRANCH_NAME undefined)

```yaml
- name: Bump version
  run: npm run patch-release  # Script uses ${BRANCH_NAME} but it's undefined!
```

### CORRECT Pattern (explicit BRANCH_NAME)

```yaml
- name: Bump version
  env:
    BRANCH_NAME: ${{ github.ref_name }}
  run: npm run patch-release  # Now ${BRANCH_NAME} resolves correctly
```

### Where This Applies

Any step that runs npm version scripts containing `git push origin HEAD:${BRANCH_NAME}`:
- `bump-version` step
- `patch-release` step
- `minor-release` step
- `major-release` step

### Verification During Migration

```bash
# Check if package.json scripts use BRANCH_NAME
grep "BRANCH_NAME" package.json && echo "INFO: Scripts require BRANCH_NAME env var"

# Check if workflow sets BRANCH_NAME
grep -B 5 "npm run.*release" .github/workflows/ci-cd.yml | grep -q "BRANCH_NAME:" || echo "WARNING: BRANCH_NAME not set for version scripts!"
```

### Common Symptoms

- Local commit created but push fails
- Error: "fatal: invalid refspec 'HEAD:'"
- Version bump job shows partial success but commit never appears on remote

---

## 16. Summary Style Guidelines

**Root Cause ID:** STYLE-001
**Severity:** MEDIUM
**Symptom:** Inconsistent job summaries across repositories, poor readability

### Problem

GitHub Action job summaries should follow a consistent style for readability and professionalism. Using emojis and ad-hoc formats creates visual noise.

### WRONG Pattern (inconsistent, emoji-heavy)

```yaml
- name: Build variables summary
  run: |
    echo "## 📋 Build Configuration" >> $GITHUB_STEP_SUMMARY
    echo "- **Branch:** \`${{ github.ref_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Should bump:** \`true\`" >> $GITHUB_STEP_SUMMARY
    echo "✅ All good!" >> $GITHUB_STEP_SUMMARY
```

### CORRECT Pattern (clean, structured)

```yaml
- name: Build variables summary
  run: |
    echo "## Build Configuration" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Branch Information" >> $GITHUB_STEP_SUMMARY
    echo "- **Branch:** \`${{ github.ref_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Commit:** ${{ steps.commit.outputs.subject }}" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Build Variables" >> $GITHUB_STEP_SUMMARY
    echo "- **Docker Tag:** \`${{ steps.tag.outputs.tag_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Version:** \`${{ steps.version.outputs.version }}\`" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Pipeline Decisions" >> $GITHUB_STEP_SUMMARY
    if [ "${{ steps.bump.outputs.should_bump }}" == "true" ]; then
      echo "- Version Bump: Enabled" >> $GITHUB_STEP_SUMMARY
    else
      echo "- Version Bump: Skipped" >> $GITHUB_STEP_SUMMARY
    fi
    if [ "${{ steps.build.outputs.should_build }}" == "true" ]; then
      echo "- Docker Build: Enabled" >> $GITHUB_STEP_SUMMARY
    else
      echo "- Docker Build: Skipped" >> $GITHUB_STEP_SUMMARY
    fi
```

### Style Rules

1. **No emojis in headers** - Use plain `## Title` format
2. **Use subsections** - Organize with `###` for related content
3. **Pipeline decisions** - Show `Enabled`/`Skipped` status, not `true`/`false`
4. **Consistent key names** - Use `Version:`, `Branch:`, `Docker Tag:`, etc.
5. **Empty lines** - Separate sections with `echo ""` for readability

### Summary Templates Per Job

**set-build-variables:**
```
## Build Configuration
### Branch Information
### Build Variables
### Pipeline Decisions
```

**bump-version:**
```
## Version Bumped
- Old Version
- New Version
- Branch
```

**build-and-push-docker:**
```
## Docker Build Summary
- Image
- Version
- Environment
```

**helm-chart-update:**
```
## Helm Chart Update
- Helm chart repository updated on GitHub
```

### Reference Implementations

See existing workflows for correct style. Pick the closest-precedent for the project being migrated:
- [`UNCTAD-eRegistrations/Mule4` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/Mule4/blob/develop/.github/workflows/ci-cd.yml) — closest precedent for **Mule3** (same Maven `mule-application` shape + identical `standard-version`/`xml-js` tooling; runtime differs CE 4.7 vs CE 3.9, and Mule4 has no helm chart — for the helm-chart-update job reference ActiveMQ)
- [`UNCTAD-eRegistrations/DS-Backend` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/DS-Backend/blob/develop/.github/workflows/ci-cd.yml) — Python (Django) project; `package.json` + `standard-version` for version-bump tooling
- [`UNCTAD-eRegistrations/BPA-Backend` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/BPA-Backend/blob/develop/.github/workflows/ci-cd.yml) — Java / Spring Boot (Maven build); `standard-version` bump tooling syncs version to `pom.xml` via `xml-js`

---

## 17. Runner Labels

**Root Cause ID:** RUNNER-001
**Severity:** CRITICAL
**Symptom:** Jobs fail with "no matching runner found" or run on wrong runner type

### Problem

Self-hosted runners have specific labels that must be used correctly. Using incorrect labels like `[self-hosted, linux]` or `[self-hosted, linux, docker]` will either fail to match runners or run on inappropriate hardware.

### WRONG Pattern (incorrect labels)

```yaml
jobs:
  build:
    runs-on: [self-hosted, linux]  # Too generic, may match wrong runner

  docker-build:
    runs-on: [self-hosted, linux, docker]  # Label doesn't exist!
```

### CORRECT Pattern (proper labels)

```yaml
jobs:
  # Regular jobs (set-build-variables, bump-version, tag-production, notify-failure)
  regular-job:
    runs-on: [self-hosted, linux, build, normal]

  # Helm chart update
  helm-chart-update:
    runs-on: [self-hosted, linux, build]

  # Docker build jobs (resource intensive)
  build-and-push-docker:
    runs-on: [self-hosted, linux, build, heavy]

  # Jenkins trigger jobs
  trigger-jenkins-deploy:
    runs-on: [self-hosted, linux, jenkins]
```

### Label Mapping

| Job Type | Labels |
|----------|--------|
| Regular jobs (set-build-variables, bump-version, tag-production, notify-failure) | `[self-hosted, linux, build, normal]` |
| Helm chart update | `[self-hosted, linux, build]` |
| Docker builds | `[self-hosted, linux, build, heavy]` |
| Jenkins triggers | `[self-hosted, linux, jenkins]` |

### Why This Matters

1. **`build, normal`** - Standard runners for lightweight operations
2. **`build`** (without normal) - Helm chart jobs that need helm CLI and git access but are not resource-intensive
3. **`build, heavy`** - High-resource runners for Docker builds, compilations
4. **`jenkins`** - Runners with Jenkins CLI access for deployment triggers

### Verification

```bash
# Check runner labels in workflow
grep "runs-on:" .github/workflows/ci-cd.yml | sort | uniq -c

# Expected patterns:
# - [self-hosted, linux, build, normal]
# - [self-hosted, linux, build, heavy]
# - [self-hosted, linux, jenkins]
```

### Reference

See working examples. Pick the closest-precedent for the project being migrated:
- [`UNCTAD-eRegistrations/Mule4` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/Mule4/blob/develop/.github/workflows/ci-cd.yml) — closest precedent for **Mule3** toolchain shape (runtime differs; no helm chart in Mule4)
- [`UNCTAD-eRegistrations/DS-Backend` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/DS-Backend/blob/develop/.github/workflows/ci-cd.yml)
- [`UNCTAD-eRegistrations/BPA-Backend` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/BPA-Backend/blob/develop/.github/workflows/ci-cd.yml)

---

## 18. Feature Parity Verification

**Root Cause ID:** PARITY-001
**Severity:** CRITICAL (BLOCKING)
**Symptom:** CI/CD pipeline missing functionality that existed in Jenkinsfile, causing build failures or incomplete deployments

### Problem

When migrating from Jenkinsfile to GitHub Actions, it is CRITICAL to ensure EVERY feature from the original Jenkinsfile is present in the generated ci-cd.yml. Missing features cause:
- Build failures (missing dependencies, tools, or cloned repos)
- Incomplete deployments (missing steps or notifications)
- Silent failures (features that worked before now don't run)

### MANDATORY Pre-Generation Checklist

Before generating ANY ci-cd.yml, you MUST:

1. **Extract ALL stages from Jenkinsfile:**
   ```bash
   grep -E "stage\s*\(" Jenkinsfile | sed "s/.*stage('\([^']*\)').*/\1/"
   ```

2. **Extract ALL shell commands:**
   ```bash
   grep -E "sh\s+['\"]" Jenkinsfile
   ```

3. **Extract ALL git clone operations:**
   ```bash
   grep -E "git clone" Jenkinsfile
   ```

4. **Extract ALL credential usages:**
   ```bash
   grep -E "(sshagent|withCredentials|credentials)" Jenkinsfile
   ```

5. **Extract ALL environment variables:**
   ```bash
   grep -E "(environment|env\.)" Jenkinsfile
   ```

### Feature Parity Verification Table

Create this table BEFORE generating ci-cd.yml:

| Jenkinsfile Feature | Present in ci-cd.yml | Notes |
|---------------------|---------------------|-------|
| Stage: Install npm packages | ✅/❌ | |
| Stage: Increase version number | ✅/❌ | |
| Stage: Clone eregistrations-tools | ✅/❌ | **COMMONLY MISSED** |
| Stage: Build docker image | ✅/❌ | |
| Stage: Push to dockerhub | ✅/❌ | |
| Stage: Helm chart update | ✅/❌ | |
| Stage: Tag version for production | ✅/❌ | |
| Post: Slack notification | ✅/❌ | |
| Post: Email notification | ✅/❌ | |
| Credential: SSH keys | ✅/❌ | |
| Credential: Docker login | ✅/❌ | |

### Common Missed Features

These are frequently missed during migration:

1. **External repository clones:**
   ```groovy
   // Jenkinsfile
   sh "git clone git@bitbucket.org:org/some-tools.git"
   ```
   MUST become:
   ```yaml
   # ci-cd.yml
   - name: Clone some-tools
     run: |
       rm -rf some-tools
       git clone git@bitbucket.org:org/some-tools.git
   ```

2. **Translation extraction:**
   ```groovy
   // Jenkinsfile
   sh "npm run extract-keys"
   sh "git add src/assets/translation-keys.json"
   sh "git commit -m 'chore: update translations'"
   ```

3. **Parallel stages:**
   ```groovy
   // Jenkinsfile
   parallel {
     stage("Clone tools") { ... }
     stage("Run tests") { ... }
   }
   ```

4. **Post-build notifications:**
   ```groovy
   // Jenkinsfile
   post {
     failure {
       slackSend(...)
       step([$class: 'Mailer', ...])
     }
   }
   ```

### BLOCKING Verification Step

After generating ci-cd.yml, you MUST run this verification:

```bash
# Count stages in Jenkinsfile
JENKINS_STAGES=$(grep -cE "stage\s*\(" Jenkinsfile)

# Count jobs in ci-cd.yml
ACTIONS_JOBS=$(grep -cE "^\s{2}\w+(-\w+)*:\s*$" .github/workflows/ci-cd.yml)

echo "Jenkinsfile stages: $JENKINS_STAGES"
echo "GitHub Actions jobs: $ACTIONS_JOBS"

# Extract git clones from Jenkinsfile
echo "=== Git clones in Jenkinsfile ==="
grep "git clone" Jenkinsfile

# Verify same clones exist in ci-cd.yml
echo "=== Git clones in ci-cd.yml ==="
grep "git clone" .github/workflows/ci-cd.yml

# If any clone is missing, STOP and add it!
```

### Symptoms of Missing Features

- Docker build fails with "file not found" (missing cloned repo)
- Version bump works but translations not updated (missing extract-keys)
- Build succeeds but no Slack notification on failure (missing post block)
- Helm chart not updated when commit starts with "helm" (missing helm job)

### Migration Workflow (MANDATORY)

1. **READ entire Jenkinsfile** - Don't skim, read every line
2. **CREATE feature checklist** - List every stage, every shell command
3. **GENERATE ci-cd.yml** - Include ALL features from checklist
4. **VERIFY parity** - Check every item on checklist is present
5. **TEST on branch** - Run workflow and verify all features execute

### Example: statistics-frontend Missing Clone

**Jenkinsfile had:**
```groovy
stage('Clone eregistrations tools') {
    steps {
        sh "rm -rf eregistrations-tools"
        sh "git clone git@bitbucket.org:unctad/eregistrations-tools.git"
    }
}
```

**Initial ci-cd.yml MISSED this entirely**, causing:
```
#34 ERROR: "/usr/src/app/eregistrations-tools/scripts/parse-docker-secret/script.sh": not found
```

**Fix required adding:**
```yaml
- name: Clone eregistrations-tools
  run: |
    rm -rf eregistrations-tools
    git clone git@bitbucket.org:unctad/eregistrations-tools.git
```

### Prevention

NEVER skip the feature parity verification. Missing a single `git clone` or shell command can break the entire build. This is not a "nice to have" - it is a BLOCKING requirement for migration.

---

## 19. TAG_NAME Stale for Version-Based Tags

**Root Cause ID:** TAG-001
**Severity:** CRITICAL
**Symptom:** Docker image tagged with OLD version (e.g., 2.17.1) even though bump succeeded and build used NEW version (2.17.2)

### Problem

For release/* and master branches, TAG_NAME is set to VERSION in `set-build-variables`. This job runs BEFORE `bump-version`, so TAG_NAME contains the OLD version. Even if `build-and-push-docker` correctly pulls the new version and builds with it, it still uses the stale TAG_NAME from `set-build-variables`.

### Why Patterns #7 and #13 Don't Catch This

Patterns #7 and #13 ensure the build job:
- Checks out the branch (not trigger commit)
- Uses `git pull` (not fetch + reset)
- Reads VERSION after pull

But they DON'T address that TAG_NAME is a separate variable passed from `set-build-variables`, which ran BEFORE the bump.

### WRONG Pattern (TAG_NAME is stale)

```yaml
set-build-variables:
  steps:
    - run: |
        VERSION=$(node -p "require('./package.json').version")  # 2.17.1
        case "$BRANCH_NAME" in
          release/*|master)
            TAG_NAME="${VERSION}"  # TAG_NAME = 2.17.1 (OLD!)
            ;;
        esac

build-and-push-docker:
  needs: [set-build-variables, bump-version]
  steps:
    - run: git pull  # Gets 2.17.2
    - run: VERSION=$(node -p "...")  # VERSION = 2.17.2 (correct)
    - run: |
        TAG_NAME=${{ needs.set-build-variables.outputs.tag_name }}  # 2.17.1 (STALE!)
        docker build --build-arg VERSION=${VERSION} -t image:${TAG_NAME}  # Built with 2.17.2, tagged as 2.17.1!
```

### CORRECT Pattern (override TAG_NAME for version-based branches)

```yaml
build-and-push-docker:
  steps:
    - name: Build Docker image
      run: |
        VERSION=${{ steps.version.outputs.version }}
        TAG_NAME=${{ needs.set-build-variables.outputs.tag_name }}

        # For release branches and master, TAG_NAME should be the current version (after bump)
        if [[ "${{ github.ref_name }}" == release/* ]] || [[ "${{ github.ref_name }}" == "master" ]]; then
          TAG_NAME="${VERSION}"
          echo "Overriding TAG_NAME with current version for release/master branch"
        fi

        # Export for subsequent steps
        echo "DOCKER_TAG=${TAG_NAME}" >> $GITHUB_ENV

        docker build --build-arg VERSION=${VERSION} -t image:${TAG_NAME} .

    - name: Push Docker image
      run: docker push image:${{ env.DOCKER_TAG }}
```

### Key Rules

1. **ALWAYS override TAG_NAME** for release/* and master branches in the build job
2. **Use GITHUB_ENV** to pass the corrected tag to subsequent steps (push, summary)
3. **Don't trust** `set-build-variables.outputs.tag_name` for version-based tags after bump

### Verification

```bash
# Check if build job overrides TAG_NAME for release/master
grep -A 10 "Build Docker image" .github/workflows/ci-cd.yml | grep -E "release.*master.*TAG_NAME" || echo "WARNING: TAG_NAME not overridden for release/master!"

# Check if push uses env.DOCKER_TAG
grep "docker push" .github/workflows/ci-cd.yml | grep -E "env.DOCKER_TAG|DOCKER_TAG" || echo "WARNING: Push may use stale tag!"
```

### Symptoms

- Version bump logs show: `2.17.1 -> 2.17.2`
- Docker build logs show: `VERSION: 2.17.2`
- Docker push logs show: `Pushed image:2.17.1` (WRONG!)
- DockerHub shows tag `2.17.1` with content built from `2.17.2`

---

## 20. SSH Host Key Verification for External Repositories

**Root Cause ID:** SSH-002
**Severity:** CRITICAL
**Symptom:** `git clone` fails with "Host key verification failed" when cloning from Bitbucket or other external hosts

### Problem

When using `webfactory/ssh-agent` to set up SSH authentication, the SSH agent is configured but the remote host's key is NOT added to `~/.ssh/known_hosts`. This causes `git clone` to fail with:

```
Cloning into 'eregistrations-tools'...
Host key verification failed.
fatal: Could not read from remote repository.
```

### WRONG Pattern (missing known_hosts)

```yaml
- name: Setup SSH
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

- name: Clone external repo
  run: git clone git@bitbucket.org:org/repo.git  # FAILS!
```

### CORRECT Pattern (add host to known_hosts)

```yaml
- name: Setup SSH
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

- name: Add Bitbucket to known hosts
  run: |
    mkdir -p ~/.ssh
    ssh-keyscan -t rsa bitbucket.org >> ~/.ssh/known_hosts

- name: Clone external repo
  run: git clone git@bitbucket.org:org/repo.git  # Works!
```

### Multiple Hosts

If cloning from multiple hosts (e.g., both GitHub and Bitbucket):

```yaml
- name: Add hosts to known_hosts
  run: |
    mkdir -p ~/.ssh
    ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
    ssh-keyscan -t rsa bitbucket.org >> ~/.ssh/known_hosts
```

### When This Applies

- ANY `git clone` to an external SSH host
- Jobs that clone dependencies from Bitbucket via SSH (e.g., eregistrations-tools in docker build)
- Docker builds that clone repos inside the Dockerfile (use BuildKit SSH mount instead)

**Note:** The `helm-chart-update` job does NOT require SSH or ssh-keyscan. It uses HTTPS with `GHCR_TOKEN` for both `helm repo add` and git clone to `UNCTAD-eRegistrations/Eregistrations-Helm` on GitHub. See [Pattern #23](#23-helm-chart-update-job-pattern).

### Verification

```bash
# Check for ssh-keyscan before git clone
grep -B 5 "git clone git@" .github/workflows/ci-cd.yml | grep -q "ssh-keyscan" || echo "WARNING: Missing ssh-keyscan before git clone!"
```

### Symptoms

- Job fails at `git clone` step
- Error: "Host key verification failed"
- Error: "Could not read from remote repository"

---

## 21. Docker Hub Authentication Secret Names

**Root Cause ID:** DOCKER-AUTH-001
**Severity:** CRITICAL
**Symptom:** Docker login fails with "Password required" error

### Problem

Using incorrect secret name for Docker Hub authentication. The docker/login-action receives an empty string for the password parameter.

### WRONG Pattern

```yaml
- name: Login to DockerHub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_PASSWORD }}  # WRONG NAME!
```

### CORRECT Pattern

```yaml
- name: Login to DockerHub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}  # Correct: DOCKERHUB_TOKEN
```

### Standard Secret Names

| Secret Name | Purpose |
|-------------|---------|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub password or access token |
| `SSH_PRIVATE_KEY` | SSH key for Bitbucket/GitHub access |
| `GHCR_TOKEN` | GitHub PAT for helm repo auth and Eregistrations-Helm clone |
| `JENKINS_URL` | Jenkins server URL |
| `JENKINS_USER` | Jenkins username |
| `JENKINS_API_TOKEN` | Jenkins API token |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications |

### Verification

```bash
# Check Docker login uses correct secret name
grep -A 3 "docker/login-action" .github/workflows/ci-cd.yml | grep "DOCKERHUB_TOKEN" || echo "WARNING: Wrong Docker secret name!"
```

### Symptoms

- Docker login step fails immediately
- Error: "Password required"
- Job never reaches Docker build step

---

## 22. Artifact Uploads Must Be Opt-In

**Root Cause ID:** ARTIFACT-001
**Severity:** HIGH
**Symptom:** GitHub Actions artifact storage quota exceeded, unnecessary storage consumption

### Problem

GitHub has storage limitations for artifacts. Uploading artifacts (like test results, coverage reports) on every push event quickly consumes storage quota. Artifact uploads should be opt-in only, available via manual workflow dispatch.

### WRONG Pattern (uploads on every build)

```yaml
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: junit.xml
    retention-days: 30
```

### CORRECT Pattern (opt-in via workflow_dispatch)

```yaml
on:
  push:
    branches: [...]
  workflow_dispatch:
    inputs:
      FORCE_BUILD:
        description: 'Force build/push regardless of branch rules'
        required: false
        default: false
        type: boolean
      UPLOAD_ARTIFACTS:
        description: 'Upload test results artifact (only available via manual run)'
        required: false
        default: false
        type: boolean

jobs:
  build:
    steps:
      - name: Run tests
        run: npm run test:coverage

      - name: Upload test results
        if: always() && github.event_name == 'workflow_dispatch' && inputs.UPLOAD_ARTIFACTS == true
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: junit.xml
          retention-days: 30
```

### Key Rules

1. **Add `UPLOAD_ARTIFACTS` input** to `workflow_dispatch` (boolean, default: false)
2. **Condition artifact upload** on:
   - `github.event_name == 'workflow_dispatch'` (manual trigger only)
   - `inputs.UPLOAD_ARTIFACTS == true` (explicit opt-in)
3. **Keep `always()` in condition** to upload even on test failure (when opted in)

### Behavior

| Trigger | UPLOAD_ARTIFACTS | Artifact Uploaded? |
|---------|------------------|-------------------|
| Push event | N/A | No |
| Manual run | false (default) | No |
| Manual run | true | Yes |

### Why This Matters

1. **Storage quota** - GitHub free/team plans have limited artifact storage
2. **Cost** - Excess storage incurs charges on paid plans
3. **Noise** - Most builds don't need artifacts preserved
4. **Intentional access** - When you need artifacts, explicitly request them

### Verification

```bash
# Check if artifact upload is conditional on workflow_dispatch
grep -A 2 "upload-artifact" .github/workflows/ci-cd.yml | grep -q "workflow_dispatch" || echo "WARNING: Artifact upload not restricted to manual runs!"

# Check for UPLOAD_ARTIFACTS input
grep -q "UPLOAD_ARTIFACTS" .github/workflows/ci-cd.yml || echo "WARNING: Missing UPLOAD_ARTIFACTS workflow input!"
```

### When to Upload Artifacts

Only opt-in to artifact uploads when:
- Debugging a failing test that needs detailed results
- Collecting coverage reports for external tools
- Archiving build outputs for compliance/audit
- Sharing test results across jobs in the same workflow

---

## 23. Helm Chart Update Job Pattern

**Root Cause ID:** HELM-001
**Severity:** HIGH
**Symptom:** Helm chart not updated, wrong packaging flow, push to Eregistrations-Helm fails, or dependency resolution fails

### Problem

The helm-chart-update job has specific requirements that differ from other jobs:
1. Uses `[self-hosted, linux, build]` runner (not `build, normal`)
2. Uses HTTPS with `GHCR_TOKEN` for authentication (not SSH)
3. Requires `azure/setup-helm@v4` to install Helm CLI
4. Requires `helm dependency update` before lint/package (charts may have dependencies)
5. Clones `UNCTAD-eRegistrations/Eregistrations-Helm` from GitHub (not Bitbucket)
6. Needs idempotency check and push retry with merge conflict resolution

### Required Pattern

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
          CHART_NAME: <chart-name>
        run: |
          cd helm
          helm repo add eregistrations-helm https://raw.githubusercontent.com/UNCTAD-eRegistrations/Eregistrations-Helm/master --username x-access-token --password ${{ secrets.GHCR_TOKEN }}
          helm dependency update .
          helm lint .
          helm template . > /dev/null
          helm package ./

      - name: Update Helm chart repository
        env:
          CHART_NAME: <chart-name>
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

### Key Rules

1. **Runner is `[self-hosted, linux, build]`** -- NOT `[self-hosted, linux, build, normal]`
2. **Uses `azure/setup-helm@v4`** to install Helm CLI (self-hosted runners may not have it pre-installed)
3. **Uses `GHCR_TOKEN`** for both `helm repo add` authentication and HTTPS git clone (NOT SSH)
4. **`helm repo add` before dependency update** -- adds the Eregistrations-Helm repo so chart dependencies resolve
5. **`helm dependency update .`** runs before lint/package (handles subchart dependencies)
6. **Clone via HTTPS** -- `https://x-access-token:${{ secrets.GHCR_TOKEN }}@github.com/...` (NOT `git@github.com:...`)
7. **Git user config required** before commit operations
8. **`git rm`** removes old chart tgz files from git tracking (clean history)
9. **Idempotency check** -- `git diff --cached --quiet` skips commit when chart is unchanged
10. **Push retry (5 attempts)** with index.yaml merge conflict resolution via regeneration
11. **Commit message format** -- `helm: update $CHART_NAME chart with $TGZ_FILE`
12. **Clone into `umbrella-repo/`** subdirectory (not `eregistrations-helm/`)

### SHOULD_HELM Detection in set-build-variables

The `set-build-variables` job must detect helm commits and set the SHOULD_HELM flag:

```yaml
# Check if this is a helm commit
SHOULD_HELM="false"
if [[ "$SUBJECT" == helm* ]]; then
  SHOULD_HELM="true"
fi
echo "SHOULD_HELM=${SHOULD_HELM}" >> $GITHUB_OUTPUT
```

When `SHOULD_HELM` is true, `SHOULD_BUILD` should be false (helm commits skip Docker builds).

### Helm Repo Index URL

The `helm repo index` URL must use the GitHub raw content URL:
```
https://raw.githubusercontent.com/UNCTAD-eRegistrations/Eregistrations-Helm/master
```

This replaces the old Bitbucket API URL:
```
https://api.bitbucket.org/2.0/repositories/unctad/eregistrations-helm/src/master/
```

### Required Secret

| Secret | Purpose |
|--------|---------|
| `GHCR_TOKEN` | GitHub Personal Access Token with repo access, used for helm repo authentication and Eregistrations-Helm clone |

### Verification

```bash
# Check helm job exists
grep -q "helm-chart-update:" .github/workflows/ci-cd.yml || echo "MISSING: helm-chart-update job!"

# Check runner label
grep -A 2 "helm-chart-update:" .github/workflows/ci-cd.yml | grep -q "\[self-hosted, linux, build\]" || echo "WARNING: Wrong runner for helm job!"

# Check uses GHCR_TOKEN (not SSH)
grep -A 30 "helm-chart-update:" .github/workflows/ci-cd.yml | grep -q "GHCR_TOKEN" || echo "WARNING: Missing GHCR_TOKEN in helm job!"

# Check setup-helm action
grep -q "azure/setup-helm" .github/workflows/ci-cd.yml || echo "WARNING: Missing setup-helm action!"

# Check SHOULD_HELM output
grep -q "SHOULD_HELM" .github/workflows/ci-cd.yml || echo "MISSING: SHOULD_HELM flag!"

# Check notify-failure includes helm-chart-update
grep -A 2 "notify-failure:" .github/workflows/ci-cd.yml | grep -q "helm-chart-update" || echo "WARNING: notify-failure missing helm-chart-update dependency!"
```

### Reference Implementation

See: [`UNCTAD-eRegistrations/ActiveMQ` — `.github/workflows/ci-cd.yml`](https://github.com/UNCTAD-eRegistrations/ActiveMQ/blob/develop/.github/workflows/ci-cd.yml)
