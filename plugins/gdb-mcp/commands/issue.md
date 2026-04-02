---
description: Report a GDB MCP tool issue or unexpected behavior
argument-hint: [description]
effort: medium
allowed-tools: Read, Write, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *)
---

# MCP Issue

Report an issue with a GDB MCP tool. Invoke the `mcp-issue` skill to guide the user through documenting the problem. The server is **GDB** — pass this context to the skill so it skips server identification.

Arguments: `$ARGUMENTS`

If arguments were provided, treat them as the initial problem description and pass to the skill (skip the "what happened?" question in Step 1).
