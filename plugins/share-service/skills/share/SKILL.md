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
  version: "1.3.0"
  version-date: "2026-06-14"
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

The publisher token is **per user, not per project**. It lives in the user's home directory so the same token is reused across every repository on this machine.

Before any API call, ensure you have a publisher token:

1. Check if a token file exists at `~/.share-token` (resolve `~` to `$HOME`).
2. **Migration (one-time)**: if `~/.share-token` is missing but a legacy `.share-token` file exists in the current git root, move it: `mv "<git-root>/.share-token" ~/.share-token && chmod 600 ~/.share-token`. Also remove the legacy entry from the repo's `.gitignore` if it's still listed there.
3. If **no token file** exists in either place:
   - Call `POST /api/register` with `{"name": "<machine-or-user-name>"}` (e.g. `$(whoami)@$(hostname -s)`, or whatever short identifier makes sense).
   - Save the returned `token` value to `~/.share-token`.
   - `chmod 600 ~/.share-token` so other local users cannot read it.
4. Read the token from `~/.share-token`.

**Always send the token** as `Authorization: Bearer <token>` on publish, list, delete, and update calls.

> Note: there is no need to gitignore `~/.share-token` — it is outside every repository.

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
  -H "Authorization: Bearer $(cat ~/.share-token)" \
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

#### Custom slug — choose a readable URL

By default the document gets a random 10-character id and a URL like `/d/a1b2c3d4e5`. The user can instead request a **custom slug** to get a memorable URL such as `/d/tz-migration-report`.

- Pass an optional `slug` field in the JSON body (or a `slug` form field for `POST /upload`).
- When a slug is given, the document id **is** the slug and the URL becomes `<base>/d/<slug>`. The create response is `201` with `{id, url, secret, visibility, created_at}` as usual.
- **Slug rules** (validated server-side):
  - Must match `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` — lowercase letters, digits, and internal hyphens only (no leading/trailing hyphen).
  - Length **3–64** characters.
  - Must **not** be a reserved word: `raw`, `api`, `static`, `upload`, `d`, `health`, `me`, `documents`, `register`, `index`.
  - Must **not** look like a random id (rejects the 10-char nanoid shape `^[a-z0-9]{10}$`).
  - An invalid slug returns `400 invalid slug: <reason>`.
- If the slug is **already in use**, the API returns `409 URL already in use` — pick another slug.
- The `slug` field is **optional**. Omitting it preserves today's behavior exactly: a random 10-char id is generated.

#### Update in place — overwrite an existing document

To replace the content of an already-published document **at the same URL** (instead of creating a new one), POST again with `short_code` plus the document's `secret`:

- Send `short_code` set to the document's id-or-slug, and either the management secret (`sk_...`) or the publisher Bearer token, to `POST /api/documents` (or `POST /upload`). On `POST /api/documents` the JSON field is named `secret`; on the `POST /upload` form the field is named `management_secret`.
- **Overwrites**: `title`, `content`, `format`, `visibility`.
- **Preserves**: `created_at`, `project`, `doc_type`, `agent_session`, `tags`, `pinned` (and the publisher).
- Returns `200` with `{id, url, visibility, created_at, updated_at}`. The URL is unchanged; only the content is replaced.
- **Cannot combine `slug` with `short_code`** — doing so returns `400 cannot use slug with short_code`. Use `slug` to create a new document; use `short_code` to update an existing one.
- Other errors: `401` if neither `secret` nor a publisher Bearer token is supplied, `403` if the caller doesn't own the document, `404` if `short_code` matches no document.

### `/share list` — List your published documents

```bash
curl -s -X GET "https://share.eregistrations.dev/api/me/documents?page=1&limit=20" \
  -H "Authorization: Bearer $(cat ~/.share-token)"
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

## Deleting a document

To delete a published document, use either the document id or its slug:

- `DELETE /api/documents/{id}` with the publisher `Authorization: Bearer <token>`.
- Or the thin alias `DELETE /d/{code}` with header `X-Management-Secret: <sk_...>` (where `{code}` is the id or slug). This is equivalent to `DELETE /api/documents/{id}` and is handy when the user only kept the management secret.

## Examples

### Create with a custom slug

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{
    "title": "Tanzania Migration Report",
    "format": "md",
    "content": "# Migration Report\n...",
    "visibility": "private",
    "slug": "tz-migration-report"
  }'
# -> 201 {"id":"tz-migration-report","url":".../d/tz-migration-report","secret":"sk_...","visibility":"private","created_at":"..."}
```

### Update an existing document in place

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{
    "short_code": "tz-migration-report",
    "secret": "sk_...",
    "title": "Tanzania Migration Report (v2)",
    "format": "md",
    "content": "# Migration Report — updated\n...",
    "visibility": "public"
  }'
# -> 200 {"id":"tz-migration-report","url":".../d/tz-migration-report","visibility":"public","created_at":"...","updated_at":"..."}
```

## Important Notes

- **Max content size**: 5 MB
- **Max title length**: 200 characters
- **Formats**: Only `html` and `md` are supported
- **Visibility**: Default is `private` (unlisted — accessible only via direct link). To make a document appear in the public listing, the user must explicitly request `"visibility": "public"`.
- **Rate limit**: 10 publishes per minute per IP. If you get 429, wait and retry.
- The management secret is shown only once at creation. It allows deleting or updating the document without the publisher token.
- The publisher token also allows managing all documents published with it.
- **Custom slugs**: optionally pass `slug` on create to get a readable `/d/<slug>` URL. Omitting it keeps the default random id. See [Custom slug](#custom-slug--choose-a-readable-url).
- **Update in place**: re-POST with `short_code` + the management secret (JSON field `secret`, or form field `management_secret` on `/upload`) — or the publisher token — to overwrite an existing document at the same URL. See [Update in place](#update-in-place--overwrite-an-existing-document).

## Error Handling

- **401**: Token invalid or expired — delete `~/.share-token` and re-register.
- **413**: Content too large — inform the user of the 5 MB limit.
- **429**: Rate limited — wait 60 seconds and retry once.
- **422**: Content contains detected secrets (API keys, passwords, private keys) — review and remove sensitive data before sharing.
- **400**: Validation error — check title, format, and content fields. Also returned for an invalid slug (`invalid slug: <reason>`) or when `slug` is combined with `short_code` (`cannot use slug with short_code`).
- **403**: On an update-in-place, the caller doesn't own the document — use the correct `secret` or publisher token.
- **404**: On an update-in-place, `short_code` matches no existing document.
- **409**: The requested slug is already in use (`URL already in use`) — choose a different slug.
