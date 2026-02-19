---
name: print-document-design
description: >
  Expert guidance on designing BPA print documents: certificates, licenses, permits,
  receipts, and official correspondence. Use when creating a new print document for a
  BPA service, adding components to a certificate, ordering document sections, working
  with print document templates, or reverting to a previous document version.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server.
allowed-tools: Read Write Bash
metadata:
  version: "1.0.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# Print Document Design Skill

Best practices for creating official government print documents in BPA.

## Document Types

| Type | Purpose | Key Components |
|------|---------|----------------|
| Certificate | Official approval/certification | Header, seal, applicant details, validity dates, signature |
| License | Authorization to operate | Header, license number, permitted activities, conditions, expiry |
| Permit | One-time authorization | Header, permit number, specific activity, validity period |
| Receipt | Payment acknowledgment | Reference number, payment details, date, amount |
| Acknowledgment | Submission confirmation | Reference number, submission date, next steps |

## Standard Component Order

1. **Header** — Institution name, logo, document title
2. **Reference block** — Document number, issue date, reference number
3. **Applicant block** — Name, ID, address
4. **Subject block** — What is being certified/authorized
5. **Conditions block** — Any attached conditions or restrictions
6. **Validity block** — Valid from/until dates
7. **Signature block** — Authorized officer, title, date, signature line
8. **Footer** — QR code (if applicable), verification URL, page number

## Field Mapping Tips

- Map `applicationDate` → issue date
- Map `applicantName` + `applicantId` → identification block
- Map `registrationNumber` → the document's official reference number
- Always include a unique document number for traceability

## Versioning

Print documents support revisions. After any significant change:
1. The previous version is automatically saved in history
2. Use `print_document_history` to view all versions
3. Use `print_document_revert` to roll back if the new version has issues
4. Always test the document by reviewing component structure before publishing

## Changelog

- 1.0.0 (2026-02-19) tf-tools — Initial skill
