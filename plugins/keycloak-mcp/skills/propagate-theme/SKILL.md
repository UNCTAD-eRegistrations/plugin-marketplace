---
name: propagate-theme
description: >
  Propagate an existing Keycloak theme directory (`themes/<name>/`) from a source branch (default
  `develop`) to one or more target branches in the eRegistrations Keycloak repo
  (https://github.com/UNCTAD-eRegistrations/Keycloak). Uses `git checkout <src> -- themes/<name>/`
  to copy the theme files into each target branch and commits the result locally — does NOT push.
  TRIGGER when: the user asks to "propagate", "port", "bring", "copy", or "sync" a Keycloak theme
  from one branch to others (e.g. "propagate the tanzania theme to release/2026 and staging",
  "bring rwanda theme into the cuba-prod branch", "sync all themes from develop to main").
  DO NOT TRIGGER when: scaffolding a NEW theme that doesn't exist yet (use `create-theme`); merging
  branches in general (just `git merge`); editing a theme on a single branch (just edit and commit).
license: UNCTAD-Internal
compatibility: Pure git operations — does not require an active Keycloak MCP connection.
allowed-tools: Read, Bash(git *), Bash(test *), Bash(ls *)
metadata:
  version: "1.0.1"
  version-date: "2026-04-28"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<theme-name> [--from <src-branch>] [--to <target-branches>]"
  disable-model-invocation: "false"
  changelog:
    - "1.0.1 (2026-04-28): Pressure-test refinements — (1) made it explicit to capture the original branch in a `$ORIGINAL` variable before any checkout, (2) clarified that fetch/pull failures should be tolerated when no `origin` remote is configured (not just when there's no upstream for the branch). All four pressure tests (clean run, dirty tree, missing target, missing source) passed before this revision; these are documentation-only tightenings of nuances the test agents had to infer."
    - "1.0.0 (2026-04-28): Initial — propagates `themes/<name>/` from a source branch (default `develop`) to one or more target branches. Verifies repo + source theme, switches branches safely (refuses with uncommitted changes), copies files via `git checkout <src> -- themes/<name>/`, commits per-target. Does NOT push — leaves that to the user."
---

# Propagate Keycloak Theme

Bring an existing theme directory (`themes/<name>/`) from a source branch into one or more target branches in the eRegistrations Keycloak repo.

**Canonical repo:** https://github.com/UNCTAD-eRegistrations/Keycloak
**Default source branch:** `develop`

## When to Use

- A theme was added or updated on `develop` (e.g. via `/keycloak-mcp:create-theme`) and now needs to land on other branches — release branches, country-specific deployment branches, `main`, etc.
- The user names a list of target branches and (optionally) a source branch.

**Don't use this for:**

- **New themes that don't exist anywhere yet** — use `create-theme` instead.
- **General branch merges** — this skill copies *only* `themes/<name>/`, nothing else. If you need to merge full branches, use `git merge` directly.
- **Pushing** — this skill commits locally per branch. The user pushes when they're ready.

## Arguments

| Position | Name | Required | Default | Notes |
|---|---|---|---|---|
| 1 | `<theme-name>` | yes | — | Lowercase directory name under `themes/`, e.g. `tanzania`. Must already exist on the source branch. |
| 2 | `--from <src-branch>` | no | `develop` | Branch to copy the theme files **from**. |
| 3 | `--to <target-branches>` | yes | — | Comma-separated branch names to copy the theme **to**, e.g. `main,release/2026,cuba-prod`. |

If `--to` is not given, ask the user. Don't guess — propagating to the wrong branch is hard to undo.

## Verify the environment

### 1. Are we in the Keycloak repo?

```bash
test -d themes/unctad-next && echo IN_REPO || echo "NOT_IN_KEYCLOAK_REPO"
```

If not, point the user at https://github.com/UNCTAD-eRegistrations/Keycloak and offer to clone (same as `create-theme`):

```bash
git clone https://github.com/UNCTAD-eRegistrations/Keycloak.git
cd Keycloak
```

### 2. Does the source branch exist + contain the theme?

```bash
git fetch origin <src-branch> 2>/dev/null || true
git rev-parse --verify <src-branch> >/dev/null  # branch exists locally?
git show <src-branch>:themes/<theme-name>/login/theme.properties >/dev/null  # theme exists there?
```

- If the branch doesn't exist locally, try `git rev-parse --verify origin/<src-branch>`. If it exists on origin, `git fetch origin <src-branch>:<src-branch>` to bring it in.
- If the theme isn't on the source branch → stop. Show `git ls-tree <src-branch> themes/` so the user can pick the right name.

### 3. Do all target branches exist?

For each target branch, verify it exists (locally or on origin) before doing any work — fail fast:

```bash
for b in <target-branches>; do
  git rev-parse --verify "$b" 2>/dev/null \
    || git rev-parse --verify "origin/$b" 2>/dev/null \
    || { echo "MISSING_BRANCH: $b"; exit 1; }
done
```

If any target is missing, stop and ask the user — don't silently skip and don't auto-create new branches.

### 4. No uncommitted changes

```bash
git status --porcelain
```

If the working tree is dirty, stop and show `git status`. Ask the user to commit or stash first. Don't auto-stash without permission.

### 5. Remember the starting branch

Before any `git checkout`, capture the current branch so we can return to it at the end:

```bash
ORIGINAL=$(git rev-parse --abbrev-ref HEAD)
```

### 6. About `origin` and pull failures

If `git remote -v` is empty (no `origin` configured), every `git fetch origin ...` and `git pull --ff-only origin ...` step below will hard-fail. **That's expected** for self-hosted / offline scenarios — tolerate the failure and continue with purely local branches. The recipes below use `|| true` (or equivalent) where appropriate; do not treat a missing remote as a stop condition. (A diverged-history failure on `git pull --ff-only` against an existing remote is different — that one IS a stop condition for the affected target.)

## Steps

For each target branch in the `--to` list:

### 1. Switch to the target branch

```bash
git checkout <target-branch>
git pull --ff-only origin <target-branch> 2>/dev/null || true
```

The `|| true` covers the no-`origin` and no-upstream cases. **However**, if `origin` *is* configured and the pull fails because of diverged history (non-fast-forward), that's a real problem — **stop for that target** and ask the user. Don't force-pull. Continue with the remaining targets only after the user decides. (To distinguish: re-run without `2>/dev/null || true` if the first attempt swallowed an error you weren't expecting.)

### 2. Copy the theme files from the source

```bash
git checkout <src-branch> -- themes/<theme-name>/
```

This stages the source theme's files into the target branch's index + working tree. If the target branch already has the theme, the differences are staged.

### 3. Stage + check for actual changes

```bash
git add themes/<theme-name>/
git diff --cached --quiet  # exit 0 = no changes; exit 1 = changes staged
```

- **No changes** (target already matches source): skip the commit. Tell the user `<target-branch>` is already up-to-date and move on to the next target.
- **Changes**: commit:

  ```bash
  git commit -m "feat(themes): propagate <theme-name> from <src-branch>"
  ```

  Use a single-line, conventional-commit-style message. Don't squash multiple themes into one commit if propagating several — run the skill once per theme.

### 4. Move on to the next target

After the commit (or skip), loop to the next target branch. Do NOT push.

## After all targets

1. Switch back to the user's original branch (the `$ORIGINAL` captured in step 5 above): `git checkout "$ORIGINAL"`.
2. Print a summary table: target branch | result (committed `<sha>` / already up-to-date / skipped because of error).
3. Remind the user:
   - Review the new commits on each branch (`git log <branch> -1 --stat`).
   - Push each branch when ready: `git push origin <branch>`.
   - If any branch has CI/CD that auto-deploys, **mention it explicitly** so the user pushes deliberately.

## Connecting to Keycloak

This skill **does not** call any `mcp__Keycloak__*` tool — it only manipulates git history. The Keycloak server only sees a new theme after the relevant branch is pushed, the Docker image is rebuilt, and a pod restart picks up the new theme directory.

## Common Mistakes

- **Auto-stashing without permission.** If the working tree is dirty, stop and ask. Don't run `git stash` automatically — silently stashed work is hard to find.
- **Force-pulling on the target branch.** If `git pull --ff-only` fails, stop. The user's branches may have history that should be preserved.
- **Pushing automatically.** Never push from this skill. The user reviews and pushes manually.
- **Copying more than the theme directory.** `git checkout <src> -- themes/<name>/` is scoped to that path — never broaden the path argument. If a theme depends on changes outside `themes/<name>/` (e.g. a parent theme update in `themes/unctad-next/`), surface that to the user; this skill won't pull in those side-changes.
- **Squashing multiple themes into one commit.** If propagating several themes, run the skill once per theme so each lands as a separate, reverter-friendly commit.
- **Skipping the source-existence check.** If `themes/<name>/` doesn't exist on `<src-branch>`, the `git checkout` would silently delete it from the target. Always verify first.

## Examples

```
/keycloak-mcp:propagate-theme tanzania --to main
/keycloak-mcp:propagate-theme rwanda --from develop --to release/2026,cuba-prod
/keycloak-mcp:propagate-theme jamaica --to staging,production
```
