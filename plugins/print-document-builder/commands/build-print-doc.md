---
description: Create and manage print documents (certificates, licenses, permits) for BPA services
argument-hint: <service-id> [mcp-server] [--from-template]
allowed-tools: [Read, Write, Bash]
---

# Print Document Builder

Build print documents for BPA service `$ARGUMENTS`.

## Instructions

Parse arguments:
- First token: service ID (required)
- Second token: MCP server name (optional)
- `--from-template`: list available templates and build from selected template

### Flow

1. List existing print documents via `print_document_list`
2. If `--from-template`: show available templates via `print_document_templates`
3. Prompt for document details: name, type (certificate/receipt/permit)
4. Create document via `print_document_create`
5. Add components (header, body fields, footer, signatures) via `print_document_component_add`
6. Review layout and reorder with `print_document_sort` / `print_document_component_move`
7. Show revision history via `print_document_history`

### Editing existing documents
If the service already has print documents, offer to:
- Edit components
- View diff between versions
- Revert to a previous revision via `print_document_revert`

## Usage

```
/build-print-doc 42 BPA-jamaica
/build-print-doc 17 --from-template
/build-print-doc 42 BPA-lesotho2 --from-template
```
