---
description: Fetch cas + partc schema dumps from a country's source Postgres host via ssh, ready for the CAS→Keycloak migration pipeline.
argument-hint: "[country]"
allowed-tools: Skill, Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
---

Invoke the `cas-to-keycloak` skill in **fetch** mode.

Use the Skill tool with:
- skill: "cas-to-keycloak"
- args: "fetch $ARGUMENTS" (country name, e.g. `cuba`; skill prompts if omitted)

The skill will:
1. Locate the country's eRegistrations config repo under `/home/jenkins` or `/opt`.
2. Stage the vendored `dump-keycloak-local/` tooling into `<repo>/sql/`.
3. Prompt for the source-Postgres ssh host + DB name.
4. Run `ssh <host> 'sudo -u postgres pg_dump -n cas | xz' > sql/cas.sql` and the partc equivalent.
5. Report dump sizes and user-row sanity counts.

Operator runs `/devops:cas-to-keycloak-seed <country>` next to produce the realm import.
