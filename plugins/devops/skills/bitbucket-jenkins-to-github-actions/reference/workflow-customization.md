# Workflow customization guide

This guide accompanies [`workflow-template.yml`](workflow-template.yml). After copying the canonical template into the target repo's `.github/workflows/ci-cd.yml`, work through the four sections below in order.

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

## Reference

- Canonical template: [`workflow-template.yml`](workflow-template.yml)
- Patterns and rationale: [`critical-patterns.md`](critical-patterns.md) §§ 24–31
- Incident driving this design: [`lessons-learned.md`](lessons-learned.md) "mule3-benin migration (2026-04)"
