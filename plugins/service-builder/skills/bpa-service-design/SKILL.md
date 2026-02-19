---
name: bpa-service-design
description: >
  Expert patterns and best practices for designing eRegistrations BPA services, forms,
  determinant logic, roles, and registration workflows. Use when the user is building a
  new BPA service, designing form components, configuring conditional logic (determinants),
  setting up processing roles, creating registrations, or asking how to structure a
  government procedure in eRegistrations.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server.
allowed-tools: Read Write Bash
metadata:
  version: "1.0.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# BPA Service Design Skill

Expert knowledge for designing well-structured eRegistrations services.

## Form Design Patterns

### Section Hierarchy
```
Service
└── Form
    ├── Section: Applicant Information
    │   ├── Field: applicantType (select → triggers determinants)
    │   ├── Field: fullName
    │   ├── Field: nationalId
    │   └── Grid: addresses (repeating)
    ├── Section: Activity Details (conditional on applicantType)
    │   ├── Field: activityDescription
    │   └── Field: estimatedValue
    └── Section: Declarations
        └── Field: declarationAccepted (boolean)
```

### Field Naming Convention
- Use camelCase: `applicantName`, `businessRegistrationNumber`
- Be descriptive: prefer `companyLegalName` over `name`
- Boolean fields: `isLicensed`, `hasExistingPermit`
- Date fields: `applicationDate`, `licenseExpiryDate`

### Determinant Best Practices
- **One condition → one determinant**: don't combine multiple conditions in one
- **Use `selectdeterminant`** for dropdown-based conditions (most common)
- **Use `booleandeterminant`** for yes/no toggles
- **Cascade**: show Section B only if Field A = "Company", then show Field C only if Field B = "Manufacturing"
- **Never hide required fields**: make a field optional before hiding it

### Role Design Patterns
```
Applicant (UserRole)
  └── Submits application → Submitted status

Reviewer (ProcessingRole - Department A)
  ├── Under Review status
  ├── Request More Info → Incomplete status (returns to Applicant)
  └── Forward → Department B

Approver (ProcessingRole - Department B)
  ├── Approved → generates print document
  └── Rejected → notifies Applicant
```

### Registration Tracks
- One registration per distinct procedure track
- Example: "New License" and "License Renewal" = two separate registrations
- Link both to the same service if they share the same form

## Common Mistakes to Avoid

1. **Over-sectioning**: don't create a section for every 2-3 fields
2. **Missing applicantType determinant**: always make the first select field drive the rest
3. **All roles assigned to same institution**: each role should have appropriate institution
4. **No cost configured**: even free services should have a cost of 0 (for audit trail)
5. **Publishing before debug scan**: always `debug_scan` before publishing

## Changelog

- 1.0.0 (2026-02-19) tf-tools — Initial skill
