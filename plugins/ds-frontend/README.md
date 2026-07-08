# ds-frontend

ds-frontend delivery and formio fork integration skills for eRegistrations.

## Skills

| Skill | Description |
|-------|-------------|
| `ship-formio-fork-to-ds-frontend` | Deliver a change in a UNCTAD eRegistrations formio fork all the way to a deployed instance. Use whenever a fix/feature has been (or needs to be) merged in one of the formio forks — `formiojs` (`formiojs-4.x-src` → `formiojs-4.x`), `@formio/angular`, `formio-signature`, `formio-dropdown`, `formio-leaflet-map`, `formio-nested-html-element` — and must actually reach users. Covers the full chain: source PR → (formiojs only) transpile-and-mirror into the `formiojs-4.x` dist repo → bump the git-SHA pin in `ds-frontend/package.json` on the right release branch → CI auto-release (`chore(release): 2.18.x` image) → deploy the image → live-verify the runtime behaviour. |

## Formio Fork Delivery Pattern

The ds-frontend uses git-SHA pinning for six formio packages, split into two patterns:

- **Pattern A — single-repo fork**: `@formio/angular`, `formio-signature`, `formio-dropdown`, `formio-leaflet-map`, `formio-nested-html-element`. The source repo itself is pinned; changes ship directly.
- **Pattern B — split source→dist**: `formiojs` only. The source repo `formiojs-4.x-src` (ESM) must be transpiled and mirrored into the dist repo `formiojs-4.x` (babel-CJS). A source merge is invisible until transpile-and-mirror completes.

See `skills/ship-formio-fork-to-ds-frontend/references/repo-map.md` for the authoritative fork list, SHAs, and a worked example (VUCE-42).

## Definition of Done

Every hop's gate must pass:
1. Source PR merged on the fork's default branch
2. (Pattern B / formiojs only) Compiled output mirrored into dist repo
3. ds-frontend pin updated on the release branch, PR merged
4. CI auto-release committed the new version
5. Instance deployed with the new image
6. **Live runtime check proves the behaviour** — the actual change is visible and working

A merged PR, green CI, or "the image is out" are necessary but not sufficient. The runtime check is the contract.
