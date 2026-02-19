---
name: data-import-patterns
description: >
  Patterns and validation rules for importing bulk data into BPA (classifications,
  document requirements, costs). Use when reading CSV or Excel files for BPA import,
  validating import file structure, handling import errors gracefully, or designing
  data templates for country teams to fill in.
license: UNCTAD-Internal
compatibility: Requires python3 + openpyxl for Excel files. CSV files need no extra dependencies.
allowed-tools: Read Write Bash
metadata:
  version: "1.0.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# Data Import Patterns Skill

Conventions and validation rules for BPA bulk data import.

## File Reading Strategy

```python
# CSV
import csv
with open(file_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Excel (requires openpyxl)
import openpyxl
wb = openpyxl.load_workbook(file_path)
ws = wb.active
headers = [cell.value for cell in ws[1]]
rows = [dict(zip(headers, [c.value for c in row])) for row in ws.iter_rows(min_row=2)]
```

## Validation Rules

Before importing any row:
1. Required fields are present and non-empty
2. Numeric fields are valid numbers (not strings)
3. Boolean fields accept: `true/false`, `yes/no`, `1/0`, `True/False`
4. No leading/trailing whitespace in codes or keys
5. Codes are unique within the file (warn on duplicates)

## Error Report Format

Always produce an import report:
```
Import Report: countries.csv → "Country Codes" catalog (BPA-jamaica)
────────────────────────────────────────────────────────────
Total rows:        249
Successfully imported: 247
Skipped (duplicate): 2   [KE line 45, KE line 201]
Errors:            0

Duration: 4.2s
```

## Idempotency

All import commands should be safe to run twice:
- Check for existing entries before creating
- Skip duplicates with a warning rather than erroring
- Never delete existing data unless explicitly asked

## Template Files

Provide downloadable templates when users need to fill in data:

**classifications-template.csv:**
```
code,label,description
```

**requirements-template.csv:**
```
registration_name,document_name,description,mandatory,original_required
```

**costs-template.csv:**
```
registration_name,cost_name,type,amount,currency,formula
```

## Changelog

- 1.0.0 (2026-02-19) tf-tools — Initial data import patterns skill
