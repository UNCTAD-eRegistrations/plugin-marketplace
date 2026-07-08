---
name: ship-formio-fork-to-ds-frontend
description: >-
  Deliver a change in a UNCTAD eRegistrations formio fork all the way to a deployed instance.
  Use whenever a fix/feature has been (or needs to be) merged in one of the formio forks —
  formiojs (formiojs-4.x-src → formiojs-4.x), @formio/angular, formio-signature, formio-dropdown,
  formio-leaflet-map, formio-nested-html-element — and must actually reach users. Covers the full
  chain: source PR → (formiojs only) transpile-and-mirror into the formiojs-4.x dist repo → bump
  the git-SHA pin in ds-frontend package.json on the right release branch → CI auto-release
  (chore(release): 2.18.x image) → deploy the image → live-verify the runtime behaviour. Reach for
  this when someone says "ship/deliver/deploy the formio fix", "bump formiojs in ds-frontend",
  "why isn't my renderer change live", "release the editgrid/select/phone fix", "the PR merged but
  cuba still shows the old behaviour", or merges a formio-fork PR and asks "what's next" — even if
  they never name the pipeline. A merged source PR is NOT deployed; this skill is the missing chain.
  Scope boundary — this is the POST-MERGE delivery chain only: do NOT use it for writing/fixing the
  renderer code itself (that's the source PR + TDD), for running ds-frontend locally, for backend bugs
  (BPA-backend Java, ds-backend Python), or for unrelated instance ops (keycloak themes, camunda,
  translations sync, plain image rollbacks). It fires once a formio-fork change exists and must reach
  a deployed instance.
allowed-tools: Read, Grep, Glob, Bash(git *), Bash(gh *), Bash(npm *), Bash(ls *), Bash(grep *), Bash(head *), Bash(cp *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-07-08"
  argument-hint: "[fork] [ticket] [instance]"
---

# Ship a formio-fork change to a deployed eRegistrations instance

## Why this skill exists

In eRegistrations, the citizen/officer UI (`ds-frontend`, Angular) renders forms with **forked
formio packages**. ds-frontend does not depend on these by version — it pins each to an **immutable
git SHA** in `package.json`. So merging a PR in a fork repo changes **nothing** that users see: the
SHA still points at the old commit. The change only goes live after a deliberate **pin bump →
CI release → deploy** chain. People routinely merge a fork PR, see the instance unchanged, and
conclude "the fix doesn't work" — when in fact it was simply never delivered. This skill is that
chain, end to end, with a verification gate at every hop so you never hand off a half-delivered fix.

## First: which fork, and which pattern?

Read `references/repo-map.md` for the authoritative list of the 6 pinned forks, their source repos,
and which deploy pattern each uses. The split that drives everything:

- **Pattern A — single-repo fork** (`@formio/angular`, `formio-signature`, `formio-dropdown`,
  `formio-leaflet-map`, `formio-nested-html-element`): ds-frontend pins the **source repo itself**.
  The change ships straight from the source SHA.
- **Pattern B — split source→dist fork** (`formiojs` **only**): the source repo `formiojs-4.x-src`
  is ESM (`src/…`); ds-frontend pins a **different, pre-transpiled** repo, `formiojs-4.x`, whose
  files are babel-CJS package layout (`components/…`, not `src/…`). A source merge is invisible until
  you **transpile and mirror** it into the dist repo. Forgetting this hop is the #1 way a formiojs
  fix silently never ships.

To detect the pattern for any dep: look at the pinned URL in `ds-frontend/package.json`. If it ends
in `formiojs-4.x.git#<sha>` it is Pattern B; everything else is Pattern A. When unsure, grep the
source repo for a separate `*-4.x`/dist sibling.

## The chain (run top to bottom; each hop has a gate you must pass before the next)

Set these once: `TICKET` (e.g. `VUCE-42`), `DEP` (the package.json key, e.g. `formiojs`),
`RELEASE_BRANCH` (the current live release line — **discover it, don't assume**; see below),
`INSTANCE` (e.g. `cuba`).
Repo roots live one level up from this workspace under `~/PROJECTS/00-eRegistrations-Next/`.

**Discover the live release line (do NOT hardcode a version).** The platform advances
(`release/2.17` → `release/2.18` → `release/2.19` → …); whichever is newest-and-live is your
target. Find it, don't carry a number from memory or from this doc:
```bash
cd <ds-frontend> && git fetch origin --prune
# highest-numbered release/N.M branch on the remote = the current live line:
git branch -r --list 'origin/release/*' | sed 's#.*origin/release/##' | sort -V | tail -3
RELEASE_BRANCH="release/$(git branch -r --list 'origin/release/*' | sed 's#.*origin/release/##' | sort -V | tail -1)"
echo "$RELEASE_BRANCH"   # confirm this matches the line the instance you target actually runs
```
Every `2.18`/`2.18.x`/`:2.18` string below is an **illustrative example from the VUCE-42 era**
(≈2026-07), not a canonical value — substitute your discovered `$RELEASE_BRANCH` and its release tags.

### Hop 1 — Source PR merged
The fix lands in the fork's source repo on a `feature/<TICKET>-…` branch, reviewed, merged to the
fork's default branch. Use TDD; ship the test with the fix.
**Gate:** PR merged; the change is on the fork's default branch (`git log --oneline <default> | head`).

### Hop 2 — (Pattern B / formiojs only) Transpile-and-mirror into the dist repo
The dist repo (`formiojs-4.x`) holds the **compiled** package. Erick's established mechanism is a
*targeted* mirror — compile the changed file(s) in the source repo and copy the compiled output into
the dist repo's matching path, NOT a full rebuild (a full `gulp build` would churn hundreds of files
and the whole `dist/` bundle; the real bump commits touch only the changed component + its test).

The path mapping is **source `lib/<path>` → dist `<path>`** (the dist repo root == the source repo's
transpiled `lib/`). Concretely:
```bash
cd <formiojs-4.x-src>            # the SOURCE repo, on the merged change
npm run transpile && npm run templates    # produces lib/… (babel-CJS, same shape as the dist repo)
# in the DIST repo formiojs-4.x, on a branch feature/<TICKET>-dist:
cp <src>/lib/components/<area>/<File>.js   <dist>/components/<area>/<File>.js
# (optionally also mirror the compiled *.unit.js test, as the existing bumps do)
git -C <dist> add -A && git -C <dist> commit -m "<TICKET>: <area> <one-line>"   # then PR + merge
```
**Gate (do not skip):** the new dist commit actually contains your change —
`git -C <dist> grep "<a-symbol-from-your-diff>" <dist-sha> -- components/...` returns a hit, and the
compiled output matches the source `lib/` (same babel style: `function`, `_lodash.default`,
`_objectSpread`). Record the **dist SHA** — that is what ds-frontend will pin.

### Hop 3 — Bump the ds-frontend pin on the release branch
**Read the CURRENT pin from `origin/$RELEASE_BRANCH` after a fetch — never a local branch or checkout.**
Local clones here are routinely stale (the ds-frontend checkout often sits on `release/2.17`); reading
a stale ref shows an old SHA and will make you conclude a previously-shipped fix "was never delivered"
(it was) and bump from the wrong base. Always:
```bash
cd <ds-frontend> && git fetch origin
# current pin (authoritative) + bump history (note: `git log -S` MISSES sha→sha bumps — use -L):
git show "origin/$RELEASE_BRANCH:package.json" | grep "\"$DEP\""
git log -L '/"'"$DEP"'":/,+1:package.json' "origin/$RELEASE_BRANCH" --no-patch \
  --pretty='%h | %an | %ad | %s' --date=short | head
# SANITY: confirm the SHA you intend to replace is the branch TIP, not an ancestor you misread.
# In the dep's repo, an older SHA is an ANCESTOR of the current one:
git -C <dep-repo> merge-base --is-ancestor <SHA-you-think-is-current> <new-SHA> && echo "old precedes new — ordering OK"
```
Edit the one `package.json` line: replace the **current** SHA with the **new source SHA (Pattern A)**
or the **new dist SHA (Pattern B)**. Commit `chore(deps): <TICKET> bump <DEP> for <reason>`, push,
open the ds-frontend PR against `RELEASE_BRANCH`.
**Gate:** after merge, `git show origin/$RELEASE_BRANCH:package.json | grep "\"$DEP\""` shows the new
SHA; `npm ci` resolves it and `git grep "<symbol-from-diff>" -- node_modules/<DEP>/...` finds the
change in the installed tree (strongest pre-CI proof the pin resolves to a tree that actually has the fix).

### Hop 4 — CI auto-release builds the image
ds-frontend uses automated semantic-release: merging the bump to `RELEASE_BRANCH` triggers a
**`chore(release): 2.18.x`** commit by the GitHub Actions Bot, which builds the Docker image tagged
`…:2.18.x` (and moves the floating `:2.18` tag).
**Gate:** a new `chore(release): 2.18.x` commit exists whose history contains your bump —
`git tag --contains <bump-sha>` (or the first `chore(release)` after it). Record that **version**;
that is the deployable image.

### Hop 5 — Deploy to the instance + live-verify
Roll the instance's `ds-frontend` service to the new image. The mechanism differs by host
orchestration (Docker Swarm vs compose) — see the memory note
`eregistrations-host-orchestration-varies-swarm-vs-compose` and
`eregistrations-live-deploy-and-verify-gotchas`. Floating `:2.18` does NOT auto-pull: force it.
```bash
# Swarm:   docker service update --image <registry>/ds-frontend:2.18 --force <service>
# Compose: docker compose pull ds-frontend && docker compose up -d --force-recreate ds-frontend
```
**Gate — the real definition of done:** verify the **runtime behaviour**, not "image deployed". The
public URL/status can be CDN-cached stale for hours. The strongest check is to load the affected form
in a logged-in browser and inspect the live formio runtime — e.g. reach the component instance and
exercise the exact behaviour the fix changed:
```js
// in the browser console on the loaded form (example: a Select component method)
Object.values(window.Formio.forms)[0].everyComponent(c => { /* find your component, call the method */ });
```
Only after this passes is the change delivered. THEN post the ticket confirmation.

## Gotchas (each one has burned a real delivery)

- **Merging the source PR is not shipping.** The pin still points at the old SHA. Always finish the chain.
- **Pattern B double-repo trap.** For `formiojs`, a source merge with no dist mirror = nothing ships.
  The dist repo is the one ds-frontend installs.
- **Right release line.** Bump the **current live line** (`$RELEASE_BRANCH`, discovered above — at
  time of writing that was `release/2.18`). Each `release/N.M` is a *separate* branch with a *separate*
  pin: the previous line (e.g. `release/2.17` when 2.18 is live) does NOT inherit a bump on the newer
  line — a fix only reaches an older line via an explicit backport. Confirm which line the target
  instance actually runs before you pick the branch.
- **`git log -S` lies for pin bumps.** A SHA→SHA edit keeps the string `…-4.x.git#` present, so its
  count is unchanged and `-S` shows nothing. Use `git log -L '/"<dep>":/,+1:package.json'`.
- **Stale local refs cause phantom "never shipped" conclusions.** The local clones are often parked on
  an old branch (e.g. ds-frontend on `release/2.17`). If you read a stale `release/2.18` you may see an
  *ancestor* SHA and wrongly decide a prior fix was never delivered, then branch the dist mirror off the
  wrong base. Always `git fetch` and read `origin/<branch>`, and order-check SHAs with
  `git merge-base --is-ancestor`. Cross-check against `references/repo-map.md`: e.g. `cbda1f1c` (VUCE-42
  PR#3) **is** live — it shipped as `2.18.283` and is the current `origin/release/2.18` pin.
- **The pin is immutable.** There is no floating ref to "just rebuild"; you must bump the SHA.
- **Floating `:2.18` is digest-cached on swarm.** `--force` (or compose `pull` + `--force-recreate`),
  else the node keeps the old image.
- **Verify behaviour, not deployment.** CDN-cached `/status`, stale floating tags, and "pods restarted"
  all lie. Drive the actual UI behaviour.
- **Access is gated.** Dist-repo merge, ds-frontend merge, CI release, and the host deploy generally
  need maintainer rights (historically **Erick León Bolinaga**). If you lack them, prepare the
  branches/PRs and hand off the two SHAs + the release/deploy ask — don't claim "deployed".

## Worked example (fully verified)

`references/repo-map.md` contains the complete VUCE-42 commit trail — source PR, the dist mirror
commit, the ds-frontend bump, the release version, and the deploy — as a concrete template to copy.
Use it to sanity-check that your own chain has every hop and that the SHAs line up.

## Definition of done

Every hop's gate passed, ending with a **live runtime check on the instance** proving the new
behaviour — and only then the stakeholder/ticket update. A merged PR, a green CI, or "the image is
out" are necessary but not sufficient; the runtime check is the contract.
