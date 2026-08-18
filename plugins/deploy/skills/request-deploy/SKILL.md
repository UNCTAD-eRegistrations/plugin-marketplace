---
name: request-deploy
description: >
  Request a deployment on singlewindow Coolify by opening an issue on unctad-ai/deploy.
  Use when the user says "deploy this", "deploy to singlewindow", "request a deploy",
  "host this on eregistrations.dev", or similar. Detects repo + framework, fills sensible
  defaults, asks only what's needed, posts via `gh`.
license: UNCTAD-Internal
compatibility: Requires `gh` CLI authenticated to GitHub.
allowed-tools: Read, Edit, Bash(gh *), Bash(git *), Bash(cat *), Bash(ls *), Bash(test *), Bash(diff *), Bash(npm *), Bash(docker *), Bash(python3 *), Bash(du *), Bash(find *), Bash(rm *), AskUserQuestion
metadata:
  version: "1.10.0"
  version-date: "2026-08-18"
  author: "UNCTAD Trade Facilitation Section"
  changelog:
    - "1.10.0 (2026-08-18): Added pre-flight Gate 3 — Runner toolchain compatibility (Rule F auto-fix). Incident (designstudio): local Gates 1–2 passed on the dev laptop's newer Node, but the nixpacks runner built with Node 22.11.0 while vite 8/rolldown require ^20.19.0 || >=22.12.0 — and npm on Node <22.12 silently skips optional deps with unsatisfied engines (npm/cli#4828), so `npm ci` exited 0 without installing @rolldown/binding-linux-x64-gnu and `vite build` died with 'Cannot find native binding'. Detection scans installed packages' engines against the runner's Node; fix pins a newer nixpkgsArchive in nixpacks.toml (repo-side, no Coolify change). Documents the NIXPACKS_NODE_VERSION=24/23 traps."
---

# Request-Deploy — Open a Deployment Issue

**Invoke from inside the repo you want to deploy.** This skill reads the current directory's git remote to infer the repo, then opens a well-formed issue on `unctad-ai/deploy`. That repo's workflows handle the rest: parse the issue → create the Coolify app → provision a cert → comment the live URL back.

## The quick path

1. `git remote get-url origin` to detect the repo. The repo must live under `unctad-ai` or `UNCTAD-eRegistrations` — those are the orgs where the Coolify GitHub App is installed. For any other namespace, tell the user to open a maintainer request on `unctad-ai/deploy` first.
2. Sniff the repo to guess the build type + port. **Check in this exact order and stop on the first match** (compose wins over Dockerfile because compose orchestrates Dockerfile builds):
   1. `docker-compose.yml` (or `docker-compose.yaml`, or `compose.yml`, or `compose.yaml`) present → `dockercompose`.
   2. `Dockerfile` present (and no compose file) → `dockerfile`.
   3. `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `Gemfile`, etc. → `auto-detect`. Default port: `3000` for Node/Next, `8000` for Python/Django, otherwise ask. **Before accepting `auto-detect` for Node**, check the static-SPA shape in step 2.bis — if it matches, reclassify and apply Rule E before filing.
   4. Only static HTML/CSS/JS → `static`, port `80`.

2.bis. **Node static-SPA detection — run before accepting `auto-detect` from step 2.3.** A frontend-only Node project builds a `dist/` (or `build/` / `out/`) but has no runtime server. Nixpacks has no `start` command to run, so the container crashloops with `bash: -c: option requires an argument`. Coolify's `static` build pack doesn't help either — it copies the repo verbatim without running `npm run build`, so the served page ends up referencing `/src/main.tsx` instead of the built assets.

   Trigger when **all** apply:
   - `package.json.scripts.build` is defined
   - `package.json.scripts.start` is **not** defined
   - no `Dockerfile` and no compose file
   - any of the framework signals below is true:

   | Framework | Signal | Output dir |
   |---|---|---|
   | Vite | `vite` in deps, OR `vite.config.{ts,js,mjs,cjs}` present | `dist` |
   | Astro (static) | `astro` in deps and astro.config.* has no `output: 'server'` | `dist` |
   | SvelteKit static | `@sveltejs/adapter-static` in deps | `build` |
   | CRA | `react-scripts` in deps | `build` |
   | Next.js export | `next` in deps and next.config.* has `output: 'export'` | `out` |

   If matched → apply Rule E below **before** filing the deploy issue. Port becomes `3000` (what `serve` binds to). Build type stays `auto-detect` (the added `start` script makes Nixpacks work out of the box).

   **Rule E — Static SPA has no runtime server** (BLOCKER, auto-fixable).
   Add a `start` script that serves the built output via `serve`, and install `serve` as a `devDependency` so Nixpacks bakes it into the image during `npm ci`. No Dockerfile, no nginx config — just two package.json additions and a synced lockfile.

   **Why devDependency, not `npx -y`:** an earlier version of this rule used `"start": "npx -y serve@14 …"` to avoid touching dependencies. That works, but `npx` downloads `serve` at *container-start* time, adding ~60-90s of cold-start latency on **every deploy**, **every restart**, **every rolling update** — Coolify's auto-redeploy on `git push` means this hits users repeatedly. Installing `serve` as a devDependency makes `npm ci` fetch it once at build time; `serve` binds port 3000 instantly on container boot.

   - *Fix:* three edits, applied atomically:
     1. `package.json.scripts.start` = `"serve -s <OUTPUT_DIR> -l ${PORT:-3000}"` (with `<OUTPUT_DIR>` from the table above).
     2. `package.json.devDependencies.serve` = `"^14.2.4"` (merge into existing devDependencies object, preserving other entries).
     3. Regenerate `package-lock.json` via `npm install serve@14 --save-dev --package-lock-only` — this updates the lockfile without writing `node_modules` (fast, no disk churn), so subsequent `npm ci` in Nixpacks resolves `serve` reproducibly.

     The `-s` flag enables SPA fallback (unknown routes → `index.html`). `$PORT` is injected by Coolify from `ports_exposes`.

   **Pre-check:** `command -v npm` must succeed on the skill-runner's machine. If `npm` is missing, bail to "open a help issue" option with a one-line explanation — the skill can't regenerate the lockfile without it. Most machines running Claude Code on a Node repo already have `npm`; this guard prevents a broken commit in the rare case they don't.

   **Non-technical framing** — this is a self-service deploy for non-technical users. Never show the user a diff or explain the line. The single question they see is:

   ```
   question: "Your <framework> app needs one line added to package.json so it can be served after building. Can I add it?"
   header: "Quick setup"
   multiSelect: false
   options:
     - label: "Yes, add it and deploy (recommended)"
       description: |
         I'll add a 'start' script to package.json (plus a small dev dependency called 'serve')
         that hosts your built site. It's a standard setup used by most web apps —
         safe to ignore once added.
     - label: "No — open a help issue instead"
       description: "Abort. A maintainer will help you deploy this app manually."
   ```

   On "Yes":
   1. Reuse the **same guardrails as the compose auto-fix** (clean tree, upstream branch — see the Auto-fix path section below).
   2. Apply edits 1–2 with the `Edit` tool on `package.json` (add `start` script, add `serve` devDependency).
   3. Run `npm install serve@14 --save-dev --package-lock-only` to sync `package-lock.json`.
   4. **Verify the build locally before committing anything.** Run `npm ci && npm run build` in the repo (pipe stderr, save stdout to a file so we can surface errors). The build is the same command Nixpacks will run in the deploy container; running it here catches broken deps, TypeScript errors, missing env vars, etc. *before* we commit and push. If it fails: show the user a plain-language message — *"I tried to prepare your project for deployment, but the build failed on my end. This means the deploy would fail too. No changes were committed."* — then surface the last 20 lines of build output as context and offer only "Open a help issue" or "Cancel." `git restore package.json package-lock.json` to undo the edits.
   5. Only if the build succeeded: verify the expected output directory exists (e.g., `dist/` for Vite). If it doesn't, bail with the same "build failed on my end" message — the `start` script would point at a non-existent directory.
   6. `git add package.json package-lock.json`, commit with subject `chore: add deploy start script`, push.
   7. Fall through to step 4 of the main flow with `Build type: auto-detect`, `Port: 3000`.

   **Why verify locally:** the whole point of the non-technical flow is that the user clicks "Yes" and trusts the skill. If the skill pushes a broken commit and the deploy fails server-side, the user sees a cryptic red × from the onboarder — exactly the outcome we're trying to prevent. Running the build client-side takes 10–60 seconds and confirms the diff actually works end-to-end before anything leaves the laptop.

   **Final success message must mention the added script, plain-language:**

   ```
   Deployed ✓ https://<domain>/   (SSL cert provisions in ~2 min)

   I added a 'start' script to your package.json so the deploy system knows how to
   serve your app. You can ignore it — future pushes will redeploy the same way.
   ```
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
   - `git status --porcelain` must be empty (clean working tree). If not: "I can't auto-fix with uncommitted changes — commit or stash them first." This is a safety guard, not a workflow nit: it prevents the skill from sweeping the user's in-progress work into our commit.
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}` must return a remote-tracking branch (so `git push` has a target). If not: bail with "this branch has no upstream — please push it to GitHub first."

   **Do not ask the user about branches.** Non-technical users don't master git branching; the skill must commit to **whatever branch the user is currently on** and push there. If they're on `main`, push to `main`. If they're on a feature branch, push to that. Branch strategy is the user's choice by virtue of their current `HEAD` — asking them to pick between "main" and "a new branch" is a developer ergonomic that has no place in a self-service deploy flow. The protected-branch concern is handled at step 3: if the push fails (protected branch, missing permission, stale upstream), the skill rolls back the local commit and offers the fallback options — no branching decision required from the user.

2. **Build the edits in memory, compute a unified diff, show it:**
   - **Rule A (`ports:` → `expose:`):** replace `ports:` with `expose:` using the container port (right side of `host:container` or the bare value if no colon). Preserve protocol suffix handling (`3000:3000/tcp` → `"3000"` exposed).
   - **Rule B (service rename):** change the top-level service key and update any `depends_on`, `links`, and other service references elsewhere in the file.
   - **Rule C (healthcheck `start_period`):** insert `start_period: 30s` (or `40s` for `postgres|mysql|mariadb|mongo` images) into the affected `healthcheck:` block. If `retries:` is present and `< 10`, bump it to `10`. Only add — never reduce existing values. If the healthcheck `test:` uses bare `pg_isready`, also extend it to `pg_isready -U postgres -d <db>` where `<db>` is the service's `POSTGRES_DB` (from its env block).
   - **Rule D (undeclared env vars):** this rule does NOT edit docker-compose.yml. Instead, the collected var names get appended to the env-var block the skill posts in the deploy issue (step 6 of the main flow). During the batch confirmation, show the user the proposed KEY=VALUE lines so they can override before submission.
   - Bundle all file edits into one combined diff. Run `diff -u <old> <new>` to produce a unified diff string.
   - Show the diff to the user inline before writing. Use a second `AskUserQuestion` with `{Apply this diff / Cancel}`. Only write on explicit Apply.

3. **Apply + verify locally + commit + push:**
   - Use the Edit tool to apply each change. Prefer multiple small Edit calls over a single Write to preserve comments and surrounding formatting.
   - **Verify the edited compose file parses and resolves before committing.** Run `docker compose config -q` (quiet mode: exits 0 on success, non-zero + stderr diagnostics on failure). If `docker` isn't installed on the user's machine, fall back to `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` which catches syntax errors but not compose-level issues (missing required keys, unresolved env refs). If either validation fails: **revert the working-tree edits with `git restore docker-compose.yml` — do not commit.** Show the user a plain-language error: *"I tried to fix your docker-compose.yml, but the result didn't validate. No changes were committed."* Surface the last 20 lines of validator output. Offer only "Open a help issue" or "Cancel."
   - `git add docker-compose.yml`
   - Commit subject reflects whichever rules actually fired, e.g.:
     - `fix(compose): make deploy-ready for Coolify (expose, healthcheck, service name)`
     - `fix(compose): expose ports instead of publishing` (Rule A only)
     - `fix(compose): add healthcheck start_period for DB dependency` (Rule C only)
   - Commit body: one line per applied rule, code + short description (self-documenting git log).
   - `git push` to the current branch's upstream (no `-u`, no branch-name argument — the upstream was verified in the guardrail step).
   - If push fails (permission, protected branch, rejected fast-forward), roll back the local commit with `git reset --hard HEAD~1`, then show the user a plain-language message: *"I made the fix locally but couldn't push it to GitHub — this branch may be protected, or a maintainer needs to let this project through. I've undone the local change. Options below."* Offer only two options: (a) "Open a help issue — a maintainer will set it up for me" and (b) "Cancel." Never ask the user to change branches or push manually.

4. **Continue to the normal flow** (propose slug/branch/domain, env vars, submit the deploy issue).

### What the skill must NOT do

- **Never edit without showing the diff first** and getting explicit Apply from the user. No silent modifications.
- **Never rewrite the whole file** — use the Edit tool with minimal old_string/new_string so comments and surrounding formatting are preserved.
- **Never ask the user about branches.** The user's current `HEAD` is their branch choice — commit and push there. Pushing to `main` is fine when the user is on `main`; the push-failure rollback path handles the protected-branch case without ever exposing the word "branch" to the user.
- **Never push a change that hasn't been validated locally.** Rule E runs `npm ci && npm run build`; Rules A-D run `docker compose config -q` (or a YAML parse fallback); Rule F re-runs Gates 1–2 and uses a nixpkgs pin verified server-side against the actual helper image. If validation fails, the change is restored to the working tree's pre-edit state and no commit is made. Pushing an unvalidated change would move the failure from the user's laptop (where we can gracefully offer a help-issue fallback) to the deploy runner (where the user sees a cryptic red × on a GitHub Action they didn't file).
- If the compose file uses extends, anchors, or other YAML features that make mechanical editing risky, bail to "I'll fix it manually" and tell the user why.

4. Propose defaults, but treat **domain** as special — it's the public URL, user-facing forever, and deserves its own focused question:
   - **Name** = the repo name (let the user override — the server slugifies whatever they pick, e.g. "My App" → "my-app").
   - **Branch** = current branch (or `main`).
   - **Domain** — **do NOT pre-fill the repo-slug as a "recommended" checkbox.** The repo slug (e.g., `sw-cuba` from a repo named `SW-CUBA`) is often a mechanical, unfriendly name; non-technical users tend to click "✓ recommended" without realizing the string will be visible in every URL users share for the rest of the app's life. Instead, ask the domain question *standalone*, in plain language, with the repo slug offered as a *suggestion* rather than a pre-selected default:

     ```
     question: "What public web address (domain) do you want for this app?"
     header: "Public URL"
     multiSelect: false
     options:
       - label: "<slug-of-repo>.eregistrations.dev"
         description: "Uses your repo name. Works fine but may not be the friendliest URL."
       - label: "Let me type a custom one"
         description: "Pick a short, friendly subdomain (e.g. 'cuba-home.eregistrations.dev'). Must end with .eregistrations.dev."
     ```

     If the user picks "Let me type a custom one," prompt for the subdomain with a second question, validate it matches `^[a-z0-9][a-z0-9.-]*[a-z0-9]\.eregistrations\.dev$`, and retry the prompt on invalid input with a plain-language hint about lowercase letters/digits/hyphens. **The `Name` field in the deploy issue is independent of the domain** — derive `Name` from the slug the onboarder will use internally (repo-slug by default, or user's explicit choice if they override Name too), and set `Domain` from the user's domain answer. The two can differ without confusion: `Name` is a Coolify-internal identifier, `Domain` is the public URL.
5. Show the user what you'll submit and ask for confirmation.
6. Ask about env vars (optional — "none" is fine).
7. **Run the pre-flight build gate** (see "## Pre-flight build gate" below) — `npm ci` then `npm run build` for Node `auto-detect`/`static` repos, the runner-toolchain check (Gate 3), plus the large-file & `.dockerignore` checks for all build types. This runs **even when no auto-fix path fired** — a correctly-configured repo still needs its lockfile, build, and toolchain compatibility verified. If a gate fails and can't be auto-fixed, bail to a help issue rather than filing a deploy that will fail server-side.
8. Post the issue. Show the URL. Done.

The user should need to answer **at most** a couple of questions to get a deploy running. When in doubt, propose a default and let them override — **except** for the domain, which is user-facing forever and should never be auto-accepted via a checkbox-style "recommended" nudge.

## Gathering env vars

**Detect first, ask only if needed.** Non-technical users have no way to answer "any environment variables?" — they don't know what their app reads. Showing the `<GENERATE>` / `<SET-IN-COOLIFY>` sentinel list as a prompt is technical-user jargon. The skill must infer the answer from the repo first, and only surface a question when there's something concrete to ask.

### Step 1 — Scan the repo for actual env-var references

Run these greps (each is cheap, one pass; bundle them in a single `Bash` call per family):

| Language / framework | Detection pattern | Notes |
|---|---|---|
| Vite SPA | `grep -rnE "import\.meta\.env\.[A-Z]" src/` | Only `VITE_`-prefixed vars are exposed to the browser; other `import.meta.env.*` refs are build-time only. |
| Next.js | `grep -rnE "process\.env\.[A-Z]" app/ pages/ lib/ src/` | `NEXT_PUBLIC_*` → client-side; everything else → server-side. |
| Node server (Express/Fastify/Nest) | `grep -rnE "process\.env\.[A-Z]" src/ server/ api/` | Server-side; all need to be set. |
| Python (Django/Flask/FastAPI) | `grep -rnE "os\.(environ\.get\|getenv)\(['\"][A-Z]" .` | Any hit. |
| Go | `grep -rnE "os\.Getenv\(['\"][A-Z]" .` | Any hit. |
| Ruby (Rails) | `grep -rnE "ENV\[['\"][A-Z]" app/ config/` | Any hit. |
| Any language | Check for `.env.example`, `.env.template`, `.env.sample`, `.env.dist` at repo root | These enumerate the *intended* env vars — treat as authoritative if present. |
| docker-compose (when build type is `dockercompose`) | Rule D already handles `${VAR}` extraction; feed those names into this flow so the env-var question is the same regardless of build type. |

Also inspect `package.json.dependencies` for clear signals: `@supabase/*`, `firebase`, `stripe`, `@auth0/*`, `next-auth`, `mongoose`, `pg`, `mysql2`, `@prisma/client` — each is a strong hint that a specific env var is required even if the user hasn't wired it yet. Add those to the candidate list with a plain-language description (e.g., `DATABASE_URL` → "connection string for your database").

### Step 2 — Classify what you found

After the scan, partition the candidate list into one of three buckets:

- **Empty bucket — no env vars needed.** Skip the question entirely. Tell the user in one line: *"Your app doesn't read any environment variables at runtime — skipping that step."* This is the common case for static SPAs (Figma exports, CRA demos, Astro static, etc.). Do **not** ask the question "just to be safe."
- **Non-secret bucket** — vars that clearly aren't secrets (e.g., `VITE_API_URL`, `NEXT_PUBLIC_SITE_URL`, `PORT`, `NODE_ENV`). These are safe to ask about in plain text; offer a default derived from context when possible (e.g., `VITE_API_URL` → suggest `https://<same-subdomain>-api.eregistrations.dev` or similar, let the user override).
- **Secret-shaped bucket** — anything matching `(PASSWORD|SECRET|TOKEN|KEY|DSN)$` or the specific var names `DATABASE_URL`, `REDIS_URL`, `MONGO_URL`, `JWT_SECRET`, `STRIPE_SECRET_KEY`, etc. Offer three options per var: (a) "Generate one for me" (expands to `<GENERATE>` or `<GENERATE:hex:32>` depending on expected shape — JWT secrets → hex 64, session secrets → hex 32, etc.), (b) "I'll set it in Coolify after deploy" (expands to `<SET-IN-COOLIFY>`), (c) "I have a value — I'll paste it" (free text; if it's pasted literal matches a real-secret shape, auto-swap to `<SET-IN-COOLIFY>` per the rule below).

### Step 3 — Ask once, in plain language, only for the actionable vars

Bundle all remaining questions into **one** `AskUserQuestion` (not one-per-var). Headings are plain-language, not sentinel syntax. Example for a small Next.js app with `DATABASE_URL`, `NEXTAUTH_SECRET`, `NEXT_PUBLIC_SITE_URL`:

```
question: "Your app needs a few settings before it can run. Here's what I found:"
header:   "App settings"
multiSelect: false
options:
  - label: "Configure them now"
    description: |
      • DATABASE_URL — connection string for your database.
        I don't know this yet — can you set it in Coolify after deploy?  [default]
        Paste it now (I'll redact it from the issue):  [free text]
      • NEXTAUTH_SECRET — session-signing secret.
        Generate one for me.  [default]
        I have one to paste.  [free text]
      • NEXT_PUBLIC_SITE_URL — your app's public URL.
        Default: https://<your-domain>/  [editable]
  - label: "Skip — I'll fill them in Coolify later"
    description: "All settings default to placeholders. Deploy will still build, but the app may not work until you set them in Coolify (https://coolify.singlewindow.dev)."
```

(The question shape is illustrative — the actual `AskUserQuestion` tool only supports simple options, so render the per-var breakdown in the question body, then use two outer options: "Configure now (show me the form)" vs "Set up later in Coolify." On "Configure now," follow up with a single free-text prompt where the user pastes values, and parse those into KEY=VALUE lines. Resist the urge to ask N sequential questions — batch everything into one round-trip.)

### Step 4 — Safety net: secret-shaped literals

**Handle secret-shaped literals helpfully, not defensively.** If a literal value the user pastes looks like a real secret (common prefixes like `sk_live_`, `ghp_`, `xox[bp]-`, `AKIA…`, or PEM headers, or a JWT-shape, or length > 200 chars), auto-swap to `<SET-IN-COOLIFY>` and tell the user once:

```
⚠  STRIPE_SECRET_KEY looks like a real secret. Posting it in a public GitHub issue
   would expose it. I've set it to <SET-IN-COOLIFY> instead. After deploy, paste
   the real value in Coolify (https://coolify.singlewindow.dev) and redeploy.
```

Do NOT interrogate every value. Do NOT refuse to post. The `<SET-IN-COOLIFY>` path is designed exactly for this; swap and move on.

### Why this shape

The screenshot-driven improvement: asking a non-technical user "any environment variables?" and showing them `<GENERATE:base64:N>` sentinels is a UX failure twice — first because they can't answer, second because the answer is almost always "no" for the static SPAs this skill most often handles. A single grep pass over `src/` determines that 80% of the time nobody needs to be asked anything. The remaining 20%, the skill asks a focused question about the specific vars it found, with defaults picked per variable-shape — and never mentions the word "sentinel" or a `<>` token in the user-facing copy.

## Pre-flight build gate — verify the deploy will actually build (mandatory, runs before Posting)

This gate runs for **every Node/buildable repo**, regardless of build type and **regardless of whether any auto-fix path fired**. It closes the gap left by Rule E, which only runs the build when the static-SPA auto-fix triggers (i.e. when `start` is missing). A repo that is *already* set up correctly — has both `build` and `start` — skips Rule E entirely, so without this gate nothing ever runs the deploy commands locally, and a broken lockfile or build error reaches Coolify unseen.

**Incident that motivated this (2026-06-03, SW-Comores):** the repo had a valid `start` script, so Rule E was skipped. Its `package-lock.json` carried wrong SRI `integrity` hashes (off by one base64 char) for several packages. Nixpacks runs `npm ci`, which strictly verifies every tarball against the lockfile and rejected the *genuinely-correct* registry tarballs as "corrupted" — the deploy died with `EINTEGRITY` after minutes of retries. A local `npm ci` would have caught it in seconds.

**When to run:** after build-type detection (and any auto-fix), before "## Building the issue body". Run **Gates 1–3** when `build type` is `auto-detect` or `static` **and** a `package.json` with a `build` script exists. Skip Gates 1–3 for `dockerfile`/`dockercompose` (the image build happens server-side with a repo-controlled base image; Rules A–D already pre-flight compose) — but always run the **Large-file & context checks** below, for every build type.

**Pre-check:** `command -v npm` must succeed. If npm is missing, skip Gates 1–3 with a one-line note (can't verify without it) and continue — do not block the deploy.

### Gate 1 — Clean install (catches corrupt / out-of-sync lockfile)

Run the deploy runner's exact install command in the repo:

```bash
npm ci --no-audit --no-fund
```

`npm ci` is strict: it requires `package-lock.json`, refuses to modify it, and verifies every tarball's `integrity`. This is the gate that catches the incident class — `npm install` would silently *repair* the bad lockfile and hide the problem until CI hits it.

- **No `package-lock.json`:** `npm ci` errors immediately, and the deploy would fall back to `npm install` (slower, non-reproducible). Offer to generate one with `npm install --package-lock-only`, commit as `chore: add package-lock.json for reproducible deploy`, using the **same guardrails and push/rollback flow as the compose auto-fix** (clean tree, upstream branch, graceful help-issue fallback on push failure).
- **`EINTEGRITY`, "tarball … seems to be corrupted", or "npm ci can only install … in sync with package.json":** the lockfile is corrupt or has drifted. Offer to regenerate it (reuse the auto-fix guardrails + confirmation):
  1. `rm -f package-lock.json && rm -rf node_modules`
  2. `npm install --no-audit --no-fund` — rebuilds the lockfile from the registry; integrity hashes now match the canonical published values.
  3. Re-run `npm ci` to confirm it passes.
  4. Commit `package-lock.json` as `fix: regenerate corrupt/out-of-sync lockfile`, push to the current branch (rollback-on-failure path).

  Plain-language question: *"Your project's dependency lock file is out of date and would make the deploy fail. Can I refresh it for you?"* → `{Yes, refresh and deploy (recommended) / Open a help issue instead}`.

### Gate 2 — Build (catches broken deps, TS errors, missing build output)

Only after Gate 1 passes:

```bash
npm run build
```

This is the same command Nixpacks runs. On failure, **do not file the issue** — show the plain-language message Rule E uses (*"I tried to prepare your project for deployment, but the build failed on my end. This means the deploy would fail too. No changes were committed."*), surface the last 20 lines of output, and offer only "Open a help issue" or "Cancel." Then confirm the expected output dir exists (e.g. `dist/` for Vite) — if not, bail the same way.

### Gate 3 — Runner toolchain compatibility (catches engine-gated optional deps)

Gates 1–2 run on the **user's laptop**, whose Node is usually newer than the deploy runner's. That gap hides a nasty failure class:

**Incident that motivated this (2026-08-18, designstudio):** Coolify's nixpacks (helper ≤ 1.0.15, nixpacks 1.41) builds with **Node 22.11.0** from its pinned nixpkgs snapshot. The repo used vite 8, which is rolldown-based and declares `engines: node ^20.19.0 || >=22.12.0`. On Node < 22.12, npm **silently skips optional dependencies whose engines aren't satisfied** ([npm/cli#4828](https://github.com/npm/cli/issues/4828)) — `npm ci` exited 0 but never installed `@rolldown/binding-linux-x64-gnu`, and `vite build` died with `Cannot find native binding`. Gates 1–2 passed locally (laptop Node 22.22); the lockfile was correct; `--force` and upgrading npm don't help. Only the runner's Node version matters.

**Detection** (run after Gate 1, while `node_modules` is populated). Fast-path signal: `vite` major ≥ 8 or `rolldown` present in `node_modules`. Generic check — scan installed packages' `engines.node` for minimums above the runner's Node:

```bash
node -e '
const fs=require("fs"),path=require("path");
const [rMaj,rMin]=[22,11]; // nixpacks runner Node (helper <=1.0.15, nixpacks 1.41)
const bad=[];
(function scan(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){
  if(e.name.startsWith("."))continue;
  const p=path.join(dir,e.name);
  if(!e.isDirectory())continue;
  if(e.name.startsWith("@")){scan(p);continue;}
  const pj=path.join(p,"package.json");
  if(!fs.existsSync(pj))continue;
  const eng=((JSON.parse(fs.readFileSync(pj,"utf8")).engines)||{}).node||"";
  for(const m of eng.matchAll(/>=\s*(\d+)\.(\d+)|\^(\d+)\.(\d+)/g)){
    const maj=+(m[1]||m[3]),min=+(m[2]||m[4]);
    if(maj>rMaj||(maj===rMaj&&min>rMin)){bad.push(e.name+" (engines.node: "+eng+")");break;}
  }
}})("node_modules");
if(bad.length){console.log("RUNNER-INCOMPATIBLE:");bad.forEach(b=>console.log("  "+b));process.exit(1);}
console.log("runner-compatible");
'
```

Heuristic, not a full semver solver — it targets the observed failure class (`>=22.12`-style minimums). If it exits 0, continue. If it flags packages, apply **Rule F**.

**Rule F — Runner Node too old for the toolchain** (BLOCKER, auto-fixable, repo-side).
Pin a newer nixpkgs snapshot in the repo's `nixpacks.toml` so the runner's `nodejs_22` resolves to ≥ 22.12. No Coolify UI change needed — Coolify's `NIXPACKS_NODE_VERSION=22` maps to `nodejs_22`, and the archive pin controls which nixpkgs provides it.

- *Fix:* create `nixpacks.toml` if absent (preserve and extend it if present — never clobber existing `[phases.*]` or `[start]` blocks) with:

  ```toml
  [phases.setup]
  nixpkgsArchive = "4684fd6b0c01e4b7d99027a34c93c2e09ecafee2"
  ```

  This revision (nixpkgs-unstable, 2025-05-24) provides `nodejs_22` = **22.14.0** — verified 2026-08-18 on the deploy server via `nixpacks build` inside `ghcr.io/coollabsio/coolify-helper:1.0.15`. If the repo already has `[phases.setup]`, add/replace only the `nixpkgsArchive` line. If `nixpkgsArchive` is already pinned to a snapshot with nodejs_22 ≥ 22.12, the gate passes — do nothing.
- *Verify:* re-run Gates 1–2 (must still pass), then `git add nixpacks.toml`, commit `fix(deploy): pin newer nixpkgs for Node >=22.12 toolchain`, push — using the **same guardrails and push/rollback flow as the compose auto-fix** (clean tree, upstream branch, graceful help-issue fallback on push failure).
- *Skip Rule F entirely* for `dockerfile`/`dockercompose` build types — those control their own base image.

**Traps — do NOT "fix" this any of these ways:**
- `NIXPACKS_NODE_VERSION=24` → nix-env fails: the pinned nixpkgs snapshot has no `nodejs_24`.
- `NIXPACKS_NODE_VERSION=23` → nixpacks 1.41 **silently falls back to `nodejs_18`** in the generated plan. Worse than 22.
- Upgrading the Coolify helper → doesn't help: helper 1.0.15 still ships nixpacks 1.41 with the same snapshot.
- `npm ci --force` / upgrading npm in the install phase → the engine-gating of optional deps follows the **Node** version, not the npm version.

Plain-language question (same shape as Rule E):

```
question: "Your app's build tools need a newer version of Node.js than the deploy server uses by default. Can I add a small config file (nixpacks.toml) that tells it to use a newer one?"
header: "Quick setup"
multiSelect: false
options:
  - label: "Yes, add it and deploy (recommended)"
    description: "I'll add a nixpacks.toml that pins a newer Node for the build servers. Standard configuration — safe to ignore once added."
  - label: "No — open a help issue instead"
    description: "Abort. A maintainer will help you deploy this app manually."
```

### Large-file & context checks (all build types, advisory — never block)

These prevent slow/fragile builds rather than outright failures:

- **Missing `.dockerignore`:** if absent, the entire repo — including `.git` — is shipped as the Docker build context. A `.git` bloated with media committed to history can push the context to hundreds of MB and exhaust the builder's disk mid-`npm`-extract, which itself manifests as *spurious* "tarball corrupted" retries. Offer to add a `.dockerignore` covering at least `.git`, `node_modules`, `dist`.
- **Tracked files > 50 MB:** `find . -path ./.git -prune -o -type f -size +50M -print`. Warn the user — GitHub flags these, and they bloat every clone and every build context; suggest Git LFS or moving the asset to object storage/CDN. (Incident reference: SW-Comores shipped a 619 MB context with no `.dockerignore`, plus 500+ MB of unused videos committed to history.)

**Why a gate and not just trust the auto-fix paths:** the auto-fix paths (Rule E, Rules A–D) only fire when something *needs* fixing. A correctly-configured repo skips them all — and that's exactly the repo whose *lockfile* or *transitive build* can still be silently broken. Running the deploy commands unconditionally, locally, is the only thing that guarantees "builds cleanly here → deploys cleanly there."

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
