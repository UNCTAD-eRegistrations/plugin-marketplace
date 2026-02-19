---
description: Generate a citizen-facing HTML user manual for a BPA service
argument-hint: <service-id> [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Service Manual Generator

Generate a complete citizen-facing HTML user manual for BPA service `$ARGUMENTS`.

## Instructions

Parse arguments: first token is the service ID, second (optional) is the MCP server name (default: use whichever BPA server is already authenticated).

Follow the `service-manual` skill in this plugin (`skills/service-manual/SKILL.md`).

## Usage

```
/service-manual 42 BPA-jamaica
/service-manual 17
```
