---
name: share
description: >
  Publish HTML or Markdown content to share.eregistrations.dev and get a shareable URL.
  Use when the user asks to share, publish, or host a document, report, HTML page, or markdown file.
  Also use when the user says "share this", "publish this", or "put this online".
  Supports listing previously published documents with /share list.
license: UNCTAD-Internal
allowed-tools: Read, Write, Edit, Bash(curl *), Bash(cat *), Bash(ls *)
metadata:
  version: "1.1.0"
  version-date: "2026-04-01"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[list | <file-path>]"
---

# Share — Publish Documents

You publish documents to `share.eregistrations.dev` via its REST API.

## API Base

```
https://share.eregistrations.dev
```

## Authentication — Publisher Token

Before any API call, ensure you have a publisher token:

1. Check if a token file exists at `.share-token` in the project root (same directory as `.git`).
2. If **no token file** exists:
   - Call `POST /api/register` with `{"name": "<project-name>"}` (use the current git repo name or directory name).
   - Save the returned `token` value to `.share-token` in the project root.
   - Add `.share-token` to `.gitignore` if not already there.
3. Read the token from `.share-token`.

**Always send the token** as `Authorization: Bearer <token>` on publish, list, delete, and update calls.

## Commands

### `/share <file-path>` — Publish a file

1. Read the file at the given path.
2. Detect format:
   - `.html` files → format `html`
   - `.md` files → format `md`
   - Other files → ask the user which format to use
3. Use the filename (without extension) as the title, or ask the user.
4. **Show a confirmation summary before publishing:**

   ```
   About to share:
   - Title: <title>
   - Format: <format>
   - Visibility: private (unlisted — accessible only via direct link)
   - Size: <file size in KB>
   - Preview: <first 200 characters of content>...

   Publish this document? (The URL will be accessible to anyone with the link)
   ```

   Wait for the user to confirm. If they say no, stop.

5. Detect metadata from context:
   - **project**: Use the current git repo name or directory name as a project tag (e.g., `tz` for Tanzania, `rw` for Rwanda, `jm` for Jamaica). If unsure, leave empty.
   - **doc_type**: Classify the content: `migration-analysis`, `service-audit`, `debug-report`, `implementation-plan`, `documentation`, `research`, or leave empty.
   - **tags**: Extract 2-3 relevant comma-separated keywords from the content.

6. Call the API:

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat .share-token)" \
  -d '{
    "title": "<title>",
    "format": "<html|md>",
    "content": "<file-contents>",
    "visibility": "private",
    "project": "<project-tag-if-known>",
    "doc_type": "<type-if-known>",
    "tags": "<comma-separated-tags>"
  }'
```

7. Show the user:
   - The shareable URL (from `url` in the response)
   - The management secret (from `secret`) — remind them to save it
   - The document ID

### `/share list` — List your published documents

```bash
curl -s -X GET "https://share.eregistrations.dev/api/me/documents?page=1&limit=20" \
  -H "Authorization: Bearer $(cat .share-token)"
```

Display as a table: title, format, visibility, created date, URL.

### `/share` (no arguments) — Publish from context

If no file path is given:
1. Ask the user: **"What would you like to share?"** Present options:
   - Any HTML or Markdown files generated in this conversation (list them by name)
   - "Or specify a file path"
2. **Do NOT auto-select content.** Wait for the user to explicitly choose.
3. Once the user picks content, ask for a title if one isn't obvious.
4. Show the same confirmation summary as `/share <file-path>` (title, format, visibility, size, preview).
5. Wait for confirmation before publishing.
6. Publish using the same API call as above.

## Important Notes

- **Max content size**: 5 MB
- **Max title length**: 200 characters
- **Formats**: Only `html` and `md` are supported
- **Visibility**: Default is `private` (unlisted — accessible only via direct link). To make a document appear in the public listing, the user must explicitly request `"visibility": "public"`.
- **Rate limit**: 10 publishes per minute per IP. If you get 429, wait and retry.
- The management secret is shown only once at creation. It allows deleting or updating the document without the publisher token.
- The publisher token also allows managing all documents published with it.

## Error Handling

- **401**: Token invalid or expired — delete `.share-token` and re-register.
- **413**: Content too large — inform the user of the 5 MB limit.
- **429**: Rate limited — wait 60 seconds and retry once.
- **422**: Content contains detected secrets (API keys, passwords, private keys) — review and remove sensitive data before sharing.
- **400**: Validation error — check title, format, and content fields.
