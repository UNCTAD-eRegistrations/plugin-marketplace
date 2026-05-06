# `align-mule3-repo` — quick checklist

A condensed, copy-pasteable checklist for the impatient. SKILL.md is the source of truth; this file is for skimming during a run.

## Pre-flight

- [ ] `gh auth status` shows a logged-in account
- [ ] `ssh -T git@github.com` succeeds
- [ ] cwd's `git remote get-url origin` is `git@github.com:UNCTAD-eRegistrations/mule3-<country>.git`
- [ ] working tree is clean (no uncommitted changes)
- [ ] reference repo (default `mule3-benin`) is cloned next to cwd and `git fetch`-ed
- [ ] (advisory) actor is a UNCTAD-eRegistrations org admin

## Discovery facts gathered

- [ ] `COUNTRY` slug from `package.json` `name`
- [ ] remote default branch (`gh repo view --json defaultBranchRef`)
- [ ] presence of `.github/workflows/ci-cd.yml`
- [ ] presence of `Jenkinsfile`
- [ ] presence of multi-stage `FROM ... as builder` in Dockerfile
- [ ] `package.json` `devDependencies.standard-version` value
- [ ] `pom.xml` `mule-common` and `datamapping` versions
- [ ] latest mule-common + datamapping versions in their packages branches
- [ ] presence of `mule3-${COUNTRY}` in `mule-common` and `mule3-datamapping-connector` consumer matrices
- [ ] presence of `delete protection` ruleset on the repo
- [ ] presence of `v4-development` team push permission

## Local repo alignment (Phase 2 — single commit at the end)

- [ ] `.github/workflows/ci-cd.yml` scaffolded from reference, country name substituted everywhere
- [ ] `Jenkinsfile` deleted
- [ ] `Dockerfile` builder stage removed
- [ ] `Dockerfile` `COPY` rewritten to `./target/mule3-${COUNTRY}-$VERSION.zip ./apps`
- [ ] `package.json` standard-version → `file:./vendor/standard-version.tgz`
- [ ] `package-lock.json` standard-version `devDependencies` entry → `file:./vendor/standard-version.tgz`
- [ ] `package-lock.json` `node_modules/standard-version.resolved` → `file:vendor/standard-version.tgz`
- [ ] `pom.xml` `mule-common` bumped to packages-branch latest (only if pom version not in packages branch)
- [ ] `pom.xml` `datamapping` bumped to packages-branch latest (only if pom version not in packages branch)
- [ ] one commit: `feat: align repo with mule3-* GH structure (CI/CD, Docker, deps) TOBE-17420`
- [ ] pushed (after Phase 3.1 if branch was renamed)

## GitHub repo settings (Phase 3)

- [ ] If default = `main`: rename local `main` → `develop`, push, set default, delete remote `main`
- [ ] `delete protection` ruleset created (target=branch, includes main/master/develop/beta/release-candidate/release/*)
- [ ] `v4-development` team granted `push`

## Propagator PRs (Phase 4)

- [ ] PR opened in `UNCTAD-eRegistrations/mule-common` adding `- mule3-${COUNTRY}` to consumer matrix (alphabetical)
- [ ] PR opened in `UNCTAD-eRegistrations/mule3-datamapping-connector` adding `- mule3-${COUNTRY}` to consumer matrix (alphabetical)

## Verification (Phase 5)

- [ ] `gh run list -L 1` shows the push triggered a run
- [ ] CI run completes green (or follow-up logged for the failure)

## Deferred (intentionally not auto-done)

- [ ] Push `master` branch — wait for first live release
- [ ] Merge propagator PRs — wait for review unless user asks
- [ ] eregistrations-helm umbrella entry — manual

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `mule-common <X> not found in packages branch` | pom version still old, Phase 2.5 didn't fire | Re-run Phase 1.6 → 2.5 |
| Reference repo name leaks through workflow | `sed` substitution missed something | Hand-fix; check `grep -n "mule3-${REFERENCE#mule3-}" .github/workflows/ci-cd.yml` returns nothing |
| `npm ci` fails on standard-version | lockfile second edit (resolved field) skipped | Apply the second lockfile edit too |
| Default branch change rejected | actor not org admin | Fall back to manual setting in repo Settings → Branches |
| Team grant 404 | wrong team slug | Confirm slug is exactly `v4-development` (not `v4-developers`) |
| Propagator PR fails CI | PR added a stray space or wrong indentation in matrix | Match the existing matrix entries' indentation exactly (6 spaces, then `- mule3-...`) |
