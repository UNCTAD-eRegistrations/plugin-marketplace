# service-design

Skills for designing and extending eRegistrations BPA services. Each skill encodes a proven cross-repo (BPA-backend + MCP-eRegistrations) implementation pattern extracted from a working diff, with explicit rationalization counters captured from baseline subagent testing.

## Bundled skills

| Skill | What it does | Extracted from |
|-------|--------------|----------------|
| `bpa-add-history-endpoint` | Add Hibernate Envers-backed revision history (3 REST endpoints + 2 MCP tools) for any `@Audited` BPA resource — Bot, Cost, Notification, Classification, Determinant, Form, etc. Mirrors the pattern shipped for Message in v1.33.0. | [MCP-eRegistrations#105](https://github.com/UNCTAD-eRegistrations/MCP_eRegistrations/issues/105) |

## Why this plugin exists

Several BPA features ship as cross-repo PRs (backend Java + MCP Python + manual deploy + live verification). The mechanical parts of these workflows can be encoded as skills so future feature additions take 30 minutes instead of 4 hours, and don't repeat the same mistakes (e.g., missing `mvn spotless:check` before pushing → broken `develop` CI).

Each skill in this plugin includes:
- Prerequisite check (does the resource entity have `@Audited`? does the audit table exist at runtime?)
- Backend code template (controller endpoints + tests)
- MCP code template (tools + tests)
- **Mandatory quality gates with explicit rationalization counters** (the trap that's already cost ~30 min of CI debugging)
- Live verification probe sequence

## Requirements

- Local checkouts of:
  - `~/PROJECTS/00-eRegistrations-Next/BPA-backend`
  - `~/PROJECTS/software-factory/MCP_eRegistrations_BPA`
- `mvn` 3.9+, JDK 22, `gh` CLI authenticated for `UNCTAD-eRegistrations`
- `bpa-mcp` plugin installed (skills dispatch BPA tools for live verification)
