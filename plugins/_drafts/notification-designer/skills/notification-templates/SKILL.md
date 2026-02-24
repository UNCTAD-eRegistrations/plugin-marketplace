---
name: notification-templates
description: >
  Templates and best practices for writing BPA service notification messages (email, SMS, push).
  Use when creating or editing notification message templates for status changes in BPA
  registration workflows, writing applicant-facing email bodies, composing SMS notifications,
  or choosing which events should trigger notifications.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server.
allowed-tools: Read
metadata:
  version: "1.1.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# Notification Templates Skill

Guidance for writing effective BPA notification messages.

## Connecting to BPA

Before any tool call:
1. If the instance is unknown, call `mcp__BPA__instance_list()` to see registered profiles.
2. Check auth: `mcp__BPA__connection_status(instance="{name}")`.
3. If not authenticated → `mcp__BPA__auth_login(instance="{name}")`, wait for success.

Pass `instance="{name}"` to every `mcp__BPA__*` tool call.

## Creating Notifications

```
# List existing notifications for a service
mcp__BPA__message_list(instance="{instance}", service_id="{service_id}")

# Create a new notification message
mcp__BPA__message_create(instance="{instance}", service_id="{service_id}",
  name="...", subject="...", body="...")

# Update an existing message
mcp__BPA__message_update(instance="{instance}", message_id="{id}",
  subject="...", body="...")

# Check the notification rules (which events trigger which messages)
mcp__BPA__notification_list(instance="{instance}", service_id="{service_id}")
```

Always check `mcp__BPA__message_list` before creating — avoid duplicates.

## When to Notify

| Event | Channels | Priority |
|-------|----------|----------|
| Application submitted | Email | High — confirm receipt |
| Application under review | Email | Medium — set expectations |
| More info requested | Email + SMS | High — requires action |
| Application approved | Email + SMS | High — good news |
| Application rejected | Email | High — explain reason |
| Certificate ready for download | Email + SMS | High |
| Payment due | Email + SMS | High |

## Available Template Variables

BPA message templates support `{{variable}}` interpolation:

| Variable | Description |
|----------|-------------|
| `{{applicant_name}}` | Full name of the applicant |
| `{{reference_number}}` | Application reference number |
| `{{service_name}}` | Name of the service |
| `{{submission_date}}` | Date application was submitted |
| `{{portal_url}}` | URL to the citizen portal |
| `{{status}}` | Current application status |
| `{{rejection_reason}}` | Reason for rejection (on_reject only) |
| `{{reviewer_name}}` | Name of the reviewing officer |

## Email Template Structure

```
Subject: [{{service_name}}] Your application status: {{status}}

Dear {{applicant_name}},

[OPENING — one sentence stating what happened]

[BODY — 2-3 sentences with relevant details, next steps]

[ACTION — clear call to action with link if applicable]

Reference: {{reference_number}}
Submitted: {{submission_date}}

[Institution name]
[Portal URL]
```

## SMS Template Guidelines

- Maximum 160 characters per message
- Include reference number and portal URL
- No HTML
- Example: `Your application {{reference_number}} has been approved. Download your certificate at {{portal_url}}`

## Tone Guidelines

- **Formal but accessible** — government authority without bureaucratic language
- **Action-oriented** — always tell the applicant what to do next
- **Multilingual** — if the deployment serves multiple languages, create one message per language

## Changelog

- 1.1.0 (2026-02-19) tf-tools — Add Connecting to BPA section, tool call examples, allowed-tools narrowed to Read
- 1.0.0 (2026-02-19) tf-tools — Initial notification templates skill
