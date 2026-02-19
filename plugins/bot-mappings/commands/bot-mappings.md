---
description: Create, configure, and manage BPA bot integrations and field mappings
argument-hint: <service-id> [instance] [--suggest]
allowed-tools: [Read, Write, Bash]
---

# Bot Mappings Manager

Configure bot integrations for BPA service `$ARGUMENTS`.

## Instructions

Parse arguments:
- First token: service ID (required)
- Second token: instance profile name (optional)
- `--suggest`: auto-suggest mappings using AI (min_confidence=0.3)

### Execution flow

1. List existing bots with `bot_list`
2. For each bot, get mapping summary via `bot_mapping_summary`
3. Identify unmapped or low-confidence mappings
4. If `--suggest`: run `bot_suggest_mappings` and present suggestions for review
5. Present a summary table: bot name, mapped inputs, unmapped inputs, mapped outputs, unmapped outputs
6. Offer to apply suggestions or create specific mappings

### Validation
After any mapping changes, run `bot_validate` to confirm configuration integrity.

## Usage

```
/bot-mappings 42 jamaica
/bot-mappings 17 --suggest
/bot-mappings 42 lesotho2 --suggest
```
