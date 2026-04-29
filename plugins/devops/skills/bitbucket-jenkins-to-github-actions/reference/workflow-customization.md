# Workflow customization guide

This guide accompanies the canonical templates. Two templates exist:

- [`workflow-template.yml`](workflow-template.yml) — for **deployable Docker apps** (mule3-benin, ds-backend, BPA-backend)
- [`workflow-template-library.yml`](workflow-template-library.yml) — for **Maven libraries** that publish artifacts via the `packages` branch (mule-common, mule3-datamapping-connector)

After copying the matching template into the target repo's `.github/workflows/ci-cd.yml`, work through the sections below.

## 0. Choose template: app or library

| Signal in the source repo | Use this template |
|---|---|
| Has Dockerfile + produces a runnable image | `workflow-template.yml` (app) |
| `pom.xml` has `<packaging>` of `jar`, `mule-module`, `maven-plugin`, or `pom`; **no Dockerfile** | `workflow-template-library.yml` (library) |

SKILL.md Step 3.2.0's library detection automates the heuristic; sections 1–4 below cover **app-mode** customization, sections 5–7 cover **library-mode** specifics.

## 1. Replace placeholders

Two placeholders appear in the template. Both must be replaced before commit.

| Placeholder | Meaning | Where to find the value | Example |
|---|---|---|---|
| `<DOCKER_IMAGE_NAME>` | Full Docker Hub image path used as the runtime image (without tag). Appears in `env.DOCKER_IMAGE`, `env.EPHEMERAL_IMAGE` (×2 jobs), and the Docker Hub API cleanup URL (×2 jobs). | The Jenkinsfile usually has it in a `dockerImage` variable or a `docker.build`/`docker push` invocation. Org convention: `unctad/<repo-name>` (lowercase, hyphenated). | `unctad/mule3-benin` |
| `<REPO_NAME>` | Short identifier used only as part of the npm cache key in `bump-version`. Distinct cache namespaces per repo prevent cross-contamination on shared runners. | The repo directory name (or anything stable that's unique across the org). Convention: same as the Docker image suffix. | `mule3-benin` |

Recommended sed pass once you know the values:

```bash
sed -i \
  -e 's|<DOCKER_IMAGE_NAME>|unctad/mule3-benin|g' \
  -e 's|<REPO_NAME>|mule3-benin|g' \
  .github/workflows/ci-cd.yml
```

## 2. Fill the `<BUILD_STEP>` block in `build-docker-image`

The template marks the build sequence as a comment block in `build-docker-image`. The Docker build/push steps that follow assume a build context is already prepared (Maven artifact, Python package, npm bundle, etc.). Pick the recipe that matches the repo:

### Java / Maven (e.g. mule3-benin, BPA-backend, ActiveMQ)

```yaml
      - name: Build Maven artifact
        run: |
          mvn -DskipTests -DlightweightPackage -Dfile.encoding=UTF-8 clean package

      - name: Setup SSH agent
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

      - name: Add remote hosts to known_hosts
        run: |
          mkdir -p ~/.ssh
          # TODO: Update this URL when eregistrations-tools is confirmed migrated to GitHub
          ssh-keyscan -t rsa bitbucket.org >> ~/.ssh/known_hosts

      - name: Clone eregistrations-tools
        run: |
          rm -rf eregistrations-tools
          # TODO: Update to GitHub URL once eregistrations-tools is confirmed migrated
          git clone git@bitbucket.org:unctad/eregistrations-tools.git
```

Notes:
- `-DskipTests` is intentional — tests run in `run-tests` job (if uncommented), not in the build job.
- `-DlightweightPackage` is a Mule3-specific Maven property; for non-Mule Java projects (BPA-backend, ActiveMQ), drop it.
- The `eregistrations-tools` clone is needed for Mule3 / BPA shared utility scripts; the `bitbucket.org` references are tracked TODOs until that repo migrates to GitHub.

### Python (e.g. ds-backend)

No separate build step before `docker build` — the Dockerfile handles it via multi-stage builds. Instead, add a GitHub App token step for cross-repo access:

```yaml
      - name: Generate GitHub App Token for Python-Commons
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ vars.DEPENDENCY_PROPAGATOR_ID }}
          private-key: ${{ secrets.DEPENDENCY_PROPAGATOR_SECRET }}
          owner: UNCTAD-eRegistrations
          repositories: Python-Commons
```

Then change the `Build Docker image (ephemeral)` step's `docker build` to pass the token via BuildKit secret:

```yaml
      - name: Build Docker image (ephemeral)
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          docker build \
            --target runtime \
            --ssh default \
            --secret id=github_token,env=GH_TOKEN \
            --build-arg BRANCH=${{ github.ref_name }} \
            -t "$EPHEMERAL_IMAGE" \
            .
```

### Frontend / Node (e.g. atlas-* repos)

Build the static bundle, then let `docker build` package it:

```yaml
      - name: Set up Node.js (for build)
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install dependencies
        run: npm ci

      - name: Build production bundle
        run: npm run build
```

Then the existing `docker build` step copies the bundle into the image.

### Mule3 ESB (mule3-benin specifics)

Use the Java/Maven recipe above. Note that mule3-benin's Dockerfile only declares `ARG VERSION` (not `ARG ENV`) — the `ENV` build-arg passed by the template is currently dead code in the image, but the pass-through is preserved by convention to make a future Dockerfile change a one-line addition.

## 3. Optional add-on jobs

The template's bottom half lists four optional jobs as commented-out stubs. Uncomment each one only if the repo has the corresponding signal AND a working pattern to copy from.

| Optional job | Repo signal | Pattern source | Wiring needed in `push-docker-image` |
|---|---|---|---|
| `helm-chart-update` | `helm/Chart.yaml` exists | SKILL.md Step 3.2.3 (full template) | None — it runs on its own, not gated by docker. Make sure `set-build-variables` exposes a `should_update_helm` output (see SKILL.md Step 3.2.1 details). |
| `run-tests` | `pytest`, `jest`, or similar test runner exists; Dockerfile has a `test` target | ds-backend's `run-tests` (lines 615+ in its `ci-cd.yml`) | Add `run-tests` to `push-docker-image.needs:`; extend `if:` with `(needs.run-tests.result == 'success' \|\| needs.run-tests.result == 'skipped')`. |
| `run-linting` | linter config (`pyproject.toml` ruff/black, `.eslintrc`, etc.) | ds-backend's `run-linting` (lines 804+ in its `ci-cd.yml`) | Same as `run-tests`. |
| `qodana-analysis` | `.qodana.yaml` or `qodana.yaml` exists | ds-backend's `qodana-analysis` (lines 926+ in its `ci-cd.yml`) | Same as `run-tests`. |
| `artifact-cleanup` | Any job uses `actions/upload-artifact` | ds-backend's `artifact-cleanup` (lines 1304+ in its `ci-cd.yml`) | Add to `notify-failure.needs:` (cleans up on both success and failure paths via its own `if: always()`). |

To uncomment a section, remove the leading `# ` from each line in that block. Be careful with indentation — YAML is whitespace-sensitive, and the `# ` prefix in commented YAML is exactly 2 characters that need to vanish without disturbing indent.

When adding a job to `push-docker-image.needs:`, also extend `set-build-variables`'s `outputs:` to expose the corresponding `should_*` flag the new job will gate on (see ds-backend's set-build-variables for the pattern).

## 4. Validation

Run actionlint with the org's runner-label config (see SKILL.md GATE 3-4):

```bash
actionlint -config-file ~/.config/actionlint.yaml .github/workflows/ci-cd.yml
```

Expected: clean output (only the standard custom-runner-label warnings if you forget the config file).

Then the gap self-audit grep loop from SKILL.md GATE 3-4 will confirm all 12 canonical patterns are present:

```bash
for pattern in "build-docker-image" "push-docker-image" "tag-release" "ephemeral" "imagetools create" \
               "FEATURE_" "actions/cache@v4" "actions/setup-node@v4" "MINOR_TAG"; do
  grep -q "$pattern" .github/workflows/ci-cd.yml || echo "MISSING: $pattern"
done
```

Any `MISSING:` line means a placeholder wasn't replaced, an optional section wasn't uncommented when it should have been, or a customization step accidentally removed required content. Fix and re-run before pushing.

## 5. Library-mode placeholders (workflow-template-library.yml)

For library repos, two additional placeholders appear in the `env:` block:

| Placeholder | Meaning | How to find |
|---|---|---|
| `<ARTIFACT_GROUP_ID>` | Maven coordinates groupId. Used to compute the path inside `packages/` (dots → slashes) | First `<groupId>` element in `pom.xml`, e.g. `org.unctad.eregistrations.mule.modules` |
| `<ARTIFACT_ID>` | Maven artifactId — also used as the JAR filename prefix and the title pattern in propagator PR searches | First `<artifactId>` element in `pom.xml`, e.g. `datamapping` |
| `<REPO_NAME>` | (same as app mode) — short repo identifier for the npm cache key | The Bitbucket/GitHub repo name |

Also no `<DOCKER_IMAGE_NAME>` placeholder — libraries don't push Docker images.

Recommended sed pass:
```bash
sed -i \
  -e 's|<ARTIFACT_GROUP_ID>|org.unctad.eregistrations.mule.modules|g' \
  -e 's|<ARTIFACT_ID>|datamapping|g' \
  -e 's|<REPO_NAME>|mule3-datamapping-connector|g' \
  .github/workflows/ci-cd.yml
```

## 6. Library `<BUILD_STEP>` recipes

The library template marks the build sequence as a comment block in `build-and-publish`. Pick the recipe that matches the repo:

### Mule 3 module / connector (mule-devkit-parent)

```yaml
      - name: Build Maven artifact
        run: |
          mvn -DskipTests -Dfile.encoding=UTF-8 clean package
```

The packages-branch publish step expects the artifact at `target/${ARTIFACT_ID}-${VERSION}.jar` — the standard Maven default. The encoding flag is required for some Mule 3 plugins that mishandle non-UTF-8 sources.

### Plain Java/Maven library

```yaml
      - name: Build Maven artifact
        run: |
          mvn -DskipTests clean package
```

Drop `-Dfile.encoding=UTF-8` if there's no specific reason to set it.

### Multi-module Maven (build a single sub-module)

```yaml
      - name: Build Maven artifact
        run: |
          mvn -DskipTests -pl <module-name> -am clean package
```

`-pl` selects the module; `-am` builds its dependencies first. The publish step still expects `target/${ARTIFACT_ID}-${VERSION}.jar`, so the selected module's artifactId must match `<ARTIFACT_ID>`.

### Library with cross-repo build dependencies (e.g. mule-common)

If the library being built depends on ANOTHER UNCTAD-internal artifact (e.g. mule3-datamapping-connector itself depends on mule-common), the build step needs the same packages-branch fetch we apply in app-mode `<BUILD_STEP>`. Stage upstream UNCTAD artifacts into `~/.m2/repository` BEFORE the `mvn` call. See `mule3-benin/.github/workflows/ci-cd.yml`'s "Fetch mule-common from Bitbucket packages branch" step as a reference pattern.

## 7. Propagate-version: managing the consumer matrix

The library template ships with an **empty** consumer matrix — each adopting library populates its own list. There is no org-wide default; different libraries have different downstream consumers.

### Adding a consumer

In the `propagate-version` job's `strategy.matrix.consumer` list, add a YAML list item — **repo name only** (no org prefix). The org is hardcoded as `UNCTAD-eRegistrations` in the token-generation step and the `CONSUMER` env. Format:

```yaml
        consumer:
          - mule3-benin
          - mule3-togo
          # ...
```

Next master push CI run will start propagating to each. Two prerequisites for a new consumer:
1. The `unctad-dependency-propagator` GitHub App must be installed on the consumer repo (one-time, in App settings)
2. The consumer must have a `pom.xml` with the matching `<artifactId>` (Maven only — non-Maven consumers need extension; see below)

### Removing a consumer

Comment out or delete the matrix entry. No state cleanup needed — already-merged bumps stay in place.

### What the propagator does, per consumer

1. Clones consumer's `develop` (depth 1) using `secrets.PROPAGATOR_TOKEN` (or falls back to `GITHUB_TOKEN`, which only works same-repo).
2. Updates the matching `<artifactId>` block's `<version>` in `pom.xml` via sed.
3. **Closes superseded propagator PRs first** — only PRs (a) authored by the propagator's actor AND (b) titled `chore: bump <ARTIFACT_ID> to *`. Human-authored PRs touching the same dep are NEVER closed.
4. Opens a new PR `chore: bump <ARTIFACT_ID> to <NEW_VERSION>` against the consumer's `develop`.
5. Calls `gh pr merge --merge --delete-branch` to merge immediately and remove the propagator's bump branch on the consumer side. With current org branch-protection state (no required checks), this succeeds. If consumers later add protections, the merge attempt errors and the PR is left open for human handling (branch retained) — the propagator surfaces this as a `::warning::`.

### Authentication: the `unctad-dependency-propagator` GitHub App

Cross-repo `gh pr create`/`merge`/`close`/`list` calls need a token with `contents:write` + `pull_requests:write` on each consumer. `secrets.GITHUB_TOKEN` only works same-repo — cross-repo requires a custom token.

The org has a long-lived solution: the **`unctad-dependency-propagator` GitHub App** (org-installed, slug `unctad-dependency-propagator`). The library template uses `actions/create-github-app-token@v1` to exchange the App's credentials for a 1-hour scoped token at runtime. **No PAT, no rotation.**

Org-level config (already provisioned, inherited by every library repo):
- Variable: `DEPENDENCY_PROPAGATOR_ID` — the App's numeric ID
- Secret: `DEPENDENCY_PROPAGATOR_SECRET` — the App's private key

What new libraries need to do: **install the App** on (a) the library itself and (b) each consumer in the matrix. App settings → Configure → Repository access → Add repos. Permissions are inherited from the App (currently `contents:write` + `pull_requests:write`).

If the App isn't installed on a consumer, `actions/create-github-app-token@v1` fails with a clear error pointing at the missing installation. The propagator step doesn't fall back to `GITHUB_TOKEN` (would silently fail cross-repo). Surface the failure, fix the App installation, re-run the workflow.

### Custom bump logic for non-Maven consumers

Out of scope for v1. The propagator's pom.xml-bump path assumes Maven consumers. For npm/pnpm/poetry/etc. consumers, extend the propagator step with per-matrix-entry conditional logic (e.g., a `bump_command:` matrix dimension). Document in a follow-up.

## 8. Validation

Run actionlint with the org's runner-label config (see SKILL.md GATE 3-4):

```bash
actionlint -config-file ~/.config/actionlint.yaml .github/workflows/ci-cd.yml
```

Expected: clean output (only the standard custom-runner-label warnings if you forget the config file).

Then run the gap self-audit grep loop from SKILL.md GATE 3-4 to confirm canonical patterns are present (different patterns for app vs library mode — see GATE 3-4).

## 9. Git LFS handling (cross-cutting; both app and library mode)

If Phase 0.5.2 detected `HAS_LFS=yes`, the migrated repo has binaries tracked via Git LFS (e.g. `mule-distribution/*.tar.gz` in mule3-benin). The library/app template's checkout steps don't ship LFS-aware by default — the additions below are required for any job that consumes LFS-tracked files (typically `build-docker-image` or `build-and-publish`).

### What's needed

1. **Ensure `git-lfs` is on the runner** before the checkout. Self-hosted runners often lack it. Install on demand:

   ```yaml
       - name: Ensure git-lfs is available
         run: |
           if command -v git-lfs >/dev/null 2>&1; then
             echo "git-lfs already on PATH: $(command -v git-lfs)"
             git-lfs --version | head -1
             exit 0
           fi
           LFS_VERSION="3.7.0"
           ARCH="$(uname -m)"
           case "$ARCH" in
             x86_64)         LFS_ARCH="amd64" ;;
             aarch64|arm64)  LFS_ARCH="arm64" ;;
             *) echo "::error::Unsupported arch: $ARCH"; exit 1 ;;
           esac
           TARBALL="git-lfs-linux-${LFS_ARCH}-v${LFS_VERSION}.tar.gz"
           # Retry on transient errors (502/503/504/connect failures from CDN).
           curl -fsSL --retry 5 --retry-delay 5 --retry-max-time 60 \
             "https://github.com/git-lfs/git-lfs/releases/download/v${LFS_VERSION}/${TARBALL}" \
             -o "/tmp/${TARBALL}"
           tar -xzf "/tmp/${TARBALL}" -C /tmp
           mkdir -p "$HOME/.local/bin"
           ln -sf "/tmp/git-lfs-${LFS_VERSION}/git-lfs" "$HOME/.local/bin/git-lfs"
           echo "$HOME/.local/bin" >> "$GITHUB_PATH"
   ```

2. **Set `lfs: true`** on the checkout AND **drop `clean: false`** (default `clean: true`). Self-hosted runners reuse workspaces; a stale LFS pointer file from a prior run that didn't have git-lfs may not be re-smudged unless the workspace is clean.

   ```yaml
       - name: Checkout code
         uses: actions/checkout@v4
         with:
           ref: ${{ github.ref_name }}
           fetch-depth: 0
           lfs: true
           # Drop `clean: false` for LFS jobs — stale pointer files persist otherwise.
   ```

3. **Defensive `git lfs pull` + MD5 sanity check** after the existing "Pull latest changes" step. `actions/checkout@v4` with `lfs: true` is supposed to smudge automatically, but on reused workspaces it occasionally leaves the pointer file in place. The explicit pull guarantees smudging; the MD5 check fails fast (saves the multi-minute mvn run otherwise wasted on a broken artifact):

   ```yaml
       - name: Pull latest + LFS smudge + sanity check
         run: |
           git pull origin ${{ github.ref_name }} || true
           git lfs install --local
           git lfs pull
           # OPTIONAL: per-file MD5 verification. Uncomment + set EXPECTED_MD5 if
           # the binary has a known checksum (e.g. mule-standalone-3.9.5.tar.gz).
           # if [ -f path/to/binary ]; then
           #   ACTUAL=$(md5sum path/to/binary | awk '{print $1}')
           #   EXPECTED="0a307cd20fce11426750b8f5d6dae730"
           #   [ "$ACTUAL" = "$EXPECTED" ] || { echo "::error::MD5 mismatch — LFS smudge failed"; exit 1; }
           # fi
   ```

### Why all three are needed

| Symptom | Without fix |
|---|---|
| `Unable to locate executable: git-lfs` | actions/checkout@v4 errors before the workflow does anything useful |
| Pointer file checked out instead of binary (Dockerfile MD5 fail / "is ASCII text" surprises) | Build silently consumes the 100-byte text pointer instead of the actual artifact |
| First-time-on-clean-runner works, second run fails | Reused workspace + stale pointer + `clean: false` = LFS doesn't re-smudge |

### Source-side reminder (Phase 2)

The skill's Phase 2.3/2.4 enforces `git lfs push --all github` + verification when `HAS_LFS=yes`. Without that, the LFS objects never reach GitHub even if pointer files do. **Verify Phase 2 succeeded** (Migration Validation report from Phase 5.5) before fighting consumer-side smudge issues.

## 10. Cross-repo private-read via the unctad-dependency-propagator App

When an app consumes a library that publishes via the packages-branch trick (e.g. mule3-benin reading from mule3-datamapping-connector's `packages` branch), the consumer's CI needs to clone the library repo. Two complications:

1. **The runner's `SSH_PRIVATE_KEY` only authenticates to bitbucket.org** (the standard org SSH key). It does NOT have GitHub access.
2. **`secrets.GITHUB_TOKEN` is implicitly scoped to the running repo** — won't authenticate to other private GitHub repos.

The org standard solution: reuse the **`unctad-dependency-propagator` App**. It's already installed (the App that powers library propagator PRs) and has `contents:write` on the libraries it propagates from. Generate a per-job, scoped App token and HTTPS-clone with it.

### Recipe (for `<BUILD_STEP>` in app template's `build-docker-image`)

Place these two steps after the JDK setup, before the `mvn` build:

```yaml
      - name: Generate token for <library> access
        id: <library>-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ vars.DEPENDENCY_PROPAGATOR_ID }}
          private-key: ${{ secrets.DEPENDENCY_PROPAGATOR_SECRET }}
          owner: UNCTAD-eRegistrations
          repositories: <library-repo-name>   # e.g. mule3-datamapping-connector

      - name: Fetch <library> from GitHub packages branch
        env:
          GH_TOKEN: ${{ steps.<library>-token.outputs.token }}
        run: |
          LIB_VERSION=$(grep -A 20 '<artifactId><artifactId-here></artifactId>' pom.xml \
            | grep -m 1 '<version>' \
            | sed 's/.*<version>\(.*\)<\/version>.*/\1/')
          if [ -z "$LIB_VERSION" ]; then
            echo "::error::Could not extract <library> version from pom.xml"
            exit 1
          fi

          TARGET=~/.m2/repository/<groupId-as-path>/<artifactId>/${LIB_VERSION}
          if [ -f "$TARGET/<artifactId>-${LIB_VERSION}.jar" ]; then
            echo "<library> ${LIB_VERSION} already cached, skipping fetch"
            exit 0
          fi

          PKG_DIR=$(mktemp -d)
          # HTTPS + App token. The runner's SSH key only authenticates to bitbucket.org.
          git clone --depth 1 -b packages \
            "https://x-access-token:${GH_TOKEN}@github.com/UNCTAD-eRegistrations/<library-repo-name>.git" \
            "$PKG_DIR"

          SRC="$PKG_DIR/<groupId-as-path>/<artifactId>/${LIB_VERSION}"
          if [ ! -d "$SRC" ]; then
            echo "::error::<library> ${LIB_VERSION} not found in packages branch (looked at $SRC)"
            exit 1
          fi

          mkdir -p "$TARGET"
          cp "$SRC"/* "$TARGET/"
```

### Prerequisites (one-time per consumer + library pair)

- The `unctad-dependency-propagator` App must be installed on **both** the consumer repo (so `actions/create-github-app-token@v1` can issue tokens from the consumer's workflow) and the library repo (so the issued token can read it).
- Org-level vars/secrets `DEPENDENCY_PROPAGATOR_ID` + `DEPENDENCY_PROPAGATOR_SECRET` exist (already provisioned for the propagator).

### Why not SSH

Adding a GitHub deploy key per consumer-library pair works but doesn't scale — N×M keys to rotate. The org App is one-time setup with auto-rotating tokens.

### Why not `secrets.GITHUB_TOKEN`

`GITHUB_TOKEN` is repo-scoped and can only access the running repo, never other private repos in the org. A 403 / "Not Found" cross-repo clone is the symptom.

## Reference

- App template: [`workflow-template.yml`](workflow-template.yml)
- Library template: [`workflow-template-library.yml`](workflow-template-library.yml)
- App patterns and rationale: [`critical-patterns.md`](critical-patterns.md) §§ 24–31
- Library patterns and rationale: [`critical-patterns.md`](critical-patterns.md) §§ 32–33
- Cross-cutting LFS handling: [`critical-patterns.md`](critical-patterns.md) §34
- Cross-cutting App-token cross-repo fetch: [`critical-patterns.md`](critical-patterns.md) §35
- Incident driving the app-template design: [`lessons-learned.md`](lessons-learned.md) "Critical Failure #9: Heavy Runner Missing Node + 12 Structural Gaps (mule3-benin migration, 2026-04)"
