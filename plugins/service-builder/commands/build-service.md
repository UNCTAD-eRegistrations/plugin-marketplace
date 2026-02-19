---
description: Design and build a new eRegistrations service interactively
argument-hint: [service-name] [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Service Builder

Build a new eRegistrations service: `$ARGUMENTS`.

## Instructions

Parse arguments:
- First token: service name or description (optional, will prompt if omitted)
- Second token: MCP server name (optional)

### Interactive build flow

Delegate to the `service-architect` agent for complex builds, or follow this flow directly:

1. **Define service**: name, description, short name
2. **Create service**: `service_create`
3. **Design form**: add components (sections, fields, grids) via `form_component_add`
4. **Configure determinants**: add conditional logic via `*determinant_create` tools
5. **Set up roles**: create applicant + processing roles via `role_create`
6. **Add registrations**: create and link registrations via `registration_create` + `serviceregistration_link`
7. **Assign institutions**: link institutions to registrations via `registrationinstitution_create`
8. **Configure costs**: add fixed or formula costs
9. **Add document requirements**: link required documents
10. **Validate**: run `debug_scan` to check for issues
11. **Publish**: activate and publish via `service_activate` + `service_publish`

Ask clarifying questions at each step if requirements are unclear.

## Usage

```
/build-service "Business Registration" BPA-jamaica
/build-service "Import Permit"
```
