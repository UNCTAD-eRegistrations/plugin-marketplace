---
name: classification-design
description: >
  Expert guidance on designing and managing BPA classification catalogs (lookup tables,
  country codes, document type lists, business sector codes). Use when the user is creating
  a new classification catalog, adding entries to a catalog, applying country codes,
  managing dropdown options in forms, or exporting catalog data.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server.
allowed-tools: Read Write Bash
metadata:
  version: "1.0.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# Classification Design Skill

Best practices for BPA classification catalogs.

## When Classifications Are Needed

Use a classification (catalog) whenever a form field offers a list of options that:
- Has more than 5 options (use select + classification instead of hardcoded options)
- May change over time (adding new countries, sectors, document types)
- Is shared across multiple services (define once, reuse)
- Maps to an international standard (ISO, UN codes)

## Standard Catalog Types

| Catalog Name | Purpose | Standard |
|-------------|---------|----------|
| `country-codes` | ISO country list | ISO 3166-1 alpha-2/3 |
| `currency-codes` | Currency list | ISO 4217 |
| `document-types` | Accepted ID documents | National |
| `business-sectors` | ISIC activity codes | ISIC Rev. 4 |
| `port-codes` | Port/entry point codes | UN/LOCODE |
| `hs-codes` | Harmonized tariff codes | WCO HS 2022 |
| `license-types` | Types of licenses issued | National |

## Naming Convention

- Catalog name: lowercase, hyphens, descriptive: `business-activity-codes`
- Entry keys: uppercase for codes (`JM`, `LS`), lowercase for IDs
- Entry labels: human-readable, in the deployment language

## Country Codes Pattern

Always apply ISO country codes using `mcp__BPA__classification_apply_country_codes` rather than manually entering them. This ensures:
- Correct ISO 3166-1 alpha-2 codes
- Consistent labeling
- All 249 countries/territories included

```
mcp__BPA__classification_apply_country_codes(classification_id=<id>, instance="<instance>")
```

## Changelog

- 1.0.0 (2026-02-19) tf-tools — Initial skill
