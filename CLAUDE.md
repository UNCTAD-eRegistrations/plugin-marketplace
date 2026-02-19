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

### Plugin structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json       # name, version, description, category, dependencies
├── commands/             # slash commands (.md files)
├── agents/               # agent definitions (.md files)
├── skills/               # skill definitions (SKILL.md files)
└── README.md
```

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

| Profile | Country |
|---------|---------|
| `nigeria` | Nigeria |
| `jamaica` | Jamaica |
| `lesotho2` | Lesotho |
| `kenya-test` | Kenya (Test) |
| `investkenya` | Kenya (InvestKenya) |
| `cuba` | Cuba |
| `cuba-test` | Cuba (Test) |
| `elsalvador-dev` | El Salvador (Dev) |
| `colombia-test` | Colombia (Test) |
| `gambia` | Gambia |
| `bhutan-staging` | Bhutan (Staging) |

## Versioning

- Plugin versions in `plugin.json`: `MAJOR.MINOR.PATCH`
- Skill versions in `SKILL.md` metadata: same scheme
- Always add a changelog entry when bumping a skill version

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

See `~/nova/eregistrations/glossary.md` for the full glossary.
