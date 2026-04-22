---
name: request-deploy
description: >
  Request a deployment on singlewindow Coolify by opening an issue on unctad-ai/deploy.
  Use when the user says "deploy this", "deploy to singlewindow", "request a deploy",
  "host this on eregistrations.dev", or similar. Detects repo + framework, fills sensible
  defaults, asks only what's needed, posts via `gh`.
license: UNCTAD-Internal
compatibility: Requires `gh` CLI authenticated to GitHub.
allowed-tools: Read, Bash(gh *), Bash(git *), Bash(cat *), Bash(ls *), Bash(test *), AskUserQuestion
metadata:
  version: "1.2.0"
  version-date: "2026-04-22"
  author: "UNCTAD Trade Facilitation Section"
---

# Request-Deploy — Open a Deployment Issue

**Invoke from inside the repo you want to deploy.** This skill reads the current directory's git remote to infer the repo, then opens a well-formed issue on `unctad-ai/deploy`. That repo's workflows handle the rest: parse the issue → create the Coolify app → provision a cert → comment the live URL back.

## The quick path

1. `git remote get-url origin` to detect the repo. The repo must live under `unctad-ai` or `UNCTAD-eRegistrations` — those are the orgs where the Coolify GitHub App is installed. For any other namespace, tell the user to open a maintainer request on `unctad-ai/deploy` first.
2. Sniff the repo to guess the build type + port. **Check in this exact order and stop on the first match** (compose wins over Dockerfile because compose orchestrates Dockerfile builds):
   1. `docker-compose.yml` (or `docker-compose.yaml`, or `compose.yml`, or `compose.yaml`) present → `dockercompose`.
   2. `Dockerfile` present (and no compose file) → `dockerfile`.
   3. `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `Gemfile`, etc. → `auto-detect`. Default port: `3000` for Node/Next, `5173` for Vite, `8000` for Python/Django, otherwise ask.
   4. Only static HTML/CSS/JS → `static`, port `80`.
3. **`dockercompose` only — pre-flight the compose file.** This check applies **only when** build type is `dockercompose`. Other build types (`dockerfile`, `auto-detect`, `static`) don't hit the host-port collision class because Coolify controls the container's host-side networking itself — in those cases, skip this step entirely.

   Read `docker-compose.yml` (or whichever compose file matched in step 2) and scan each service for a top-level `ports:` key. If any service publishes a host port, warn the user with the exact remediation:

   ```
   ⚠  docker-compose.yml publishes host ports:
        service 'app' → ports: ["3000:3000"]
        service 'db'  → ports: ["5432:5432"]

      Coolify runs many apps on one host. Two containers can't both bind the
      same host port — your deploy will fail at `docker compose up` with
      "Bind for 0.0.0.0:<port> failed: port is already allocated".

      Fix before submitting: replace `ports:` with `expose:` (or remove
      entirely). Coolify/Traefik routes the domain to the service's internal
      port using the name you'll give in the form.

      Example:
        services:
          app:
            expose: ["3000"]   # was: ports: ["3000:3000"]
   ```

   Offer to abort so they can fix the repo, or proceed anyway (their risk). Do **not** auto-edit the compose file — it's their repo, not ours.

4. Propose defaults:
   - **Name** = the repo name (let the user override — the server slugifies whatever they pick, e.g. "My App" → "my-app").
   - **Branch** = current branch (or `main`).
   - **Domain** = `<slug-of-name>.eregistrations.dev`.
5. Show the user what you'll submit and ask for confirmation.
6. Ask about env vars (optional — "none" is fine).
7. Post the issue. Show the URL. Done.

The user should need to answer **at most** a couple of questions to get a deploy running. When in doubt, propose a default and let them override.

## Gathering env vars

Ask once: "Any environment variables? Reply with one `KEY=VALUE` per line, or 'none'."

Supported value forms (pass-through unchanged — resolved server-side):

- `KEY=<GENERATE>` — 64-char hex secret
- `KEY=<GENERATE:hex:N>` / `<GENERATE:base64:N>` / `<GENERATE:uuid>`
- `KEY=<SET-IN-COOLIFY>` — placeholder; user fills later in Coolify UI

**Handle secret-shaped literals helpfully, not defensively.** If a literal value looks like a real secret (common prefixes like `sk_live_`, `ghp_`, `xox[bp]-`, `AKIA…`, or PEM headers, or a JWT-shape, or length > 200 chars), auto-swap to `<SET-IN-COOLIFY>` and tell the user once:

```
⚠  STRIPE_SECRET_KEY looks like a real secret. I've set it to <SET-IN-COOLIFY>.
   After deploy, set the real value in Coolify (https://coolify.singlewindow.dev)
   and redeploy.
```

Do NOT interrogate every value. Do NOT refuse to post. The `<SET-IN-COOLIFY>` path is designed exactly for this; swap and move on.

## Building the issue body

The deploy workflow parses the Issue Forms–rendered body — each field becomes `### <Heading>\n\n<value>\n\n`. Use these headings, in this order, with **exact** wording:

1. `Name`
2. `Domain`
3. `GitHub repository`
4. `Branch`
5. `Port`
6. `Build type` — one of `static`, `dockerfile`, `dockercompose`, `auto-detect`
7. `Environment variables` — fenced `shell` block (the template declares `render: shell`):
   ~~~
   ### Environment variables

   ```shell
   NEXTAUTH_URL=https://myapp.eregistrations.dev
   NEXTAUTH_SECRET=<GENERATE>
   ```

   ~~~
   Omit the section, or write `_No response_`, when the user has no env vars.

Do **not** send headings the current form doesn't have (`Project slug`, `One-line description`, `Build pack`, `Build-pack extras`, `Pre-flight checklist`) — the parser ignores them, but including them bloats the body and leaves stale content in the issue.

## Posting

```bash
gh issue create \
  --repo unctad-ai/deploy \
  --title "[Deploy]" \
  --label deploy-request \
  --body "<the body from above>"
```

Capture the issue URL from stdout. The workflow auto-renames the title to `[Deploy] <domain>` after parsing — you don't need to set a specific title yourself.

## Final message to the user

Short and useful:

```
Deploy request opened: <issue URL>

The onboarder runs in 15-30s. First build + Let's Encrypt cert ~3 min.
A comment on the issue will show the live URL when it's ready.

You'll need to fill these in Coolify after deploy (https://coolify.singlewindow.dev):
  - STRIPE_SECRET_KEY    (auto-replaced — had a Stripe-shaped value)
  - DATABASE_URL         (you asked for <SET-IN-COOLIFY>)

Future pushes to `<branch>` will auto-redeploy.
```

Drop the Coolify follow-up section if the user has no placeholders.

## Pre-flight

Before starting:

1. `gh auth status` must succeed. If not, tell the user once to run `gh auth login` and stop.
2. `git remote get-url origin` must return something. If the user is outside a git repo, tell them to `cd` into the repo they want to deploy and retry.
3. If the detected repo is literally `unctad-ai/deploy`, stop: that's the deploy-orchestration repo itself and cannot be deployed through this flow.
4. If the repo's owner isn't `unctad-ai` or `UNCTAD-eRegistrations` (case-insensitive), tell the user the Coolify GitHub App isn't installed on that org and point them to `https://github.com/unctad-ai/deploy/issues/new` to request installation first.

## Notes

- The deploy repo's workflow validates inputs (name format, domain TLD, build type enum, port range). If the user provides something invalid, the workflow comments a clear error and a maintainer re-applies `approved` after they fix it. Don't re-police client-side.
- Generated secret values are never visible to you. `<GENERATE>` is a sentinel — the actual value is created on the workflow runner, stored in Coolify, and readable only from the Coolify UI.
- Non-authorized users (not in `.github/deploy-authorized-users.yml`) still get a valid issue — it just waits for a maintainer to apply `approved`. No need to pre-check.
