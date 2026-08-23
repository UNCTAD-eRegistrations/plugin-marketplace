---
name: feedback-bot-naming-convention
description: BPA bot names follow NAMEOFGDB (uppercase) + action and qualifiers (lowercase). Apply to every bot created via MCP.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2433006f-d744-406c-bedd-d45653c4e80f
---

BPA bot names use a fixed pattern: **GDB name in uppercase + everything else in lowercase**. The GDB name is the all-caps token at the front (e.g. `CERTIFICADOS`, `DOCUMENTOS`, `PERMISOSTODOS`); the action verb and any qualifier (which document type, which operation) are in lowercase.

Examples:
- `CERTIFICADOS crear` (correct)
- `DOCUMENTOS licencia crear` (correct — qualifier "licencia" lowercase)
- `DOCUMENTOS resolución crear` (correct)
- `DOCUMENTOS Licencia crear` (wrong — qualifier capitalized)
- `DOCUMENTOS LICENCIA CREAR` (wrong — action and qualifier capitalized)

**Why:** Designers scan bot lists looking for the GDB name as the entry point; uppercase makes the GDB-name token unmistakable, lowercase action+qualifiers reads as ordinary prose. Frank flagged the all-caps name "DOCUMENTOS LICENCIA CREAR - DATA BOT" rendered in the BPA UI on 2026-05-29; the standard Cuba bot roster already follows the GDB-uppercase + verb-lowercase pattern (`CERTIFICADOS crear`, `PERMISOSTODOS crear`).

**How to apply:** Whenever calling `bot_create` or `bot_update` with a `name`, capitalize only the GDB name token at the front; lowercase everything else, even nouns like document types ("licencia", "resolución", "factura"). Apply the same shape to `short_name`. Audit existing bot names you touch and rename if they violate the pattern.
