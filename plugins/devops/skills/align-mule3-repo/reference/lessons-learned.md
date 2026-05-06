# Lessons learned (mule3-burundi alignment, 2026-05-06)

This file captures non-obvious facts surfaced during the canonical run that made this skill. Future invocations should cross-check these before deviating.

## 1. The reference repo matters

`mule3-benin` and `mule3-colombia` are both already aligned, but their workflows diverge:

- **colombia** has the original `feat: migrate CI/CD from Jenkins to GitHub Actions` workflow with no later fixes.
- **benin** has TOBE-17420 propagated fixes layered on top: git-lfs install/retry, mule-common + datamapping fetch via the `unctad-dependency-propagator` GitHub App, force-fresh LFS smudge, MD5 sanity check, etc.

When scaffolding a new mule3-* repo, **prefer benin**. Colombia would also work but would carry forward already-fixed bugs.

## 2. Lockfile parity diverges between benin and colombia

After the migration, the lockfile entry for `standard-version` should be:

```
"standard-version": "file:./vendor/standard-version.tgz",
...
"node_modules/standard-version": {
  "version": "9.1.1",
  "resolved": "file:vendor/standard-version.tgz",
  ...
}
```

**Benin** has both edits applied. **Colombia** still references the original bitbucket SSH URL in the lockfile. Colombia's CI works because the vendor tarball is downloaded before `npm ci` and the resolution mismatch is tolerated for `file:` deps — but it's flaky and undesirable. Don't propagate colombia's broken state to new repos.

## 3. The propagator only knows about repos in its hardcoded matrix

`mule-common` and `mule3-datamapping-connector` both keep a hardcoded matrix in `propagate-version`. As of 2026-05-06 the matrix in each is just:

```
- mule3-benin
- mule3-colombia
```

(plus `Dataweave` in mule-common). Every other consumer is commented out as "Only repos already on GitHub. Add others as they migrate from Bitbucket".

Implication: a freshly imported mule3-* repo's pom is *frozen* at whatever version it was forked at, and the packages-branch retention policy will eventually evict that version, breaking CI. **Phase 4 is mandatory**, not optional. Don't ship a new mule3-* repo without opening both PRs.

## 4. Branch defaults

Other mule3-* repos use `develop` as the default. A freshly created GitHub repo defaults to `main`. The CI workflow's `on: push: branches: [...]` list does NOT include `main` — so without Phase 3.1 the very first push to develop won't fire CI for an obvious reason but a push to `main` would also not fire. Always check `gh repo view --json defaultBranchRef`.

## 5. Don't push `master` autonomously

It was tempting to push `master` from current `develop` HEAD as part of the alignment. **Don't.** `master` is the live-release branch, and pushing a placeholder commit to it would:
- Trigger the workflow's `master` branch case, which sets `TAG_NAME=$VERSION` and `ENV=live`
- Tag the version on docker hub as the production tag
- Possibly trigger the deploy job

The correct first commit on `master` is the first live release, cut from a `release/*` branch. Surface this as a deferred decision in the final report.

## 6. Sourceless backend repos make pom bumps mechanical

mule3-* repos are mostly XML flows + properties + servicelist.json + at most one Java file (`JMXMetric.java`) that has no mule-common imports. So a `mule-common 1.25.0 → 1.37.5` jump is safe to apply without source-code changes.

If a future mule3-* repo grows actual Java code that imports mule-common APIs, this assumption breaks. Print a warning when `find src/main/java -name '*.java' -exec grep -l 'mule_common\|mule\.common' {} +` returns anything.

## 7. The `v4-development` cascade

Granting `v4-development` push on the new repo flips ~3 specific developers from `read` to `write` automatically. Don't grant write to those users individually as direct collaborators — that creates a maintenance footgun.

The team slug is `v4-development`, not `v4-developers`. The 404 from a wrong slug is silent if you `2>/dev/null`.

## 8. Delete-protection ruleset includes `main` even when the repo doesn't

Both benin and colombia keep `refs/heads/main` in the delete-protection ruleset's include list even though they don't use `main` as the default. It costs nothing and protects an accidentally re-created `main` from being deleted. Mirror this exactly.

## 9. CI auto-bumps version on the first push

The first push to develop fires the workflow, the `feat:` commit triggers the `bump-version` job (because the commit isn't `chore` or `revert`), and `standard-version` patch-bumps the version and pushes a `chore(release): X.Y.Z` commit back. So the local `develop` will be one commit behind the remote after the first push — pull it down before doing anything else.

## 10. PR body `Test plan` checklist is load-bearing

Org PR template expects a `## Test plan` section with at least one bulleted item. PRs without it fail a Danger-style check. Always include the "Next mule-common master push opens a propagator PR…" line.
