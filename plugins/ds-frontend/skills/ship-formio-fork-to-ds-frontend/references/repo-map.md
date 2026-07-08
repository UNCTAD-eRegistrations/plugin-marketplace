# Formio fork → ds-frontend delivery: repo map & verified examples

## The forks ds-frontend pins (from `ds-frontend/package.json`)

Each is pinned to an immutable git SHA under `git+ssh://git@github.com:UNCTAD-eRegistrations/…`.

| package.json key | pinned repo | source repo | Pattern |
|---|---|---|---|
| `formiojs` | `formiojs-4.x` (transpiled dist) | `formiojs-4.x-src` (ESM source) | **B — split src→dist** |
| `@formio/angular` | `formio-angular` | same repo | A — single repo |
| `formio-digital-signature-component` | `formio-signature` | same repo | A — single repo |
| `formio-dropdown` | `formio-dropdown` | same repo | A — single repo |
| `formio-leaflet-map` | `formio-leaflet-map` | same repo | A — single repo |
| `formio-nested-html-element` | `formio-nested-html-element` | same repo | A — single repo |

Only `formiojs` is Pattern B. Detect the pattern from the pinned URL: ending in
`formiojs-4.x.git#<sha>` → Pattern B; anything else → Pattern A.

### Pattern B mechanics (formiojs)
- **Source** `formiojs-4.x-src`: ESM, edits land in `src/…`; tests `src/.../*.unit.js`;
  build: `npm run transpile` (babel `src/`→`lib/`) + `npm run templates` (gulp); test:
  `npm run test:unit` = `mocha 'lib/**/*.unit.js'` (`.mocharc.js` uses `@babel/register` +
  `jsdom-global`, `bail:true`, `TZ=UTC`). lib/ and dist/ are gitignored in the source repo.
- **Dist** `formiojs-4.x` (GitHub remote; note a stale Bitbucket mirror also exists — the live one
  ds-frontend pins is GitHub `UNCTAD-eRegistrations/formiojs-4.x`): the compiled npm package, root
  layout (`components/…`, `dist/`, `index.js`, …), babel-CJS.
- **Mapping:** source `lib/<path>` is byte-equivalent to dist `<path>` (verified: same babel output,
  identical `_lodash.default` count). So mirroring = copy the compiled `lib/components/<area>/<File>.js`
  → dist `components/<area>/<File>.js`. Real bump commits touch only the changed component (+ its
  compiled test), not the whole package.

## Verified worked example — VUCE-42 (gdb-catalog select `{key,value}` projection)

All 2026-06-22. This is the template to copy hop-for-hop.

**Hop 1 — Source PR** (`formiojs-4.x-src`)
- Branch `feature/gdb-catalog-keyvalue`; fix commit `09a90e4b` ("fix: project {key,value} for
  gdb-catalog selects (VUCE-42)") touching `src/components/select/Select.js` + a new
  `src/components/select/Select.gdbCatalog.unit.js`. Merged `fdbd2f34` (PR #3).

**Hop 2 — Dist mirror** (`formiojs-4.x`, GitHub)
- Branch `feature/VUCE-42-gdb-catalog-keyvalue-dist`, merged PR #3 → dist commit
  **`cbda1f1c40baff4c467d3395cb2b8024a90895a6`** (author: Erick León Bolinaga). Diff = only
  `components/select/Select.js` (+27, the compiled override) and the compiled
  `components/select/Select.gdbCatalog.unit.js` (+69). Verify: `git grep "dataSrcCatalog === 'gdb'"
  cbda1f1c -- components/select/Select.js`.

**Hop 3 — ds-frontend pin bump** (`release/2.18`)
- Commit **`4bdd3866`** by Erick — *"chore(deps): VUCE-42 bump formiojs-4.x for gdb-catalog
  {key,value}"* — `package.json` `formiojs`: `…#d963e67c… → …#cbda1f1c…`.

**Hop 4 — CI release**
- Immediately followed by **`e7cff47a` = `chore(release): 2.18.283`** (GitHub Actions Bot) — the first
  ds-frontend release whose history contains `4bdd3866`. (Tags containing it: 2.18.283–287.)
  → deployable image `ds-frontend:2.18.283` (+ floating `:2.18`).

**Hop 5 — Deploy + live verify**
- The `:2.18.283`/`:2.18` image rolled onto the instance (cuba). Runtime check: in the loaded PE
  form, `Object.values(window.Formio.forms)[0]` → the subpartida select's `itemValue(record)`
  returned `{…record, key, value}` (the projection), and the published schema carried
  `idPath`/`valuePath`. Only then was the ticket updated.

## The pattern recurs (other recent formiojs bumps, same shape)
From `ds-frontend release/2.18` history of the `formiojs` line — every formiojs renderer change
follows source-merge → dist-mirror → these pin bumps (all by Erick):
- `4bdd3866` 2026-06-22 → `cbda1f1c` — VUCE-42 gdb-catalog
- `cc45a328` 2026-06-17 → `d963e67c` — TOBE-17824 legacy phone-mask normalization
- `34ca6f6e` 2026-05-22 → `5460839…` — TOBE-17849 panel description sub-header
- `550f2b5e` 2026-05-13 → `9ebc16e9e` — TOBE-17804 radio iconClass
- `a9179455` 2026-04-30 → `1d08bf4a7` — TOBE-17817 checkbox-icon markup

## Useful commands
```bash
# current pin + full bump history for any dep (works where `git log -S` fails):
git log -L '/"<DEP>":/,+1:package.json' release/2.18 --pretty='%h | %an | %ad | %s' --date=short

# which release shipped a given ds-frontend bump:
git tag --contains <bump-sha>          # or: first chore(release) after it on release/2.18

# confirm a dist commit really carries the change:
git grep "<symbol-from-diff>" <dist-sha> -- 'components/**'
```

## People / access
- Dist-repo merges + ds-frontend pin bumps + releases historically run through **Erick León Bolinaga**
  (`habanero01@gmail.com`). Bitbucket→GitHub dep migration (TOBE-17420) was Frank Kiibus. Releases are
  cut by the GitHub Actions Bot (`integrator@…` / semantic-release). If you lack merge/deploy rights,
  prepare the dist branch + the ds-frontend bump PR and hand off the two SHAs + the release/deploy ask.
