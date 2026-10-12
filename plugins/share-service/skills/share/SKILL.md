---
name: share
description: >
  Publish HTML or Markdown content to share.eregistrations.dev and get a shareable URL.
  Use when the user asks to share, publish, or host a document, report, HTML page, or markdown file.
  Also use when the user says "share this", "publish this", or "put this online".
  Supports listing previously published documents with /share list.
  Choose a sharing mode: public, anyone-with-the-link, password-protected, or owner-only.
  A document filed under a project can get a short project address, such as /comores/documents.
license: UNCTAD-Internal
allowed-tools: Read, Write, Edit, Bash(curl *), Bash(cat *), Bash(ls *)
metadata:
  version: "1.6.0"
  version-date: "2026-10-12"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[list | <file-path>]"
  changelog:
    - "1.6.0 (2026-10-12): Project addresses. New 'Project addresses' section. /{project}/{name} serves the document '{project}-{name}' filed under {project}. /{project}/ is a project page. It lists public documents and password documents (title and lock only). Label rules and label discipline: list the user's documents and reuse the label that exists. Ask the user when two labels exist for one country. Step 5 requires a label that gets an address. Step 7, the custom slug section and /share list show project_url when the response has it, else url. New PATCH example that sets 'project', and the 400 text for an invalid project. Sharing Modes table names the project page. Important Notes: scripts in a markdown document do not run, so publish interactive pages as html."
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

## Sharing Modes

Every document has exactly one sharing mode, set with `share_mode` on create or update.

| `share_mode` | Listed on the home page? | Listed on the project page? | Who can read it |
|---|---|---|---|
| `public` | yes | yes | anyone |
| `link` | no | no | anyone holding the URL |
| `password` | no | title only, with a lock | anyone holding the URL **and** the password |
| `owner` | no | no | the publisher token, the management secret, or any share-service admin |

The project page is `/{project}/`. See [Project addresses](#project-addresses).

**`link` is the default** when `share_mode` is omitted. It matches what people
expect from a shared link, and it is what the retired `"visibility": "private"`
always meant.

**`password` requires a `password` field** of at least 6 characters. The reader opens
the URL, gets a prompt, enters the password once, and stays unlocked on that browser
for 12 hours. Two things to tell the user:

- Send the password **separately from the link** — not in the same message.
- The **title is still visible** without the password, because the prompt has to name
  the document. The project page also shows the title. If the title itself is
  sensitive, use `owner` instead.
- Changing the password **logs out every reader** who had unlocked it.

**`owner` is not shareable, but it is not private from admins.** It returns `404` to
anyone who sends neither the publisher token nor the management secret, and a browser
cannot send either by clicking a link — so a colleague you send the URL to gets a 404.
**A logged-in share-service admin can still read it from a plain browser click**, since
an admin session overrides per-document access. Use `owner` for your own reference
material; do not treat it as private from the people who run the service.

### `visibility` is retired on writes

**Never send `visibility` on a publish or update.** All three write endpoints
reject it:

```
400 'visibility' is no longer accepted on writes — use 'share_mode': public, link, password or owner
```

It is still **reported** in every response: `public` when the document is on the
home page, `private` otherwise. You can read it, but never write it. Use `share_mode` for
anything that changes sharing, including unlisting: `{"share_mode":"link"}`, not
`{"visibility":"private"}`.

The reason matters if you are tempted to work around it. A two-valued flag cannot
express four modes, and every attempt to map it produced a case where a caller
asked for protection, did not get it, and saw a `200`. The field is refused rather
than translated so that cannot recur.

Omitting `share_mode` on a publish defaults to `link`.

## Project addresses

A document gets a short project address, `/{project}/{name}`, when two things are true:

1. Its ID is `{project}-{name}`. The ID is the `slug` that you send on create.
2. Its `project` label is exactly `{project}`.

For example, to get `https://share.eregistrations.dev/comores/documents`, publish with
`"project": "comores"` and `"slug": "comores-documents"`. The old address
`/d/comores-documents` also works. Every old `/d/{id}` link keeps working.

The project address uses the same sharing mode as `/d/{id}`. A password prompt on the
project address sends the reader back to it after the unlock. If the label or the ID
does not match, the project address gives the same 404 as an unknown document.

### Project page

`/{project}/` is the project page. It lists the `public` and `password` documents
that have the label `{project}`. A document does not need a project address to be on it.

- A `password` document shows a lock and its title only. Its content stays behind the prompt.
- The project page does not list `link` or `owner` documents.
- Like the home page, it does not list unpinned documents that are older than 90 days.
- The home page does not change. It lists `public` documents only.
- A project with no listed documents gives 404.

### Label rules

A label gets a project address and a project page only when all of these are true:

- It contains only lowercase letters, digits and hyphens.
- It does not start or end with a hyphen.
- It is not a reserved name: `admin`, `login`, `logout`, `raw`, `api`, `static`,
  `upload`, `d`, `health`, `me`, `documents`, `register` or `index`.

Publish accepts any label. A label that breaks these rules (`Kenya`, for example) gets
no project address and no project page. The slug must also obey the
[slug rules](#custom-slug--choose-a-readable-url).

### Label discipline

Use one label for one country or team. Two labels split the project page in two.
Live documents already have this problem: `ke` and `kenya`, `cu` and `cuba`.

Before you choose a label:

1. List the user's documents. Read the `project` field of each document.

   ```bash
   curl -s "https://share.eregistrations.dev/api/me/documents?page=1&limit=100" \
     -H "Authorization: Bearer $(cat ~/.share-token)"
   ```

   The maximum `limit` is 100. If `total` is more than 100, read the next pages.
2. If one label exists for the country or team, use that label.
3. If two labels exist, ask the user which label to use.
4. Never invent a new variant of a label.

A `PATCH` can change the label of a document (see
[the example](#set-or-change-the-project-of-an-existing-document)). The ID does not
change. If you move `ke-access-review` to the label `kenya`, it loses the address
`/ke/access-review`. Its `/d/ke-access-review` link still works.

### `project_url` in responses

Every JSON response that describes a document has `project_url` when the document has
a project address. For example: `"project_url": "https://share.eregistrations.dev/comores/documents"`.
The field is not there when the document has no project address. The `url` field does not
change. It is always `<base>/d/{id}`.

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
   - Sharing: anyone with the link (unlisted)
   - Size: <file size in KB>
   - Preview: <first 200 characters of content>...

   Publish this document? Anyone with the link will be able to read it.
   Say "password" to protect it, or "public" to list it on the home page.
   ```

   Wait for the user to confirm. If they say no, stop.

   If the user asks for a password, ask them for one (at least 6 characters) and
   publish with `"share_mode": "password"`. Do **not** invent a password for them —
   they have to be able to tell their readers what it is.

5. Detect metadata from context:
   - **project**: Follow [Label discipline](#label-discipline). List the user's documents first.
     Reuse the label that already exists for this country or team. Ask the user when two
     labels exist. Never invent a new variant. If no label exists, derive one from the git
     repo name or the directory name. The label must get a project address: use only
     lowercase letters, digits and hyphens, with no hyphen at the start or end (see
     [Label rules](#label-rules)). If you are not sure, leave it empty.
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
    "share_mode": "link",
    "project": "<project-tag-if-known>",
    "doc_type": "<type-if-known>",
    "tags": "<comma-separated-tags>"
  }'
```

7. Show the user:
   - The shareable URL: `project_url` when the response has it, else `url`
   - The management secret (from `secret`) — remind them to save it
   - The document ID

#### Custom slug — choose a readable URL

By default the document gets a random 10-character id and a URL like `/d/a1b2c3d4e5`. The user can instead request a **custom slug** to get a memorable URL such as `/d/tz-migration-report`.

- Pass an optional `slug` field in the JSON body (or a `slug` form field for `POST /upload`).
- When a slug is given, the document id **is** the slug and the URL becomes `<base>/d/<slug>`. The create response is `201` with `{id, url, secret, visibility, created_at}` as usual, plus `project_url` when the document has a project address.
- When the user wants a project address, suggest the slug `{project}-{name}`. For example, the label `comores` and the slug `comores-documents` give `/comores/documents`. See [Project addresses](#project-addresses).
- Show the user `project_url` when the response has it, else `url`.
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
- **Overwrites**: `title`, `content`, `format`.
- **Preserves**: `created_at`, `project`, `doc_type`, `agent_session`, `tags`, `pinned` (and the publisher).
  To change `project`, use a `PATCH` (see [the example](#set-or-change-the-project-of-an-existing-document)).
- **An update never changes sharing** unless you pass `share_mode`. There is no
  longer any field that could imply a different mode than the document already
  has, so re-uploading content is always safe. Passing `share_mode` does change
  it, and moving away from `password` clears the stored password.
- Re-uploading a password-protected document does **not** require re-supplying the
  password; the existing one keeps working.
- Returns `200` with `{id, url, share_mode, visibility, created_at, updated_at}`, plus `project_url` when the document has a project address. The URL does not change. Only the content changes.
- **Cannot combine `slug` with `short_code`** — doing so returns `400 cannot use slug with short_code`. Use `slug` to create a new document; use `short_code` to update an existing one.
- Other errors: `401` if neither `secret` nor a publisher Bearer token is supplied, `403` if the caller doesn't own the document, `404` if `short_code` matches no document.

### `/share list` — List your published documents

```bash
curl -s -X GET "https://share.eregistrations.dev/api/me/documents?page=1&limit=20" \
  -H "Authorization: Bearer $(cat ~/.share-token)"
```

Display as a table: title, format, sharing mode, created date, URL. Use the
`share_mode` field, not `visibility` — `visibility` cannot tell a password-protected
document from a freely linkable one, since both report `private`.

For the URL column, show `project_url` when the document has it. Else show
`https://share.eregistrations.dev/d/{id}`. This list has no `url` field.

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
    "share_mode": "link",
    "slug": "tz-migration-report"
  }'
# -> 201 {"id":"tz-migration-report","url":".../d/tz-migration-report","secret":"sk_...","share_mode":"link","visibility":"private","created_at":"..."}
```

### Create a password-protected document

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{
    "title": "Kenya Access Review",
    "format": "md",
    "content": "# Access Review\n...",
    "share_mode": "password",
    "password": "<at least 6 characters>",
    "slug": "ke-access-review"
  }'
# -> 201 {"id":"ke-access-review", ..., "share_mode":"password","visibility":"private", ...}
```

Then tell the user: send the link and the password through separate messages.

### Change the sharing mode of an existing document

```bash
# Password-protect it (or rotate an existing password — this logs out every reader)
curl -s -X PATCH https://share.eregistrations.dev/api/documents/ke-access-review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{"share_mode":"password","password":"<new password>"}'

# Open it back up to anyone with the link
curl -s -X PATCH https://share.eregistrations.dev/api/documents/ke-access-review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{"share_mode":"link"}'
```

### Create a document with a project address

```bash
curl -s -X POST https://share.eregistrations.dev/api/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{
    "title": "Comores Documents",
    "format": "md",
    "content": "# Documents\n...",
    "share_mode": "password",
    "password": "<at least 6 characters>",
    "project": "comores",
    "slug": "comores-documents"
  }'
# -> 201 {"id":"comores-documents","url":".../d/comores-documents","project_url":".../comores/documents", ...}
```

Show the user `project_url`.

### Set or change the project of an existing document

```bash
# File the document under "comores". The share mode and the password do not change.
curl -s -X PATCH https://share.eregistrations.dev/api/documents/comores-documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{"project":"comores"}'
# -> 200 {"id":"comores-documents", ..., "project":"comores","project_url":".../comores/documents", ...}

# Clear the project
curl -s -X PATCH https://share.eregistrations.dev/api/documents/comores-documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat ~/.share-token)" \
  -d '{"project":""}'
```

A `PATCH` with only `project` does not change the share mode or the password. You can
also authenticate with the header `X-Secret: <sk_...>`. An invalid label gives this `400`:

```
400 invalid project: use lowercase letters, digits and inner hyphens, like "kenya". Reserved names such as "admin" or "static" are not allowed. Send "" to clear the project.
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
    "share_mode": "public"
  }'
# -> 200 {"id":"tz-migration-report","url":".../d/tz-migration-report","share_mode":"public","visibility":"public","created_at":"...","updated_at":"..."}
```

## Important Notes

- **Max content size**: 5 MB
- **Max title length**: 200 characters
- **Formats**: Only `html` and `md` are supported
- **Scripts in a markdown document do not run.** The markdown page blocks them with a
  `Content-Security-Policy`. Publish an interactive page as `html`. Scripts in an HTML
  document run in its sandboxed frame.
- **Sharing**: Default to `"share_mode": "link"` — unlisted, readable by anyone with the URL. Use `password` when the content needs protecting, `public` to list it on the home page, and `owner` only for material nobody else needs to open. See [Sharing Modes](#sharing-modes).
- **Passwords are not recoverable.** The service stores only a bcrypt hash, so a forgotten password has to be replaced with a new one, which logs out everyone currently reading.
- **Rate limit**: 10 publishes per minute per IP. If you get 429, wait and retry.
- The management secret is shown only once at creation. It allows deleting or updating the document without the publisher token.
- The publisher token also allows managing all documents published with it.
- **Custom slugs**: optionally pass `slug` on create to get a readable `/d/<slug>` URL. Omitting it keeps the default random id. See [Custom slug](#custom-slug--choose-a-readable-url).
- **Update in place**: re-POST with `short_code` + the management secret (JSON field `secret`, or form field `management_secret` on `/upload`) — or the publisher token — to overwrite an existing document at the same URL. See [Update in place](#update-in-place--overwrite-an-existing-document).
- **Project addresses**: send the label as `project` and the slug `{project}-{name}` to get `/{project}/{name}`. Reuse the label that exists. See [Project addresses](#project-addresses).

## Error Handling

- **401**: Token invalid or expired — delete `~/.share-token` and re-register.
- **413**: Content too large — inform the user of the 5 MB limit.
- **429**: Rate limited — wait 60 seconds and retry once.
- **422**: Content contains detected secrets (API keys, passwords, private keys) — review and remove sensitive data before sharing.
- **400**: Validation error — check title, format, and content fields. Also returned for an invalid slug (`invalid slug: <reason>`), when `slug` is combined with `short_code` (`cannot use slug with short_code`), or for an inconsistent sharing request:
  - `give either 'share_mode' or 'visibility', not both`
  - `password required for the password share mode`
  - `password too short` (minimum 6 characters)
  - `password only applies to the password share mode` — sent a `password` with a
    mode that is not `password`. It is refused rather than accepted-and-ignored,
    so a `200` always means the protection you asked for was applied
  - `share mode invalid` — must be `public`, `link`, `password` or `owner`
  - `'visibility' is no longer accepted on writes — use 'share_mode': …` — sent
    the retired field on a publish or update
  - `invalid project: use lowercase letters, digits and inner hyphens, like "kenya". …` —
    a `PATCH` sent a `project` label that breaks the [label rules](#label-rules)
- **401 on `GET /d/{id}`**: the document is password-protected and this request has not unlocked it. That is the reader's prompt, not an error in your call.
- **404 on a document you just published**: you probably used `share_mode: "owner"`, which hides the document from everyone without a credential. Re-publish as `link` or `password` if someone else needs to read it.
- **404 on `/{project}/{name}`**: the document's `project` is not exactly `{project}`, its ID is not `{project}-{name}`, or its mode is `owner`. Read the document with `GET /api/documents/{id}` and compare.
- **403**: On an update-in-place, the caller doesn't own the document — use the correct `secret` or publisher token.
- **404**: On an update-in-place, `short_code` matches no existing document.
- **409**: The requested slug is already in use (`URL already in use`) — choose a different slug.
