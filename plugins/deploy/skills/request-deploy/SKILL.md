---
name: request-deploy
description: >
  Request a deployment on singlewindow Coolify by opening an issue on unctad-ai/deploy.
  Use when the user says "deploy this", "deploy to singlewindow", "request a deploy",
  "host this on eregistrations.dev", or similar. Detects repo + framework, fills sensible
  defaults, asks only what's needed, posts via `gh`.
license: UNCTAD-Internal
compatibility: Requires `gh` CLI authenticated to GitHub.
allowed-tools: Read, Edit, Bash(gh *), Bash(git *), Bash(cat *), Bash(ls *), Bash(test *), Bash(diff *), AskUserQuestion
metadata:
  version: "1.5.0"
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
3. **`dockercompose` only — pre-flight the compose file.** Skip this step entirely for `dockerfile`, `auto-detect`, and `static` — Coolify controls the container's host-side networking itself in those cases.

   Parse the compose file matched in step 2 (prefer `python3 -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open('docker-compose.yml'))))"` so anchors/merge-keys resolve; fall back to regex if PyYAML isn't available). Run **all** rules below in a single pass and collect every finding — do not prompt per-rule. One bundled `AskUserQuestion` at the end beats N round-trips of "fix → redeploy → fix → redeploy".

   **Rule A — Host-published `ports:`** (BLOCKER, auto-fixable).
   Services with a `ports:` key will collide on Coolify's multi-tenant host. The deploy fails at `docker compose up` with `"Bind for 0.0.0.0:<port> failed: port is already allocated"`.
   - *Fix:* replace `ports: - '<host>:<container>'` with `expose: - '<container>'`. For bare `'<port>'` entries, expose the same port. Preserve protocol suffix (`3000/tcp` → `"3000"`).

   **Rule B — Primary service not named `app`** (BLOCKER, auto-fixable).
   The onboarder's `set_domain_compose` call hard-codes `docker_compose_domains[].name` to `"app"`. If the first service key is something else (`web`, `frontend`, `server`, …), Coolify will route the domain to no running service and the deploy will silently produce a 404 or self-signed cert.
   - *Fix:* rename the top-level service key to `app`. Also update any `depends_on`, `links`, `network_aliases` or other string references elsewhere in the file.

   **Rule C — Healthcheck with no `start_period` on a `depends_on: service_healthy` target** (BLOCKER, auto-fixable).
   If service X has `depends_on.<Y>.condition: service_healthy` and service Y has a `healthcheck:` but no `start_period:`, first-time init (especially for DB images: `postgres`, `mysql`, `mariadb`, `mongo`, `redis` with persistence) can exceed `retries × interval` and the dependent service aborts with `"dependency failed to start: container <Y> is unhealthy"`. Historical incident (2026-04-22, my-account-next): `postgres:18-alpine` first-init on a fresh volume took longer than 5 × 5s, breaking `app.depends_on.db`.
   - *Fix:* insert `start_period: 30s` (use `40s` if the target image name matches `^(postgres|mysql|mariadb|mongo)`) into the target's `healthcheck:` block, and raise `retries` to `10` if it's currently `< 10`. Also prefer `pg_isready -U postgres -d <db>` over bare `pg_isready` if a `POSTGRES_DB` env is present — more precise readiness signal.

   **Rule D — Undeclared `${VAR}` references** (BLOCKER, requires user input).
   Regex the whole compose for `\${([A-Z_][A-Z0-9_]*)(?::-[^}]*)?}` and extract variable names. A reference is **declared** if any of these apply:
   - it has an inline default (`${VAR:-some-value}`),
   - it's a Coolify magic var (`COOLIFY_URL`, `COOLIFY_FQDN`, `COOLIFY_BRANCH`, `COOLIFY_RESOURCE_UUID`),
   - the user will submit it in the issue's env-vars block (you'll collect these in step 6).

   Anything left is **undeclared** and will interpolate to an empty string at compose parse time. Empty `POSTGRES_PASSWORD` → postgres refuses to init; empty `NEXTAUTH_SECRET` → app crashes on boot; etc.
   - *Fix:* during the bundled AskUserQuestion, list each undeclared var and, for each, either (a) add it to the env-vars the user will submit (offer `<GENERATE>` for anything matching `(PASSWORD|SECRET|TOKEN|KEY)$`, plain value otherwise), or (b) declare an inline default in the compose file.

   **Bundled confirmation — one `AskUserQuestion`, never free text.**
   After running all four rules, if any finding exists, show a single question whose body enumerates every finding. The "Fix it for me" description must list the concrete edits/additions the skill will apply; the user reviews the full batch before any change is made.

   ```
   question: "docker-compose.yml has <N> issues that will fail the deploy. How to proceed?"
   header: "Compose pre-flight"
   multiSelect: false
   options:
     - label: "Fix it for me (recommended)"
       description: |
         I'll edit docker-compose.yml, show you the diff, commit+push the fix, then file the deploy issue.
         Edits I'll make:
           • [Rule A] replace `ports:` with `expose:` on <service> (port <N>)
           • [Rule B] rename top-level service `<old>` → `app` (and update refs)
           • [Rule C] add `start_period: 30s` to `<service>.healthcheck` (+ bump retries to 10)
           • [Rule D] record env vars <FOO>, <BAR> to submit in the deploy issue
         (Only the rules that fired are listed — skip the others.)
     - label: "I'll fix it manually"
       description: "Abort. Apply the listed fixes yourself, commit+push, then re-run /request-deploy."
     - label: "Proceed anyway (will fail)"
       description: "File the issue as-is. Deploy will fail. Use only if you know what you're doing."
   ```

### Auto-fix path (when user picks "Fix it for me")

This path modifies the **user's app repo** — move carefully:

1. **Guardrails — bail out early if any fails** (don't try to fix; offer only "I'll fix it manually" or "Proceed anyway"):
   - `git status --porcelain` must be empty (clean working tree). If not: "I can't auto-fix with uncommitted changes — commit or stash them first."
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}` must return a remote-tracking branch (so `git push` has a target). If not: bail with a clear message.
   - The user must be on a non-default branch **or** confirm pushing to `main`. Default to refusing a direct push to `main`; ask if they want to proceed on `main` or create a fix branch.

2. **Build the edits in memory, compute a unified diff, show it:**
   - **Rule A (`ports:` → `expose:`):** replace `ports:` with `expose:` using the container port (right side of `host:container` or the bare value if no colon). Preserve protocol suffix handling (`3000:3000/tcp` → `"3000"` exposed).
   - **Rule B (service rename):** change the top-level service key and update any `depends_on`, `links`, and other service references elsewhere in the file.
   - **Rule C (healthcheck `start_period`):** insert `start_period: 30s` (or `40s` for `postgres|mysql|mariadb|mongo` images) into the affected `healthcheck:` block. If `retries:` is present and `< 10`, bump it to `10`. Only add — never reduce existing values. If the healthcheck `test:` uses bare `pg_isready`, also extend it to `pg_isready -U postgres -d <db>` where `<db>` is the service's `POSTGRES_DB` (from its env block).
   - **Rule D (undeclared env vars):** this rule does NOT edit docker-compose.yml. Instead, the collected var names get appended to the env-var block the skill posts in the deploy issue (step 6 of the main flow). During the batch confirmation, show the user the proposed KEY=VALUE lines so they can override before submission.
   - Bundle all file edits into one combined diff. Run `diff -u <old> <new>` to produce a unified diff string.
   - Show the diff to the user inline before writing. Use a second `AskUserQuestion` with `{Apply this diff / Cancel}`. Only write on explicit Apply.

3. **Apply + commit + push:**
   - Use the Edit tool to apply each change. Prefer multiple small Edit calls over a single Write to preserve comments and surrounding formatting.
   - `git add docker-compose.yml`
   - Commit subject reflects whichever rules actually fired, e.g.:
     - `fix(compose): make deploy-ready for Coolify (expose, healthcheck, service name)`
     - `fix(compose): expose ports instead of publishing` (Rule A only)
     - `fix(compose): add healthcheck start_period for DB dependency` (Rule C only)
   - Commit body: one line per applied rule, code + short description (self-documenting git log).
   - `git push`
   - If push fails (permission, protected branch), roll back: `git reset --hard HEAD~1`, tell the user, offer to fall through to "I'll fix it manually."

4. **Continue to the normal flow** (propose slug/branch/domain, env vars, submit the deploy issue).

### What the skill must NOT do

- **Never edit without showing the diff first** and getting explicit Apply from the user. No silent modifications.
- **Never rewrite the whole file** — use the Edit tool with minimal old_string/new_string so comments and surrounding formatting are preserved.
- **Never push to `main` without explicit consent** even if the user is currently on it.
- If the compose file uses extends, anchors, or other YAML features that make mechanical editing risky, bail to "I'll fix it manually" and tell the user why.

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
