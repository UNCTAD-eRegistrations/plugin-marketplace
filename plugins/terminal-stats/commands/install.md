---
description: Install the LCARS terminal statusline — copies the script and configures Claude Code settings
allowed-tools: [Bash(cp *), Bash(chmod *), Bash(cat *), Bash(mkdir -p *), Read, Edit, Write]
---

# Terminal Stats — Install

Set up the LCARS statusline for Claude Code.

## Instructions

### Step 1 — Copy the statusline script

Symlink the script to `~/.claude/statusline-command.sh` so it stays in sync with plugin updates:

```bash
ln -sf "${CLAUDE_PLUGIN_ROOT}/statusline-command.sh" ~/.claude/statusline-command.sh
```

### Step 2 — Configure the statusline

Read `~/.claude/settings.json`. If it doesn't exist, create it.

Add or update the `statusLine` key at the top level:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  }
}
```

**Important:** Preserve all existing settings — only add/update the `statusLine` key.

### Step 3 — Verify

Check that the script exists and is executable:

```bash
test -x ~/.claude/statusline-command.sh && echo "OK" || echo "FAIL"
```

Check that `settings.json` has the statusLine config:

```bash
cat ~/.claude/settings.json | jq '.statusLine'
```

### Step 4 — Report

```
LCARS Terminal Statusline — Installed
═════════════════════════════════════
  Script:   ~/.claude/statusline-command.sh
  Config:   ~/.claude/settings.json → statusLine

  Restart Claude Code to activate the statusline.
  
  Features: 3-panel display (SYS/CTX/OPS), gradient context bar,
            thermal rate gauge, git info, cache rate, idle timer, cost.
```

If anything failed, report the specific error.

## Usage

```
/terminal-stats:install
```
