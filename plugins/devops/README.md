# devops

DevOps and deployment skills for eRegistrations infrastructure.

## Skills

| Skill | Description |
|-------|-------------|
| `docker-swarm-migration` | Convert Docker Compose files to Docker Swarm stack format with env var replacement, secrets management, init-secrets.sh generation, reference validation, and dry-run preview |
| `correct-db-passwords` | Companion to `docker-swarm-migration`. Discovers every `*_POSTGRES_DB_USER` / `*_MONGO_DB_USER` triple referenced by a stack, pairs each with its matching `*_PASSWORD` in `.env`, and emits `sync-db-passwords.sh` — a self-contained bash script that runs `ALTER USER` on Postgres and `db.changeUserPassword` on MongoDB so the DB-side passwords match what `init-swarm.sh` puts into Docker secrets. Apply / dry-run / generate-sql-files modes. Password-only — never creates users or databases. |
| `bitbucket-jenkins-to-github-actions` | Migrate a repository from Bitbucket+Jenkins to GitHub+GitHub Actions, including git history, branches, tags, CI/CD pipeline conversion (Jenkinsfile → ci-cd.yml), helm chart updates, branch deletion ruleset, and post-migration validation |
| `upgrade-eregistrations-instance` | **Orchestrator.** Resolves a target instance from a natural phrase like "lesotho test" or "syria2 test 2.18", auto-detects the source version from `unctad/*` image tags, detects the deployment shape (compose vs swarm), and dispatches to a chain of upgrade sub-skills (one version step each). Single-step pairs hand off to one sub-skill; multi-step chains (e.g. 2.15 → 2.18) are run by the orchestrator itself with one shared branch, squashed into a single PR. Supported source versions: `2.15`, `2.16`, `2.17`. Compose-shape instances are routed to `/docker-swarm-migration` first. |
| `upgrade-2.17-to-2.18` | Sub-skill. Mechanically upgrades a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from eRegistrations 2.17 to 2.18 (image bumps, minio swap + healthcheck, deprecated env-var removal). Env-aware anomaly thresholds (`BUILD_TYPE`/`EREGISTRATIONS_VERSION`) and a LIVE retype-country confirmation rail. Mode-aware: standalone (own branch + PR) or chain mode (`CHAIN_MODE=1 CHAIN_BRANCH=...`, commit-only on orchestrator-managed branch). Refuses compose-only instances. |
| `upgrade-2.16-to-2.17` | Sub-skill. Upgrades 2.16 → 2.17: bumps `unctad/*:BETA` to `:2.17`, renames the BPA / DS / GDB service families to their 2.17 image keys, pins floating `:DEV` tags on statistics + ds-frontend, version-bumps env vars, bumps Opensearch from 2.12.0 to 2.19.4. Detects legacy Wildfly Keycloak config and aborts with overhaul guidance. Mode-aware. |
| `upgrade-2.15-to-2.16` | Sub-skill. Upgrades 2.15 → 2.16: bumps `unctad/*:RC` to `:BETA` (license-registry → `:DEV`), version-bumps env vars, ensures GDB integration env vars (`USE_NEW_DS`, `GDB_URL`, `REGISTRY_SERVICE_PUBLIC_URL`), renames `RESTHEART_URL` → `RESTHEART_PUBLIC_URL` on bpa-backend, adds `RESTHEART_PASSWORD` on camunda. Mode-aware. |
| `release-platform` | Cut a new platform release across all 27 eRegistrations repositories — creates `release/<version>` branches from `develop`, pushes them, and bumps the minor version on `develop` in every repo. Sparse-clones in parallel, runs each repo's `minor-release` npm script (or falls back to `standard-version`), and produces per-repo logs. Supports `--dry-run` (read-only preview) and an optional repo filter. |

## Related

- TOBE-17731 — Convert all Docker Compose instances to Docker Swarm
- TOBE-17813 — Epic: DevOps skillification (convert recurring ops tasks into Claude skills)
- TOBE-17814 — `upgrade-eregistrations-instance` orchestrator + 2.17 → 2.18 sub-skill MVP
