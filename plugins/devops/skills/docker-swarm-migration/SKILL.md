---
name: docker-swarm-migration
description: >
  Convert Docker Compose files to Docker Swarm stack format for eRegistrations deployments.
  Use when migrating docker-compose.yml to docker-stack.yml, adding deploy sections,
  configuring overlay networks, or converting environment secrets to Docker Swarm secrets.
license: UNCTAD-Internal
compatibility: Requires access to eRegistrations deployment configuration repositories.
allowed-tools: Read, Write, Edit, Bash(ls *), Bash(cat *), Bash(diff *), Bash(git *)
metadata:
  version: "1.0.0"
  version-date: "2026-03-27"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<path-to-docker-compose.yml>"
  jira: "TOBE-17731"
---

# Convert Docker Compose to Docker Swarm

You will convert a `docker-compose.yml` file into a Docker Swarm `docker-stack.yml` file following the eRegistrations deployment conventions.

## Inputs

- **Compose file path**: `$ARGUMENTS[0]` — path to the `docker-compose.yml` to convert

If no argument is provided, ask the user which file to convert.

## Conversion Checklist

For each conversion, follow these steps in order:

### 1. Read and analyze the source compose file

- Read the `docker-compose.yml`
- Identify all services, volumes, networks, and environment variables
- Note any `depends_on`, `links`, or legacy features

### 2. Create `docker-stack.yml`

Create the Swarm stack file in the **same directory** as the source compose file.

Key transformations:

- **`deploy:` sections**: Add to every service with appropriate:
  - `replicas:` (typically `1` unless the service is stateless and scalable)
  - `placement:` constraints (e.g., `constraints: [node.role == manager]` for DB services)
  - `restart_policy:` (replace `restart:` — Swarm uses `deploy.restart_policy` instead)
  - `resources:` limits/reservations where applicable
- **Networks**: Convert `bridge` networks to `overlay` networks with `attachable: true`
- **Secrets**: Convert sensitive environment variables to Docker Swarm secrets where applicable (database passwords, API keys, etc.)
- **Remove unsupported keys**: `build:`, `container_name:`, `depends_on:`, `links:` are not supported in Swarm mode
- **Version**: Use `version: "3.8"` or later

### 3. Preserve existing patterns

Look for sibling `docker-stack.yml` files in the same environment to match conventions:
- Network naming
- Label patterns
- Volume mount styles
- Secret naming conventions

### 4. Validate

- Ensure all services from the source are present in the output
- Verify no Swarm-incompatible keys remain
- Check that overlay networks are properly defined
- Confirm secrets are declared at both service and top level

### 5. Report

After conversion, present a summary:

```
## Conversion Summary

- **Source**: `{path}/docker-compose.yml`
- **Output**: `{path}/docker-stack.yml`
- **Services converted**: {count}
- **Networks**: {bridge → overlay count}
- **Secrets extracted**: {count}

## Manual Steps Required

1. **Create Docker secrets on the Swarm manager** (if secrets were extracted):
   {for each secret: `docker secret create {secret_name} -` or from file}

2. **Deploy and test on target environment**:
   `docker stack deploy -c docker-stack.yml {stack_name}`

3. **Verify services are running**:
   `docker stack services {stack_name}`

4. **Remove legacy docker-compose.yml** (only after stack is validated and stable)
```

## eRegistrations Conventions

### Standard service labels

```yaml
deploy:
  labels:
    - "traefik.enable=true"
```

### Common placement constraints

| Service type | Constraint |
|-------------|-----------|
| Database (PostgreSQL, MongoDB) | `node.role == manager` |
| Application server | `node.role == worker` (or unconstrained) |
| Reverse proxy / Traefik | `node.role == manager` |

### Overlay network pattern

```yaml
networks:
  app-network:
    driver: overlay
    attachable: true
```

## CRITICAL RULES

- NEVER delete the source `docker-compose.yml` — the user decides when to remove it
- NEVER modify files outside the target directory without asking
- If unsure about a conversion decision, ask the user
- Always read existing `docker-stack.yml` files in the same environment for pattern matching
