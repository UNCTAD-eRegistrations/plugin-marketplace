# Plugin Marketplace — Claude Code Guidelines

This repository contains Claude Code plugins for the UNCTAD eRegistrations BPA platform.

## Architecture

**Single MCP server, multiple instances.** All BPA tool calls use the `BPA` server with an `instance` parameter:

```
mcp__BPA__service_get(service_id="42", instance="jamaica")
mcp__BPA__field_list(service_id="42", instance="lesotho2", limit=500)
```

Never use the old `mcp__BPA-jamaica__` or `mcp__BPA-lesotho2__` syntax — those are the pre-migration server names and no longer exist.

## Working with Plugins

### Command files (`commands/*.md`)

Frontmatter fields:
- `description` — shown in `/plugin` discovery UI
- `argument-hint` — shown next to the command name, e.g. `<service-id> [instance]`
- `allowed-tools` — comma-separated list, use specific patterns: `Bash(open *)`, `Bash(mkdir -p *)`

Arguments are accessed via `$ARGUMENTS[0]`, `$ARGUMENTS[1]`, etc.

### Skill files (`skills/*/SKILL.md`)

Frontmatter fields:
- `name` — skill identifier
- `description` — used for semantic matching when Claude selects skills
- `allowed-tools` — keep minimal; reference-only skills should use `Read` only
- `metadata.version` — bump on every meaningful change
- `metadata.argument-hint` — e.g. `[service-id] [instance]`
- `metadata.disable-model-invocation` — set `"true"` for skills that spawn subagents

Every skill that interacts with BPA must include a **Connecting to BPA** section:

```markdown
## Connecting to BPA

Before any tool call:
1. If the instance is unknown, call `mcp__BPA__instance_list()` to see registered profiles.
2. Check auth: `mcp__BPA__connection_status(instance="{name}")`.
3. If not authenticated → `mcp__BPA__auth_login(instance="{name}")`, wait for success.

Pass `instance="{name}"` to every `mcp__BPA__*` tool call.
```

### Subagent delegation

Skills that fetch large amounts of BPA data (forms, fields, determinants) **must** delegate to a Task subagent to avoid context saturation. The main skill context handles only: auth, service validation, user prompts, and final delivery.

```
subagent_type: "general-purpose"
```

Do NOT use `TaskCreate`/`TaskUpdate` — these are not Claude Code SDK tools. For progress tracking in batch operations, maintain a local list in the main context.

## Instance Profiles

Live source: `mcp__BPA__instance_list()` — always current, never drifts.

## Versioning

- Plugin versions in `plugin.json`: `MAJOR.MINOR.PATCH`
- Skill versions in `SKILL.md` metadata: same scheme
- Always add a changelog entry when bumping a skill version

## Bundled skill tests

Skills that ship executable helpers in `skills/<skill>/scripts/*.py` also ship tests in
`skills/<skill>/tests/`. CI (`.github/workflows/test-plugin-scripts.yml`) finds every
`plugins/**/tests/` directory holding `test_*.py` and runs each one under `pytest`.

- The scripts are **stdlib-only** — pytest is the only dependency CI installs. Do not add
  a requirements file; fix the script instead.
- Each suite needs its own `tests/conftest.py` putting the sibling `scripts/` directory on
  `sys.path`, so modules import under flat names (`from columns_logic import ...`).
- Run locally before committing:
  `python3 -m pytest plugins/<plugin>/skills/<skill>/tests -q`

## Kimi Code dual format

The repository also ships Kimi Code manifests so the same plugins install in Kimi Code:

- `.kimi-plugin/plugin.json` in each published plugin, plus `kimi-marketplace.json`
  (distributable catalog — sources are per-plugin zip URLs on the rolling `kimi-latest`
  release) and `kimi-marketplace.local.json` (relative sources, for clones) at the root
  are **generated** — never edit them by hand. Re-run
  `python3 scripts/generate-kimi-manifests.py` after changing any
  `.claude-plugin/plugin.json`, `.mcp.json`, or adding/removing `skills/`/`commands/`.
  `--check` verifies they are up to date.
- `.github/workflows/publish-kimi-plugins.yml` rebuilds the `kimi-latest` release zips on
  every push to `main` that touches plugins, so the remote catalog always installs the
  latest published state.
- The generator copies metadata from `.claude-plugin/plugin.json`, converts `.mcp.json`
  to Kimi's `mcpServers` (dropping the Claude-only `"type": "stdio"` and `${VAR}` env
  expansions), and injects a `skillInstructions` block that maps Claude idioms
  (`Task` tool, `TodoWrite`, "restart Claude") to Kimi Code equivalents.
- Exclusions are configured in the generator's `KIMI_EXCLUDED` dict (currently
  `terminal-stats` and `ds-frontend`); `plugins/_drafts/` is never included.
- Skill and command bodies stay Claude-first (e.g. `allowed-tools` frontmatter); Kimi
  ignores what it does not support.

## BPA Terminology

| Term | Meaning |
|------|---------|
| Service | A government procedure (e.g. "Business Registration") |
| Registration | A procedure track within a service |
| Role | A processing step / agency in the workflow |
| Bot | Automated field mapping integration |
| Determinant | Conditional logic that shows/hides form components |
| Classification | Lookup table / dropdown catalog |
| Institution | Government agency assigned to a role |
