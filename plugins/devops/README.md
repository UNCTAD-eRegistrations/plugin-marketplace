# devops

DevOps and deployment skills for eRegistrations infrastructure.

## Skills

| Skill | Description |
|-------|-------------|
| `docker-swarm-migration` | Convert Docker Compose files to Docker Swarm stack format with env var replacement, secrets management, init-secrets.sh generation, reference validation, and dry-run preview |
| `bitbucket-jenkins-to-github-actions` | Migrate a repository from Bitbucket+Jenkins to GitHub+GitHub Actions, including git history, branches, tags, CI/CD pipeline conversion (Jenkinsfile → ci-cd.yml), helm chart updates, branch deletion ruleset, and post-migration validation |
| `upgrade-eregistrations-instance` | Mechanical platform-version upgrade (e.g. 2.17 → 2.18) of a single `Conf-<ENV>/compose/<country>/docker-compose.yml`. Resolves the instance from a natural phrase like "lesotho test" or "kenya live", applies five fixed transformations (image bumps, minio swap, healthcheck rewrite, env-var deletions), then commits and opens a PR (gh on GitHub, manual link on Bitbucket). Strict mode pauses on any anomaly. Refuses `docker-stack.yml` — use `docker-swarm-migration` first. |

## Related

- TOBE-17731 — Convert all Docker Compose instances to Docker Swarm
