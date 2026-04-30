# devops

DevOps and deployment skills for eRegistrations infrastructure.

## Skills

| Skill | Description |
|-------|-------------|
| `docker-swarm-migration` | Convert Docker Compose files to Docker Swarm stack format with env var replacement, secrets management, init-secrets.sh generation, reference validation, and dry-run preview |
| `bitbucket-jenkins-to-github-actions` | Migrate a repository from Bitbucket+Jenkins to GitHub+GitHub Actions, including git history, branches, tags, CI/CD pipeline conversion (Jenkinsfile → ci-cd.yml), helm chart updates, branch deletion ruleset, and post-migration validation |
| `upgrade-eregistrations-instance` | **Orchestrator.** Resolves a target instance from a natural phrase like "lesotho test" or "kenya live", detects the deployment shape (compose vs swarm), confirms the source version, then dispatches to the matching upgrade sub-skill. Today's only registered route is `(test, 2.17→2.18, compose)` → `/upgrade-test-to-2.18`. Other routes abort cleanly with a "no sub-skill registered" message. Refuses `docker-stack.yml` — use `docker-swarm-migration` first. |
| `upgrade-test-to-2.18` | Sub-skill. Mechanically upgrades a single `Conf-TEST/compose/<country>/docker-compose.yml` from eRegistrations 2.17 to 2.18 (image bumps, minio swap + healthcheck, deprecated env-var removal), commits on a `chore/upgrade-test-<country>-2.18` branch, opens a PR (gh on GitHub origins, manual link on Bitbucket). Invoked by the orchestrator or directly. |

## Related

- TOBE-17731 — Convert all Docker Compose instances to Docker Swarm
- TOBE-17813 — Epic: DevOps skillification (convert recurring ops tasks into Claude skills)
- TOBE-17814 — `upgrade-eregistrations-instance` orchestrator + 2.17 → 2.18 sub-skill MVP
