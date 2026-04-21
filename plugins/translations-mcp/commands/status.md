---
description: Check whether an eRegistrations instance is in sync with the Global Translation Service
effort: low
allowed-tools: [mcp__Translations__translation_global_status, mcp__BPA__instance_list, mcp__BPA__auth_login]
---

# Translations Status

Report whether a country instance is in sync with the Global Translation Service — i.e. whether the admin UI will show real labels instead of raw translation keys like `nav.services`.

Arguments: `$ARGUMENTS`

## Instructions

1. If an instance was specified (e.g. `/translations-mcp:status jamaica`), check that one. Otherwise call `instance_list()` (from bpa-mcp) to get all instances, then loop.

2. For each instance, call `translation_global_status(instance="<name>")`.
   - If auth fails, call `auth_login(instance="<name>")` then retry.
   - If the BPA endpoint is unreachable, report the error and move on.

3. Present results as a table:

| Instance | Reload needed? | Cache size | Missing keys | Recommendation |
|----------|----------------|------------|--------------|----------------|

4. For any instance where `reload_recommended=true`, surface the one-line suggestion:
   > Run `/translations-mcp:fix <instance>` to pull from the Global Translation Service.

## Usage

```
/translations-mcp:status              # check all instances
/translations-mcp:status jamaica      # check a specific instance
/translations-mcp:status lesotho2 fr  # check a specific language
```

## Notes

- `translation_global_status` is read-only. It does not modify the instance.
- A failed probe (e.g. one or two missing keys) does not mean the instance is broken — it means the Global Translation bootstrap has never run for the current BPA version. See `/translations-mcp:fix`.
