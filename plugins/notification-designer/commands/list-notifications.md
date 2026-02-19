---
description: List all notification templates and triggers for a BPA service
argument-hint: <service-id> [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Notification List

List notifications for service `$ARGUMENTS`.

## Instructions

1. Call `message_list` to get all message templates
2. Call `notification_list` to get all triggers
3. Display as a structured table grouped by trigger event

```
Service: Business Registration (ID: 42)

SUBMISSION
  Event: on_submit
  → Email to applicant: "Your application has been received"
  → SMS to applicant: "Application #{{ref}} received. Check status at {{portal_url}}"

APPROVAL
  Event: on_approve
  → Email to applicant: "Your certificate is ready"
  → (SMS: ❌ not configured)

REJECTION
  Event: on_reject
  → (Email: ❌ not configured)
```

Flag missing notifications as ❌ (run `/design-notification` to add them).

## Usage

```
/list-notifications 42 BPA-jamaica
```
