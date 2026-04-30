# devops

DevOps and deployment skills for eRegistrations infrastructure.

## Skills

| Skill | Description |
|-------|-------------|
| `docker-swarm-migration` | Convert Docker Compose files to Docker Swarm stack format with env var replacement, secrets management, init-secrets.sh generation, reference validation, and dry-run preview |
| `bitbucket-jenkins-to-github-actions` | Migrate a repository from Bitbucket+Jenkins to GitHub+GitHub Actions, including git history, branches, tags, CI/CD pipeline conversion (Jenkinsfile → ci-cd.yml), helm chart updates, branch deletion ruleset, and post-migration validation |
| `upgrade-eregistrations-instance` | **Orchestrator.** Resolves a target instance from a natural phrase like "lesotho test" or "kenya live", detects the deployment shape (compose vs swarm), confirms the source version, then dispatches to the matching upgrade sub-skill. All five envs (dev/test/preview/prelive/live) for the swarm-stack 2.17 → 2.18 pair route to `/upgrade-2.17-to-2.18`. Other version pairs and the `compose` shape abort cleanly with a "no sub-skill registered" message. Compose-shape instances are routed to `/docker-swarm-migration` first — the 2.17 → 2.18 flow assumes the swarm migration has already happened. |
| `upgrade-2.17-to-2.18` | Sub-skill. Mechanically upgrades a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from eRegistrations 2.17 to 2.18 (image bumps, minio swap + healthcheck, deprecated env-var removal). Env-aware anomaly thresholds (`BUILD_TYPE`/`EREGISTRATIONS_VERSION`) and a LIVE retype-country confirmation rail. Commits on a `chore/upgrade-<env>-<country>-2.17-to-2.18` branch, opens a PR (gh on GitHub origins, manual link on Bitbucket). Invoked by the orchestrator or directly. Refuses compose-only instances and points them at `/docker-swarm-migration`. |
| `release-platform` | Cut a new platform release across all 27 eRegistrations repositories — creates `release/<version>` branches from `develop`, pushes them, and bumps the minor version on `develop` in every repo. Sparse-clones in parallel, runs each repo's `minor-release` npm script (or falls back to `standard-version`), and produces per-repo logs. Supports `--dry-run` (read-only preview) and an optional repo filter. |

## Related

- TOBE-17731 — Convert all Docker Compose instances to Docker Swarm
- TOBE-17813 — Epic: DevOps skillification (convert recurring ops tasks into Claude skills)
- TOBE-17814 — `upgrade-eregistrations-instance` orchestrator + 2.17 → 2.18 sub-skill MVP
