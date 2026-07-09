# DS MCP — Display System

Read-only MCP tools for admin/ops monitoring of eRegistrations Display System — application files, workflows, payments, documents, and system health.

## Prerequisites

Install the **bpa-mcp** plugin first — it provides authentication and instance management that DS depends on.

## Tools (32)

### System & Auth
- `ds_health` — Instance health check (no auth required)
- `ds_auth_login` — Authenticate via Keycloak (shared with BPA)
- `business_entity_list` — List business entities
- `instance_list` — List configured DS instances
- `instance_add` — Register a custom DS instance

### Services
- `service_list` — List published services
- `service_get` — Service detail with properties
- `service_roles` — Workflow roles for a service (from Camunda)

### Files (Application Pipeline)
- `file_list` — List application files with filters (admin)
- `file_get` — File detail
- `file_data_get` — Form submission data
- `file_document_list` — Documents uploaded for a file
- `file_kyc_status` — KYC verification status
- `file_payment_status` — Payment transactions for a file
- `file_process_state` — Current Camunda process variables
- `file_process_history` — Historical Camunda variables

### Processes (Camunda Workflows)
- `process_list` — List processes by service and role
- `process_get` — Process detail with tasks
- `process_task_variables` — Task-level form variables
- `process_history` — Archived process data

### Documents & Certificates
- `document_list` — List uploaded documents
- `certificate_list` — List issued certificates
- `certificate_get` — Certificates for a file or process

### Messages & Alerts
- `message_list_admin` — All user messages (admin)
- `message_get` — Single message detail
- `alert_list_admin` — All user alerts (admin)
- `alert_get` — Single alert detail

### Users
- `user_search` — Search users by name or email

### Payments & Finance
- `payment_provider_list` — Configured payment providers
- `payment_transaction_list` — Payment transactions
- `financial_report_data` — Revenue report data
- `financial_report_export` — Export report as Excel/PDF

## Commands

| Command | Description |
|---------|-------------|
| `/ds-mcp:status [instance]` | Check DS connection status |
| `/ds-mcp:cleanup <instance>` | Wipe ALL applicant files + Camunda processes (super_mario, destructive) |
| `/ds-mcp:repair-rejected <instance> [process_id]` | Heal rejected files wrongly shown as "Validated" in Part A (super_mario, TOBE-17948) |
| `/ds-mcp:issue [description]` | Report a DS MCP tool issue or feature request |

## Compatible Instances

DS MCP works with **v2.x Keycloak-auth** instances only:

| Instance | Version | Environment |
|----------|---------|-------------|
| guatemala-dev | 2.18.x | Dev |
| elsalvador-dev | 2.19.x | Dev |
| jamaica | 2.17.x | Production |
| kenya-test | 2.17.x | Test |
| colombia-test | 2.17.x | Test |
| bhutan-staging | 2.17.x | Staging |

**Not compatible:** Lesotho, Gambia, Nigeria (v1.x), Cuba (CAS auth).

## Auth

Login once via BPA — DS tools work automatically via shared OS keyring.

```
/bpa-mcp:login jamaica
```

Or authenticate directly:

```
ds_auth_login(username="user", password="pass", instance="jamaica")
```

## Admin Required

All DS tools require `is_staff` or `is_superuser`. Financial reports additionally require a Camunda role with `allowAccessToFinancialReports=True`.
