---
description: Export BPA service data to structured Excel documentation reports
argument-hint: [service-id] [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# eRegistrations Documentation Exporter

Generate structured Excel reports. `$ARGUMENTS`

## Instructions

Parse arguments: first token is an optional service ID (if omitted, process all services), second is the optional MCP server name.

Follow the `eregistrations-docs` skill in this plugin (`skills/eregistrations-docs/SKILL.md`).

## Requirements

Requires `python3` + `openpyxl` in the environment.

## Usage

```
/eregistrations-docs 42 BPA-jamaica
/eregistrations-docs
```
