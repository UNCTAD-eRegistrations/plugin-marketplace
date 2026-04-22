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
  version: "1.0.0"
  version-date: "2026-04-22"
  author: "UNCTAD Trade Facilitation Section"
---

# Request-Deploy — Open a Deployment Issue

**Invoke from inside the repo you want to deploy.** This skill reads the current directory's git remote to infer `repo`, `branch`, and a slug, then opens a well-formed issue on `unctad-ai/deploy`. That repo's workflows handle the rest: parse the issue → create the Coolify app → provision a cert → comment the live URL back. You just make the request easy.

## The quick path

1. `git remote get-url origin` to detect the repo.
2. Sniff the repo to guess `build_pack` + `port`:
   - `Dockerfile` present → `dockerfile`.
   - `docker-compose.yml` present → `dockercompose`.
   - `package.json` with Next/Vite/Node → `nixpacks`, port `3000` (or `5173` for Vite).
   - Otherwise → `nixpacks`, ask for the port.
3. Propose:
   - slug = sanitized repo name (`[a-z0-9-]+`, starts with letter/digit).
   - branch = current branch (or `main`).
   - domain = `<slug>.eregistrations.dev`.
   - description = "Deployment of `<owner>/<repo>` (`<branch>`)" — user can edit.
4. Show the user what you'll submit and ask for confirmation.
5. Ask about env vars (optional — "none" is fine).
6. Post the issue. Show the URL. Done.

The user should need to answer **at most** a couple of questions to get a deploy running. When in doubt, propose a default and let them override.

## Gathering env vars

Ask once: "Any environment variables? Reply with one `KEY=VALUE` per line, or 'none'."

Supported value forms (pass-through unchanged — resolved server-side):

- `KEY=<GENERATE>` — 64-char hex secret
- `KEY=<GENERATE:hex:N>` / `<GENERATE:base64:N>` / `<GENERATE:uuid>`
- `KEY=<SET-IN-COOLIFY>` — placeholder; user fills later in Coolify UI

**Handle secret-shaped literals helpfully, not defensively.** If a literal value looks like a real secret (common prefixes like `sk_live_`, `ghp_`, `xox[bp]-`, `AKIA…`, or PEM headers, or a JWT-shape, or length > 200 chars), auto-swap to `<SET-IN-COOLIFY>` and tell the user once:

```
⚠  STRIPE_SECRET_KEY looks like a real secret. Since GitHub issues are public,
   I've set it to <SET-IN-COOLIFY>. After deploy, set the real value in Coolify
   (https://coolify.singlewindow.dev) and redeploy.
```

Do NOT interrogate every value. Do NOT refuse to post. The `<SET-IN-COOLIFY>` path is designed exactly for this; swap and move on.

## Building the issue body

The deploy workflow parses the Issue Forms–rendered body — each field becomes `### <Heading>\n\n<value>\n\n`. Use these headings, in this order, with **exact** wording:

1. `Project slug`
2. `GitHub repository`
3. `Branch`
4. `Domain`
5. `Build pack`
6. `Port`
7. `One-line description`
8. `Environment variables` — fenced `shell` block (the template declares `render: shell`):
   ```
   ### Environment variables

   ```shell
   NEXTAUTH_URL=https://myaccount.eregistrations.dev
   NEXTAUTH_SECRET=<GENERATE>
   ```

   ```
   Omit the section, or write `_No response_`, when the user has no env vars.
9. `Build-pack extras` — same fenced-`shell` format. Usually `_No response_`.
10. `Pre-flight checklist` — render as:
    ```
    - [X] I've granted the Coolify GitHub App access to this repository.
    - [X] The domain I chose is not already in use by another deployment.
    ```

## Posting

```bash
gh issue create \
  --repo unctad-ai/deploy \
  --title "[Deploy] <slug>" \
  --label deploy-request \
  --body "<the body from above>"
```

Capture the issue URL from stdout and show it to the user.

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

Drop the Coolify/follow-ups section if the user has no placeholders.

## Pre-flight

Before starting:

1. `gh auth status` must succeed. If not, tell the user once to run `gh auth login` and stop.
2. `git remote get-url origin` must return something. If the user is outside a git repo, tell them to `cd` into the repo they want to deploy and retry.
3. If the detected repo is literally `unctad-ai/deploy`, stop: that's the deploy-orchestration repo itself and cannot be deployed through this flow. Tell the user to `cd` into the target app's repo instead.

## Notes

- The deploy repo's workflow validates everything (slug format, domain TLD, build_pack enum, port range). If the user provides something invalid, the workflow comments a clear error on the issue and a maintainer re-applies `approved` after they fix it. Don't re-police client-side.
- Generated secret values are never visible to you. `<GENERATE>` is a sentinel string — the actual value is created on the workflow runner, stored in Coolify, and readable only from the Coolify UI.
- Non-authorized users (not in `.github/deploy-authorized-users.yml`) still get a valid issue — it just waits for a maintainer to apply `approved`. No need to pre-check; GitHub Actions posts a comment explaining this.
