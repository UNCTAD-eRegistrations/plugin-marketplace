# Troubleshooting & Recovery Guide

This document contains rollback procedures and recovery steps for common migration issues.

---

## ⚠️ CRITICAL: Pre-Flight Checklist Enforcement

**READ THIS FIRST** - Most migration failures stem from skipping mandatory steps.

### Before Generating ANY ci-cd.yml

You MUST run these commands and document their output:

```bash
# 1. Extract ALL Jenkinsfile stages
grep -E "stage\s*\(" Jenkinsfile | sed "s/.*stage('\([^']*\)').*/\1/"

# 2. Extract ALL git clone operations (CRITICAL - missing these breaks builds)
grep "git clone" Jenkinsfile

# 3. Extract ALL shell commands
grep -E "sh\s+['\"]" Jenkinsfile | head -30
```

### Feature Parity Table Required

Create and verify this table BEFORE generating any workflow:

| Jenkinsfile Stage | GitHub Actions Job | Status |
|-------------------|-------------------|--------|
| [stage name] | [job name] | ✅/❌ |

**BLOCKING: Do NOT proceed until ALL items show ✅**

### Required TodoWrite Checklist

Initialize with EXACTLY these 13 items (matches SKILL.md Progress Tracking table):
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

If migration fails, see SKILL.md Phase 6 (Rollback Procedure).

### Post-Generation Verification

Run these after EVERY ci-cd.yml generation:

```bash
# GitHub Actions workflow validation (actionlint must be on PATH;
# install: go install github.com/rhysd/actionlint/cmd/actionlint@latest)
actionlint .github/workflows/ci-cd.yml

# Required sections check
grep -q "permissions:" .github/workflows/ci-cd.yml && echo "✅ permissions" || echo "❌ MISSING: permissions"
grep -q "contents: write" .github/workflows/ci-cd.yml && echo "✅ contents: write" || echo "❌ MISSING: contents: write"

# Runner labels check
grep "runs-on:" .github/workflows/ci-cd.yml | sort | uniq -c
```

### Reference: Correct Patterns

Always copy these patterns EXACTLY from critical-patterns.md:

**Git Config:**
```yaml
git config --global user.email "github-actions[bot]@users.noreply.github.com"
git config --global user.name "GitHub Actions Bot"
```

**Version Bump (use EXACT loop structure):**
```bash
for i in $(seq 0 $((MAX_RETRIES - 1))); do
  # ... see critical-patterns.md for full pattern
done
```

See also: `reference/lessons-learned.md` for detailed failure analysis.

---

## Table of Contents

1. [Phase 2 Recovery: Git Push Failure](#phase-2-recovery-git-push-failure)
2. [Phase 3 Recovery: CI/CD Conversion Errors](#phase-3-recovery-cicd-conversion-errors)
3. [Phase 4 Recovery: File Update Rollback](#phase-4-recovery-file-update-rollback)
4. [General: Abort and Restart Migration](#general-abort-and-restart-migration)
5. [Post-Migration Issues](#post-migration-issues)

---

## Phase 2 Recovery: Git Push Failure

### Symptom
- `git push github` fails with authentication error
- Partial branches pushed
- Tags not pushed

### Recovery Steps

#### 1. SSH Authentication Failure

```bash
# Test SSH connection
ssh -T git@github.com

# If fails, check SSH key
ssh-add -l

# Add SSH key if needed
ssh-add ~/.ssh/id_rsa
```

#### 2. Partial Branch Push

```bash
# Check what was pushed
git ls-remote --heads github

# Compare with origin
git branch -a | grep origin

# Re-push remaining branches
git push github 'refs/remotes/origin/*:refs/heads/*' --force

# Note: --force is safe here as we're pushing TO github, not modifying origin
```

#### 3. Tags Not Pushed

```bash
# Check what tags exist on github
git ls-remote --tags github

# Push all tags again
git push github --tags
```

#### 4. Complete Rollback

If you need to start over:

```bash
# Remove github remote and start fresh
git remote remove github

# Then re-add and retry
git remote add github <TARGET_GITHUB_URL>
```

---

## Phase 3 Recovery: CI/CD Conversion Errors

### Symptom
- Generated workflow has YAML syntax errors
- Missing required sections
- Workflow runs but fails immediately

### Recovery Steps

#### 1. GitHub Actions Workflow Validation

```bash
# Use actionlint (assumed on PATH; install:
# go install github.com/rhysd/actionlint/cmd/actionlint@latest)
actionlint .github/workflows/ci-cd.yml
```

#### 2. Alternative Validation Methods

```bash
# If actionlint unavailable, use yamllint
pip install yamllint
yamllint .github/workflows/ci-cd.yml

# Or basic Python YAML check
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"
```

#### 3. Missing Sections Checklist

Verify these required sections exist:

```bash
# Check for permissions block
grep -q "permissions:" .github/workflows/ci-cd.yml || echo "MISSING: permissions"

# Check for jobs section
grep -q "^jobs:" .github/workflows/ci-cd.yml || echo "MISSING: jobs"

# Check for on: triggers
grep -q "^on:" .github/workflows/ci-cd.yml || echo "MISSING: on triggers"
```

#### 4. Revert to Previous Workflow

If you had an existing workflow before conversion:

```bash
# Check git history for old workflow
git log --oneline -- .github/workflows/

# Restore previous version
git checkout HEAD~1 -- .github/workflows/ci-cd.yml
```

#### 5. Remove and Regenerate

If the workflow is badly broken:

```bash
# Remove generated workflow
rm .github/workflows/ci-cd.yml

# Keep Jenkinsfile and re-run conversion
git checkout HEAD -- Jenkinsfile
```

---

## Phase 4 Recovery: File Update Rollback

### Symptom
- package.json has wrong GitHub URL
- helm/Chart.yaml sources incorrect
- README.md links broken

### Recovery Steps

#### 1. Single File Rollback

```bash
# Revert specific file to last commit
git checkout HEAD -- package.json

# Or to specific commit
git checkout <commit-hash> -- package.json
```

#### 2. View Changes Made

```bash
# See what was changed
git diff HEAD -- package.json

# See all changed files
git status
```

#### 3. Selective Unstage

```bash
# Unstage a file (keep changes in working directory)
git restore --staged package.json

# Then revert if needed
git checkout -- package.json
```

#### 4. Bulk Rollback (all Phase 4 changes)

```bash
# List files changed in Phase 4
git diff --name-only HEAD

# Revert all changes (careful - loses all work)
git checkout -- .

# Or reset staged changes only
git reset HEAD
```

---

## General: Abort and Restart Migration

### When to Abort
- Multiple failures across phases
- Incorrect target repository specified
- Need to reconsider migration strategy

### Full Abort Steps

#### 1. Revert All Local Changes

```bash
# Discard all uncommitted changes
git checkout -- .

# Remove any untracked files (careful!)
git clean -fd

# Remove untracked .github directory if created
rm -rf .github/workflows/
```

#### 2. Remove GitHub Remote

```bash
# Remove github remote
git remote remove github

# Verify remotes
git remote -v
```

#### 3. Undo Remote Rename (if done)

```bash
# If origin was renamed to bitbucket
git remote rename bitbucket origin

# Reset checkout default
git config --unset checkout.defaultRemote
```

#### 4. Verify Clean State

```bash
# Should show only origin pointing to Bitbucket
git remote -v

# Should show clean working directory
git status

# Should be on expected branch
git branch --show-current
```

#### 5. Restart Migration

After cleanup, you can start the migration skill again:
- `/bitbucket-jenkins-to-github-actions`

---

## Post-Migration Issues

### Issue: Process completed with exit code 127 in version-reading step

**Symptom:** A workflow step that runs `node -p "require('./package.json').version"` fails with `Process completed with exit code 127` (command not found). Most commonly hits the docker-build job when it tries to read the version on `[self-hosted, linux, build, heavy]`.

**Cause:** The `[self-hosted, linux, build, heavy]` runner image does NOT have `node` pre-installed. `[self-hosted, linux, build, normal]` does.

**Fix (preferred):** Stop reading the version on the heavy runner. Consume it from upstream job outputs instead:

```yaml
# In the build-docker-image job (heavy runner):
- name: Recalculate tags after version bump
  id: recalc
  env:
    VERSION_FALLBACK: ${{ needs.set-build-variables.outputs.VERSION }}
    VERSION_BUMPED: ${{ needs.bump-version.outputs.NEW_VERSION }}
  run: |
    VERSION="${VERSION_BUMPED:-$VERSION_FALLBACK}"
    # ... case statement on BRANCH_NAME for TAG_NAME / MINOR_TAG / ENV
    echo "VERSION=$VERSION" >> $GITHUB_OUTPUT
```

This also closes structural gap A from the mule3-benin migration incident (see [`lessons-learned.md`](lessons-learned.md) "Critical Failure #9").

**Fix (fallback, if heavy-runner node is genuinely needed):** Add an explicit setup-node step:

```yaml
- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version: "20"
```

But prefer the upstream-output approach — it eliminates the dependency entirely.

See [`critical-patterns.md`](critical-patterns.md) §29 ("actions/setup-node@v4 Is Mandatory").

### Issue: Version Bump Succeeds but Commit Not Visible

**Cause:** Missing `permissions: contents: write`

**Fix:**
```yaml
# Add at top level of workflow
permissions:
  contents: write
```

### Issue: Docker Build Uses Old Version

**Cause:** Using `git fetch + reset` instead of `git pull`

**Fix:** Replace:
```yaml
# WRONG
git fetch origin ${{ github.ref_name }}
git reset --hard origin/${{ github.ref_name }}

# CORRECT
git pull origin ${{ github.ref_name }}
```

### Issue: Branch Not Triggering Workflow

**Cause:** Branch not in workflow triggers

**Fix:**
```yaml
on:
  push:
    branches:
      - master
      - develop
      - beta
      - release-candidate
      - release/**     # Add missing branch patterns
      - feature/**
```

### Issue: Jenkins Deploy Not Triggering

**Cause:** Missing Jenkins trigger job or wrong runner labels

**Fix:**
1. Verify `trigger-jenkins-deploy` job exists
2. Verify runner labels: `runs-on: [self-hosted, linux, jenkins]`
3. Verify secrets configured: `JENKINS_URL`, `JENKINS_USER`, `JENKINS_API_TOKEN`

### Issue: Self-Hosted Runner Not Found

**Cause:** Runner labels don't match any registered runners

**Fix:**
```bash
# Check required labels in workflow
grep "runs-on:" .github/workflows/ci-cd.yml

# Verify runners in GitHub Settings > Actions > Runners
# Labels must match exactly
```

### Issue: Secrets Not Available

**Cause:** Secrets not configured in GitHub repository

**Required Secrets Checklist:**
- [ ] `SSH_PRIVATE_KEY` - For git operations
- [ ] `DOCKERHUB_USERNAME` - Docker Hub login
- [ ] `DOCKERHUB_TOKEN` - Docker Hub password/token
- [ ] `JENKINS_URL` - Jenkins server URL (if using Jenkins)
- [ ] `JENKINS_USER` - Jenkins username (if using Jenkins)
- [ ] `JENKINS_API_TOKEN` - Jenkins API token (if using Jenkins)
- [ ] `SLACK_WEBHOOK_URL` - Slack notifications

**Configuration Path:** Repository > Settings > Secrets and variables > Actions

---

## Emergency Contacts

If you encounter issues not covered here:

1. Check GitHub Actions documentation: https://docs.github.com/en/actions
2. Review the original Jenkinsfile for expected behavior
3. Compare with working migrations (BPA-Backend, camunda-boot)
4. Ask in team chat for similar migration experiences
