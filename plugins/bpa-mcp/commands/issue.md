---
description: Report a BPA MCP tool issue or feature request
argument-hint: [description]
effort: medium
allowed-tools: Read, Write, Bash(mkdir -p *), Bash(grep *), Bash(find *), Bash(cat *), Bash(date *), Bash(gh *), Bash(uvx *), Bash(mcp-eregistrations-bpa *), Bash(mcp-eregistrations-gdb *)
---

# MCP Issue

Report an issue with a BPA MCP tool. Invoke the `mcp-issue` skill to guide the user through documenting the problem. The server is **BPA** — pass this context to the skill so it skips server identification.

Arguments: `$ARGUMENTS`

If arguments were provided, treat them as the initial problem description and pass to the skill (skip the "what happened?" question in Step 1).
