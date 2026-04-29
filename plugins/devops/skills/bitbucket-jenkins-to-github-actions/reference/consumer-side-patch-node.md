# Consumer-side patch: adopting a Node library that publishes to a `packages` branch

When a Node.js library is migrated to the **packages-branch + tarball** distribution
(see `workflow-template-library-node.yml`), each consumer must be patched once so
its CI fetches `latest/<lib>.tgz` from the library's `packages` branch instead of
trying to resolve a git URL.

This document is a **per-consumer one-time patch checklist**. After this patch lands
on the consumer's `develop`, every subsequent library publish is picked up
automatically (consumer's CI fetches the new tarball, regenerates lock, builds).

Reference adopters (validated 2026-04): `JS-Assistant`, `DS-Frontend`.
Reference library: `Json-Logic-Extension`.

---

## When to apply this patch

Apply when migrating a consumer that depends on a library distributed via
`packages` branch. Symptoms before applying:

- Consumer's CI fails at `npm install --no-save standard-version` (or `npm ci`)
  with `git@github.com: Permission denied (publickey)` against a private library
  repo, OR with `npm error code 128 ... ls-remote ssh://git@github.com/...`.
- The library's `package.json` URL in the consumer is `bitbucket:...`,
  `git+https://github.com/...`, or `github:OWNER/REPO` — i.e. resolution
  requires authenticated git access at npm-install time.

This patch eliminates the auth-at-install class of failures by switching the
consumer to a `file:./vendor/<lib>.tgz` URL, with the `.tgz` fetched at CI time
via a GitHub App token.

---

## Prerequisites

1. The library publishes to its own `packages` branch with structure
   `latest/<lib>.tgz` and `<version>/<lib>.tgz`.
2. Org has variable `vars.DEPENDENCY_PROPAGATOR_ID` and secret
   `secrets.DEPENDENCY_PROPAGATOR_SECRET` (App: `unctad-dependency-propagator`).
3. The App is installed on the library repo (for `contents:read`).
4. Consumer's `package.json` currently has the library as a git/bitbucket URL.

---

## Patch checklist

Apply ALL of these in a single commit on the consumer's `develop` branch.

### 1. `package.json`

Change the library dependency from `git+https://...`/`bitbucket:...`/`github:OWNER/REPO`
to a local file URL:

```diff
   "dependencies": {
-    "<LIB_NAME>": "git+https://github.com/UNCTAD-eRegistrations/<LIB_REPO>.git#X.Y.Z"
+    "<LIB_NAME>": "file:./vendor/<LIB_NAME>.tgz"
   }
```

### 2. `package-lock.json`

Regenerate the entry by running locally (use `--legacy-peer-deps` only if your
project already needs it):

```bash
mkdir -p vendor
# Pull current latest tgz once locally to regenerate the lock entry with valid
# integrity. After commit, CI will refresh integrity on every run anyway.
gh api repos/UNCTAD-eRegistrations/<LIB_REPO>/contents/latest/<LIB_NAME>.tgz?ref=packages \
  --jq '.content' | base64 -d > vendor/<LIB_NAME>.tgz

NPM_CONFIG_ENGINE_STRICT=false \
  npm install --package-lock-only --no-audit --no-fund \
  file:./vendor/<LIB_NAME>.tgz
```

The lock entry should now look like:
```json
"node_modules/<LIB_NAME>": {
  "version": "<X.Y.Z>",
  "resolved": "file:vendor/<LIB_NAME>.tgz",
  "integrity": "sha512-..."
}
```

### 3. `.gitignore`

Add the tgz path so the binary isn't committed:

```diff
+# Library tarballs fetched at CI time from <LIB_REPO> packages branch
+/vendor/*.tgz
```

The `vendor/` directory itself is created at CI time; no `.gitkeep` needed.

### 4. `Dockerfile`

If the consumer builds a Docker image (most do), add a `COPY` for `vendor/` to
the build stage that runs `npm ci`. Place it next to the existing
`COPY package.json package-lock.json ...`:

```diff
 COPY package.json package-lock.json ./
+COPY vendor ./vendor
```

For multi-stage Dockerfiles only the *builder* stage needs `vendor/` (the
runtime stage gets node_modules from the builder).

### 5. CI workflow

Add **two** new steps in **every job that runs `npm install` or `npm ci`** —
typically `bump-version`/`patch-release` (runs `npm install --no-save standard-version`)
and `build-and-push-docker` (runs `npm ci` before docker build).

Insert immediately AFTER `actions/setup-node@v4` and BEFORE the npm install:

```yaml
      - name: Generate token for <LIB_NAME> package access
        id: jle-token   # rename if multiple libraries are consumed
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ vars.DEPENDENCY_PROPAGATOR_ID }}
          private-key: ${{ secrets.DEPENDENCY_PROPAGATOR_SECRET }}
          owner: UNCTAD-eRegistrations
          repositories: <LIB_REPO>

      - name: Fetch <LIB_NAME> tarball from packages branch
        env:
          GH_TOKEN: ${{ steps.jle-token.outputs.token }}
        run: |
          mkdir -p vendor
          curl -sSL --fail \
            -H "Authorization: Bearer ${GH_TOKEN}" \
            -H "Accept: application/vnd.github.raw" \
            "https://api.github.com/repos/UNCTAD-eRegistrations/<LIB_REPO>/contents/latest/<LIB_NAME>.tgz?ref=packages" \
            -o vendor/<LIB_NAME>.tgz
          ls -la vendor/<LIB_NAME>.tgz
          # Refresh lock entry so integrity matches the fetched tarball.
          # Only needed in jobs that run `npm install --no-save` or similar
          # mutating installs; jobs that run `npm ci` strictly can skip this
          # IF the committed lock matches today's `latest/`. To be safe, always
          # include this line — it's idempotent when integrity already matches.
          npm install --package-lock-only --no-audit --no-fund \
            <-LEGACY-PEER-DEPS-IF-NEEDED-> \
            file:./vendor/<LIB_NAME>.tgz
```

Replace `<-LEGACY-PEER-DEPS-IF-NEEDED-->` with `--legacy-peer-deps` for
Angular/large-tree consumers (DS-Frontend pattern); drop it otherwise
(JS-Assistant pattern).

### 6. (Optional) Consumer's `workflow_dispatch`

If the library uses `propagate-version` to dispatch consumer CIs, the consumer
must already have `workflow_dispatch:` in its `on:` block. Most repos do; verify:

```yaml
on:
  push:
    branches: [develop, ...]
  workflow_dispatch:   # required for library to trigger this consumer
```

---

## Verification

After committing and pushing to `develop`:

1. Watch the resulting CI run:
   ```bash
   gh run watch --repo UNCTAD-eRegistrations/<CONSUMER_REPO>
   ```

2. Confirm the new "Fetch ... tarball" step ran and produced
   `vendor/<LIB_NAME>.tgz` of the expected size (≥ a few KB).

3. Confirm `npm install --no-save standard-version` (or `npm ci`) completes
   without `Permission denied` errors.

4. After docker build, confirm the image was pushed.

5. Test the propagation loop end-to-end: bump the library, watch the consumer's
   CI run automatically (if `propagate-version` is configured) OR manually
   dispatch and confirm it picks up the new tarball.

---

## Common pitfalls

- **`npm ci` fails with `EINTEGRITY`** — the committed lock's integrity hash
  doesn't match the fetched tarball. Fix: always include the
  `npm install --package-lock-only file:./vendor/<LIB_NAME>.tgz` step before
  `npm ci`. The skill's reference template already does this.
- **Dockerfile builder stage fails on `npm ci`** — `vendor/` not COPYed into
  the builder. Add `COPY vendor ./vendor` before the `RUN ... npm ci` line.
- **`.dockerignore` excludes `vendor`** — verify `.dockerignore` does NOT list
  `vendor` (it usually doesn't, but check). If it does, add a negation
  `!vendor/` or remove the line.
- **App not installed on consumer** — `actions/create-github-app-token@v2`
  fails with 401/403. Install `unctad-dependency-propagator` on the consumer
  via the org installation page.
- **Library has multiple consumers and propagate-version matrix is wrong** —
  see `workflow-template-library-node.yml` § propagate-version matrix.

---

## Backout

If the patch causes problems, revert the consumer commit. The consumer falls
back to its previous git-URL spec. The library's `packages` branch is unaffected
(other consumers can keep using it).
