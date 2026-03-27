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
  version: "1.0.0"
  version-date: "2026-03-27"
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
4. Call the API:

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat .share-token)" \
  -d '{
    "title": "<title>",
    "format": "<html|md>",
    "content": "<file-contents>",
    "visibility": "public"
  }'
```

5. Show the user:
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
1. Look at the most recent artifact, output, or content you generated in this conversation.
2. If it's HTML or Markdown, offer to publish it.
3. Ask for a title if one isn't obvious from context.
4. Publish using the same API call as above.

## Important Notes

- **Max content size**: 5 MB
- **Max title length**: 200 characters
- **Formats**: Only `html` and `md` are supported
- **Visibility**: Default is `public`. Use `"visibility": "private"` for unlisted documents.
- **Rate limit**: 10 publishes per minute per IP. If you get 429, wait and retry.
- The management secret is shown only once at creation. It allows deleting or updating the document without the publisher token.
- The publisher token also allows managing all documents published with it.

## Error Handling

- **401**: Token invalid or expired — delete `.share-token` and re-register.
- **413**: Content too large — inform the user of the 5 MB limit.
- **429**: Rate limited — wait 60 seconds and retry once.
- **400**: Validation error — check title, format, and content fields.
