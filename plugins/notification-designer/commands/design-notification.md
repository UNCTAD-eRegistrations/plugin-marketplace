---
description: Design or update notification templates for a BPA service
argument-hint: <service-id> [mcp-server] [--type email|sms|push]
allowed-tools: [Read, Write, Bash]
---

# Notification Designer

Design notifications for BPA service `$ARGUMENTS`.

## Arguments

- First: service ID (required)
- Second: MCP server (optional)
- `--type email|sms|push`: filter to one channel (default: show all)

## Flow

### Step 1: Audit existing notifications
- List messages: `message_list`
- List notifications: `notification_list`
- Show table: trigger event → channel → message template → status

### Step 2: Identify gaps
Compare expected notification points against what exists:
| Event | Expected | Status |
|-------|----------|--------|
| Application submitted | Email to applicant | ✅ / ❌ |
| Application under review | Email to applicant | ✅ / ❌ |
| More info requested | Email + SMS to applicant | ✅ / ❌ |
| Application approved | Email + SMS to applicant | ✅ / ❌ |
| Application rejected | Email to applicant | ✅ / ❌ |
| Certificate ready | Email + SMS to applicant | ✅ / ❌ |

### Step 3: Create or update templates
For each missing notification:
1. Draft message content using the `notification-templates` skill
2. Show draft to user for review
3. Create message: `message_create` (subject, body with `{{variables}}`)
4. Create notification trigger: `notification_create` (event, role, message_id)

## Usage

```
/design-notification 42 BPA-jamaica
/design-notification 17 --type sms
```
