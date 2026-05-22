---
description: Load a seeded `sql/keycloak.sql` onto the target eRegistrations deploy host, restart Keycloak, wait for health. Semi-automated step 3 of the CAS→Keycloak pipeline.
argument-hint: "[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak` skill in **deploy** mode.

Use the Skill tool with:
- skill: "cas-to-keycloak"
- args: "deploy $ARGUMENTS" (country name, e.g. `cuba`)

The skill will:
1. Locate the country's eRegistrations config repo and confirm `sql/keycloak.sql` exists (offer to run seed first if not).
2. Prompt for ssh host + deployment shape (compose vs swarm). Optional overrides: `KC_DB_NAME`, `KC_DB_USER`, `KC_COMPOSE_DIR` / `KC_SWARM_STACK`, `KC_HEALTH_URL`.
3. Confirm the destructive load (`--clean --if-exists` drops the existing Keycloak DB).
4. Execute `dump-keycloak-local/deploy-keycloak-dump.sh` — scp's the dump, runs `sudo -u postgres psql -f` on it, restarts Keycloak (`docker compose restart keycloak` or `docker service update --force`), polls `KC_HEALTH_URL` for up to 180 s.
5. Reports the load + restart + health-probe outcome.

`DRY_RUN=1` previews the commands without mutating the host.

Never reads `.env` on the deploy host — DB / OAuth secrets must already be in place out-of-band.

Operator runs `/devops:cas-to-keycloak-backfill <country>` next as a final sanity-pass.
