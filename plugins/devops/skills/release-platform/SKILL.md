---
name: release-platform
description: >
  Cut a new platform release across all 27 eRegistrations repositories. Creates
  `release/<version>` branches from `develop`, pushes them, and bumps the minor
  version on `develop` in every repo. Supports `--dry-run` to preview without
  mutating, and an optional repo filter to operate on a subset.
  Usage - /release-platform [version] [--dry-run] [repo1 repo2 ...]
license: UNCTAD-Internal
compatibility: Requires Node.js + npm (for the global `standard-version` + `xml-js` install), git, an authenticated `gh` CLI for GitHub HTTPS clones, and SSH keys configured for `bitbucket.org` for the seven `mule3-*` and `formio-server` repos. Run from any working directory — the skill creates and cleans up its own `release/` scratch directory.
allowed-tools: Read, Write, Edit, Bash(git *), Bash(npm *), Bash(node *), Bash(standard-version *), Bash(mkdir *), Bash(chmod *), Bash(rm *), Bash(bash *), Bash(grep *), Bash(basename *), Bash(export *), Bash(test *), TodoWrite, AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-04-30"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[version] [--dry-run] [repo1 repo2 ...]"
---

# Release eRegistrations Platform

You are performing a release of the eRegistrations platform across all repositories. This involves:
1. Creating a `release/<version>` branch from `develop` in every repo
2. Pushing the release branch
3. Bumping the minor version on `develop`

## Dry-Run Mode

If the user passes `--dry-run` (e.g., `/release-platform --dry-run` or `/release-platform 2.18 --dry-run`), run in **dry-run mode**. In this mode:
- Repos ARE sparse-cloned (read-only, needed to inspect files)
- NO branches are created
- NO commits are made
- NO pushes are performed
- `standard-version` is run with `--dry-run` flag
- Instead, for every repo the skill reports exactly what WOULD happen:
  - Current version in `package.json` (and `pom.xml` if present)
  - The release branch name that would be created
  - The version bump that `standard-version --dry-run` reports
  - Whether `.versionrc.js` is present (and its configuration)
  - Whether `pom.xml` is present

Set the `DRY_RUN` environment variable to `"true"` when invoking the process script in dry-run mode.

## Repo Filter Mode

If the user specifies one or more repository names after the version/flags, only process those repos instead of all 27. Repository names are matched case-insensitively against the repo display names listed in STEP 3.

Examples:
- `/release-platform 2.18 --dry-run mule3-lesotho Statistics-Frontend` — dry-run only those 2 repos
- `/release-platform mule3 Camunda` — release only mule3 and Camunda
- `/release-platform 2.18` — release all repos (no filter)

## STEP 0: Determine Release Version, Mode, and Repo Filter

Parse the arguments to extract:
- **Version** (optional): a version number like `2.18` (matches pattern `N.N` or `N.NN`)
- **Dry-run flag**: `--dry-run` if present
- **Repo filter** (optional): any remaining arguments that are not a version or `--dry-run` are treated as repository names to filter on

The user may provide a version as an argument (e.g., `/release-platform 2.18`).

**If a version is provided:** use it directly.

**If no version is provided:** detect the latest version by checking existing release branches in a few key repos:
```bash
git ls-remote --heads https://github.com/UNCTAD-eRegistrations/BPA-backend.git 'refs/heads/release/*' | sed 's|.*refs/heads/release/||' | sort -t. -k1,1n -k2,2n | tail -1
```
Then increment the minor version (e.g., `2.17` -> `2.18`).

Confirm the version with the user before proceeding: "About to release version **2.XX** across all repositories. Continue?"

## STEP 1: Prepare the release directory and install standard-version

```bash
mkdir -p release
npm install -g standard-version xml-js
export NODE_PATH="$(npm prefix -g)/lib/node_modules"
```

All repos will be sparse-cloned into subdirectories under `release/`. `standard-version` and `xml-js` (needed by `.versionrc.js` in repos that also bump `pom.xml`) are installed globally once so individual repos don't need `npm install`. `NODE_PATH` must be exported so that `.versionrc.js` files can `require('xml-js')` from the global modules.

## STEP 2: Create the processing script

Create a temporary bash script at `release/process-repo.sh` that handles a single repository. The script accepts these arguments:
- `$1` - repo display name (used for the directory name and logging)
- `$2` - git clone URL
- `$3` - release version (e.g., `2.18`)
- `$4` - sparse checkout paths (space-separated, passed as a single quoted string)
- `$5` - (optional) if set to `monorepo`, handle subdirectory version bumps

The script reads the `DRY_RUN` environment variable. If `DRY_RUN=true`, it skips all mutating git operations and runs the repo's own `minor-release` npm script with `--dry-run` appended.

```bash
#!/bin/bash
set -e

REPO_NAME="$1"
CLONE_URL="$2"
VERSION="$3"
SPARSE_PATHS="$4"
MONOREPO="$5"
DRY_RUN="${DRY_RUN:-false}"
LOG_FILE="release/${REPO_NAME}.log"

exec > "$LOG_FILE" 2>&1

if [ "$DRY_RUN" = "true" ]; then
  echo "=== [$REPO_NAME] DRY RUN - release $VERSION ==="
else
  echo "=== [$REPO_NAME] Starting release $VERSION ==="
fi

# --- Sparse clone develop branch (depth 1, only needed files) ---
git clone --depth 1 --filter=blob:none --sparse --branch develop "$CLONE_URL" "release/$REPO_NAME"
cd "release/$REPO_NAME"
git sparse-checkout set --no-cone $SPARSE_PATHS

echo "[$REPO_NAME] Cloned and sparse checkout done"

# --- Report current state ---
echo "[$REPO_NAME] Current package.json version: $(node -p "require('./package.json').version" 2>/dev/null || echo 'N/A (root)')"
[ -f pom.xml ] && echo "[$REPO_NAME] pom.xml: PRESENT" || echo "[$REPO_NAME] pom.xml: not found"
[ -f .versionrc.js ] && echo "[$REPO_NAME] .versionrc.js: PRESENT" || echo "[$REPO_NAME] .versionrc.js: not found"
if [ "$MONOREPO" = "monorepo" ]; then
  for subdir in backend frontend; do
    if [ -f "$subdir/package.json" ]; then
      echo "[$REPO_NAME] $subdir/package.json version: $(node -p "require('./$subdir/package.json').version" 2>/dev/null || echo 'N/A')"
      [ -f "$subdir/pom.xml" ] && echo "[$REPO_NAME] $subdir/pom.xml: PRESENT" || echo "[$REPO_NAME] $subdir/pom.xml: not found"
      [ -f "$subdir/.versionrc.js" ] && echo "[$REPO_NAME] $subdir/.versionrc.js: PRESENT" || echo "[$REPO_NAME] $subdir/.versionrc.js: not found"
    fi
  done
fi

if [ "$DRY_RUN" = "true" ]; then
  # --- Dry run: report what would happen, no mutations ---
  echo "[$REPO_NAME] WOULD create branch: release/$VERSION"
  echo "[$REPO_NAME] WOULD push branch: release/$VERSION to origin"

  # Show the full minor-release script for reference, then run
  # standard-version directly with --dry-run to preview the version bump.
  run_minor_release_dry() {
    local dir="$1"
    local full_script
    full_script=$(node -p "require('./package.json').scripts['minor-release'] || 'NOT FOUND'" 2>/dev/null)
    echo "[$REPO_NAME] ${dir:+$dir/}minor-release script: $full_script"
    if [ "$full_script" = "NOT FOUND" ]; then
      echo "[$REPO_NAME] ${dir:+$dir/}No minor-release script, falling back to standard-version directly"
    fi
    standard-version --release-as minor --skip.changelog=true --skip.tag=true --dry-run 2>&1 || true
  }

  if [ "$MONOREPO" = "monorepo" ]; then
    for subdir in backend frontend; do
      if [ -f "$subdir/package.json" ]; then
        echo "[$REPO_NAME] --- dry-run minor-release in $subdir/ ---"
        cd "$subdir"
        run_minor_release_dry "$subdir"
        cd ..
      fi
    done
  else
    run_minor_release_dry ""
  fi

  echo "[$REPO_NAME] WOULD commit and push version bump on develop"
  echo "=== [$REPO_NAME] DRY RUN COMPLETE ==="
else
  # --- Live mode: create branch, bump, push ---

  # Create and push release branch
  git checkout -b "release/$VERSION"
  git push -u origin "release/$VERSION"
  echo "[$REPO_NAME] Release branch release/$VERSION created and pushed"

  # Switch back to develop for version bump
  git checkout develop

  # Run minor-release (standard-version is installed globally)
  # If minor-release script exists, use it; otherwise fall back to standard-version directly
  run_minor_release() {
    local dir="$1"
    local has_script
    has_script=$(node -p "require('./package.json').scripts['minor-release'] ? 'yes' : 'no'" 2>/dev/null)
    if [ "$has_script" = "yes" ]; then
      echo "[$REPO_NAME] ${dir:+$dir/}Running npm run minor-release"
      npm run minor-release 2>&1 || true
    else
      echo "[$REPO_NAME] ${dir:+$dir/}No minor-release script, falling back to standard-version directly"
      standard-version --release-as minor --skip.changelog=true --skip.tag=true 2>&1 || true
    fi
  }

  if [ "$MONOREPO" = "monorepo" ]; then
    for subdir in backend frontend; do
      if [ -f "$subdir/package.json" ]; then
        echo "[$REPO_NAME] Bumping version in $subdir/"
        cd "$subdir"
        run_minor_release "$subdir"
        cd ..
      fi
    done
  else
    run_minor_release ""
  fi

  # Commit and push if the npm script didn't already
  if [ -n "$(git status --porcelain)" ]; then
    echo "[$REPO_NAME] Uncommitted changes detected, committing..."
    git add package.json pom.xml .versionrc.js CHANGELOG.md 2>/dev/null || true
    if [ "$MONOREPO" = "monorepo" ]; then
      git add backend/package.json backend/pom.xml backend/.versionrc.js backend/CHANGELOG.md 2>/dev/null || true
      git add frontend/package.json frontend/pom.xml frontend/.versionrc.js frontend/CHANGELOG.md 2>/dev/null || true
    fi
    git commit -m "chore(release): bump version for next development cycle" || true
  fi

  # Push develop (covers both: script pushed already = no-op, or we just committed)
  git push 2>&1 || true

  echo "=== [$REPO_NAME] DONE ==="
fi
```

Make the script executable: `chmod +x release/process-repo.sh`

## STEP 3: Run repos in parallel

Launch repositories in parallel using background bash processes. Use the process script created in step 2.

**If repo filter is specified:** only launch the repos whose names match (case-insensitive) the filter list. Only include the matching `bash "$SCRIPT" ...` lines from the full list below.

**If no repo filter:** launch ALL repos.

Set `DRY_RUN=true` if the user passed `--dry-run`, otherwise omit it (defaults to `false`):

Here is the complete repository list with their display names, clone URLs, and types. Use `&` for backgrounding and `wait` at the end:

```bash
VERSION="<detected-or-provided-version>"
SCRIPT="release/process-repo.sh"
SPARSE="package.json pom.xml .versionrc.js CHANGELOG.md"
export DRY_RUN="<true-or-false>"
export NODE_PATH="$(npm prefix -g)/lib/node_modules"

# GitHub repos (HTTPS - gh auth provides credentials)
bash "$SCRIPT" "ActiveMQ"             "https://github.com/UNCTAD-eRegistrations/ActiveMQ.git"             "$VERSION" "$SPARSE" &
bash "$SCRIPT" "BPA-backend"          "https://github.com/UNCTAD-eRegistrations/BPA-backend.git"          "$VERSION" "$SPARSE" &
bash "$SCRIPT" "BPA-frontend"         "https://github.com/UNCTAD-eRegistrations/BPA-frontend.git"         "$VERSION" "$SPARSE" &
bash "$SCRIPT" "BPA-websocket"        "https://github.com/UNCTAD-eRegistrations/BPA-websocket.git"        "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Camunda"              "https://github.com/UNCTAD-eRegistrations/Camunda.git"              "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Cashier"              "https://github.com/UNCTAD-eRegistrations/Cashier.git"              "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Chrome-URL-To-PDF"    "https://github.com/UNCTAD-eRegistrations/Chrome-URL-To-PDF.git"    "$VERSION" "$SPARSE" &
bash "$SCRIPT" "ClamAV"               "https://github.com/UNCTAD-eRegistrations/ClamAV.git"               "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Dataweave"            "https://github.com/UNCTAD-eRegistrations/Dataweave.git"            "$VERSION" "$SPARSE" &
bash "$SCRIPT" "DS-Backend"           "https://github.com/UNCTAD-eRegistrations/DS-Backend.git"           "$VERSION" "$SPARSE" &
bash "$SCRIPT" "DS-Frontend"          "https://github.com/UNCTAD-eRegistrations/DS-Frontend.git"          "$VERSION" "$SPARSE" &
bash "$SCRIPT" "GDB"                  "https://github.com/UNCTAD-eRegistrations/GDB.git"                  "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Graylog"              "https://github.com/UNCTAD-eRegistrations/Graylog.git"              "$VERSION" "$SPARSE" &
bash "$SCRIPT" "JS-Assistant"         "https://github.com/UNCTAD-eRegistrations/JS-Assistant.git"         "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Keycloak"             "https://github.com/UNCTAD-eRegistrations/Keycloak.git"             "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Publisher"            "https://github.com/UNCTAD-eRegistrations/Publisher.git"            "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Restheart"            "https://github.com/UNCTAD-eRegistrations/Restheart.git"            "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Statistics-Backend"   "https://github.com/UNCTAD-eRegistrations/Statistics-Backend.git"   "$VERSION" "$SPARSE" &
bash "$SCRIPT" "Statistics-Frontend"  "https://github.com/UNCTAD-eRegistrations/Statistics-Frontend.git"  "$VERSION" "$SPARSE" &

# GitHub monorepo (Public-Pages has backend/ and frontend/ subdirectories)
SPARSE_PP="backend/package.json backend/pom.xml backend/.versionrc.js backend/CHANGELOG.md frontend/package.json frontend/pom.xml frontend/.versionrc.js frontend/CHANGELOG.md"
bash "$SCRIPT" "Public-Pages"         "https://github.com/UNCTAD-eRegistrations/Public-Pages.git"         "$VERSION" "$SPARSE_PP" "monorepo" &

# Bitbucket repos (SSH - user has SSH keys configured)
bash "$SCRIPT" "formio-server"        "git@bitbucket.org:unctad/formio-server.git"                        "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3"                "git@bitbucket.org:unctad/mule3.git"                                "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3-bhutan"         "git@bitbucket.org:unctad/mule3-bhutan.git"                         "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3-cameroon"       "git@bitbucket.org:unctad/mule3-cameroon.git"                       "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3-colombia"       "git@bitbucket.org:unctad/mule3-colombia.git"                       "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3-els"            "git@bitbucket.org:unctad/mule3-els.git"                            "$VERSION" "$SPARSE" &
bash "$SCRIPT" "mule3-lesotho"        "git@bitbucket.org:unctad/mule3-lesotho.git"                        "$VERSION" "$SPARSE" &

wait
echo "All repos processed. Check individual logs in release/*.log"
```

## STEP 4: Report Results

After all parallel jobs complete, read each log file and produce a summary.

### Live mode

```bash
for log in release/*.log; do
  repo=$(basename "$log" .log)
  if grep -q "DONE" "$log"; then
    echo "OK  $repo"
  else
    echo "FAIL $repo"
  fi
done
```

Display results as a table:

| Repository | Release Branch | Develop Bump | Status |
|------------|---------------|--------------|--------|
| ActiveMQ | release/2.XX | bumped | OK/FAIL |
| ... | ... | ... | ... |

For any FAILED repos, show the last 20 lines of their log file so the user can diagnose the issue.

### Dry-run mode

For each repo, extract and display from the log:
- Current version in `package.json` (and `pom.xml` if present)
- Whether `.versionrc.js` is present
- The release branch that WOULD be created
- The `standard-version --dry-run` output showing the version bump

Display results as a table:

| Repository | Current Version | Has pom.xml | Has .versionrc.js | Release Branch | New Dev Version |
|------------|----------------|-------------|-------------------|----------------|-----------------|
| ActiveMQ | 2.17.0 | yes/no | yes/no | release/2.18 | 2.19.0 |
| ... | ... | ... | ... | ... | ... |

For any repos that had errors even in dry-run, show the log output.

After displaying the dry-run summary, ask the user: "This was a dry run. Would you like to proceed with the actual release?"
If the user confirms, re-run STEP 3 with `DRY_RUN=false` (no need to re-clone, the repos are already checked out).

## STEP 5: Cleanup

After reporting results (and after the user has confirmed proceeding with the actual release in case of dry-run → live transition), remove all artifacts created during execution:

```bash
rm -rf release/
```

## Important Notes

- **`standard-version` is installed globally once** in STEP 1 — do NOT run `npm install` per repo
- **Sparse checkout** ensures we only download the minimum files needed for version management
- **Parallel execution** processes all 27 repos simultaneously for speed
- If a release branch `release/<version>` already exists in a repo, `git push` will fail — the log will capture this, and it will be reported as a failure. This is expected if a partial release was already started.
- The `git clone --depth 1` ensures we only download the latest commit, not full history
