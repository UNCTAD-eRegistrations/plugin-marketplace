---
name: create-draft-instance
description: >
  Create a draft (UAT) instance configuration for an eRegistrations LIVE instance,
  and wire the LIVE side to point at it. Strips LIVE-only services (keycloak, bpa-*,
  websocket, public-pages-*), adds the publisher service, rewrites own-domain refs
  to `draft.<base>.eregistrations.org`, keeps cross-refs (BPA, Keycloak) pointing at
  LIVE, and patches LIVE bpa-backend `EXTERNAL_SERVERS` + gdb `GDB_CLIENT_URL_1`.
  Keycloak-only — CAS instances are out of scope. Use when standing up a new draft
  alongside an existing LIVE instance for UAT of upcoming platform versions.
license: UNCTAD-Internal
compatibility: Requires access to the eRegistrations Conf-LIVE / Conf-PREVIEW configuration repository (eregistrations-v4).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(ls *), Bash(diff *), Bash(git *), Bash(yq *), AskUserQuestion, TodoWrite
metadata:
  version: "1.4.1"
  version-date: "2026-05-05"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<live-instance-name> [draft-prefix]"
  jira: "TOBE-17813"
---

You are an expert eRegistrations DevOps engineer. Your task is to generate a Conf-PREVIEW draft instance configuration from an existing Conf-LIVE instance, and patch the LIVE config to wire UAT cross-references back to the draft.

## Authoritative reference

`Conf-LIVE/compose/kenya/docker-stack.yml` is the authoritative LIVE-side template. It carries the full active draft wiring (`EXTERNAL_SERVERS`, `GDB_CLIENT_URL_1`) and is the most modern Keycloak + Swarm config in the repo. When in doubt about LIVE shape or env-var conventions, defer to kenya.

For PREVIEW shape, follow `Conf-PREVIEW/compose/apiex/docker-stack.yml` and `Conf-PREVIEW/compose/burundi/docker-compose.yml` — both are Keycloak-based drafts. Output emits docker-stack.yml (Swarm) regardless of the legacy compose format some PREVIEW samples still carry.

## Core Capabilities

1. Resolve a LIVE instance under `Conf-LIVE/compose/<instance>/docker-stack.yml`
2. Generate `Conf-PREVIEW/compose/<instance>/docker-stack.yml` (Swarm shape)
3. Generate `Conf-PREVIEW/haproxy/<instance>/haproxy.cfg`
4. Patch LIVE `bpa-backend.environment.EXTERNAL_SERVERS` and `gdb.environment.GDB_CLIENT_URL_1`
5. Surface non-blocking warnings (Keycloak clients, DBs, secrets that must be pre-created)

## Reasoning Principles

1. **Kenya is canonical**: when the structure of an env block, secret list, or service block is ambiguous, copy kenya's shape verbatim — do not invent new patterns.

2. **Keycloak-only**: refuse to operate on CAS instances. The skill is forward-looking; CAS is being dropped and is not supported.

3. **Strip strictly, keep loosely**: only strip the explicit LIVE-only set (keycloak, bpa-*, websocket, public-pages-* and aliases). Anything else stays — including `mule-<country>`, `mule4-<country>`, country-specific extensions. When unsure, keep it; the operator can prune by hand.

4. **Domain rewriting is contextual**:
   - Own-domain references → `<prefix>.<base>.eregistrations.org` (where `<prefix>` defaults to `draft`)
   - Own-subdomain references (`gdb.`, `stats.`, `graylog.`, `ds.`) → `<sub>.<prefix>.<base>.eregistrations.org`
   - LIVE BPA URLs (`bpa.<live-domain>`) **stay literal** — draft uses LIVE BPA
   - LIVE Keycloak URLs (`login.<live-domain>`) **stay literal** — draft uses LIVE Keycloak

5. **Image versions copy 1:1**: do NOT auto-bump. The platform-version upgrade is a separate workflow (`/upgrade-eregistrations-instance`).

6. **Memoize prior answers** within a session: ask each question once, reuse answers if user re-runs.

7. **Fail loud, not silent**: surface every assumption that depends on out-of-scope state (Keycloak clients, DBs, secrets) as an explicit warning before exit.

## Out of Scope

The following are NOT handled by this skill:

- **CAS instances** — CAS is being deprecated platform-wide. If the LIVE source has a `cas-backend` / `cas-frontend` service, abort with guidance.
- **Keycloak realm / client provisioning** — `draft-` prefixed clients (`draft-camunda`, `draft-ds`, `draft-statistics-backend`, `draft-statistics-frontend`, `draft-gdb`, `draft-publisher`) must be created out-of-band in the LIVE Keycloak realm. The skill warns; it does not create them.
- **Database creation** — Postgres / Mongo databases (`display_system`, `gdb`, `statistics`, `camunda`, `cashier`, `formio`, `restheart`, `graylog`) must be pre-created on the draft host's DB. The skill warns.
- **Docker secrets initialization** — secrets must be initialized on the draft Swarm via `init-swarm.sh`. The skill warns.
- **DNS / certificate provisioning** — `<prefix>.<base>.eregistrations.org` and its subdomains must resolve to the draft host before haproxy will start.
- **Image version upgrades** — copies LIVE versions verbatim. Use `/upgrade-eregistrations-instance` afterwards if the draft should run a newer platform version.
- **Compose-mode (legacy non-Swarm) output** — emits Swarm `docker-stack.yml` only.
- **PREVIEW-instance teardown** — this skill is create-only. Removing a draft is a manual operation (until a separate `/remove-draft-instance` exists).

If the user asks for any of the above, explain the scope and point at the right tool / runbook.

## Workflow

### Phase 1: Input gathering

Use **AskUserQuestion** to gather inputs. If `$ARGUMENTS[0]` was provided, treat it as the instance name and skip Question 1. If `$ARGUMENTS[1]` was provided, treat it as the draft prefix and skip Question 2.

**Question 1 — LIVE instance name:**
```
question: "Which LIVE instance should the draft be created from?"
hint: "Must be a directory under Conf-LIVE/compose/<name>/ with a docker-stack.yml"
```

Validate: `Conf-LIVE/compose/<instance>/docker-stack.yml` exists. If `docker-compose.yml` exists instead (legacy compose-mode), abort: "Instance is still on docker-compose.yml — run `/docker-swarm-migration` first."

**Question 2 — Draft prefix:**
```
question: "What subdomain prefix should the draft use?"
options:
  - label: "draft (Recommended)"
    description: "Modern convention — produces draft.<base>.eregistrations.org"
  - label: "preview"
    description: "Legacy convention used by some older instances"
  - label: "Custom"
    description: "Specify a different prefix (e.g. 'investissement', 'staging')"
default: "draft"
```

**Question 3 — Draft base domain:**
```
question: "What is the draft's base eregistrations.org subdomain?"
hint: "Usually <country>.eregistrations.org, e.g. 'kenya.eregistrations.org'. The full draft URL becomes <prefix>.<base>"
default: "<instance>.eregistrations.org"
```

For the kenya example the full draft domain is `draft.kenya.eregistrations.org`.

**Question 4 — Draft host bridge gateway IP:**
```
question: "What is the bridge gateway IP on the draft host?"
hint: "Used for postgres_host / docserver_mongo / REDIS_HOST extra_hosts. Typical values: 172.17.0.1, 172.18.0.1, 172.19.0.1"
default: "172.18.0.1"
```

**Question 5 — Draft host DB host (extra_hosts target):**
```
question: "What IP should `postgres_host` and `mongodb_host` resolve to on the draft host?"
hint: "Same as bridge IP if Postgres/Mongo run as containers on the draft host. Different IP (e.g. 10.0.0.2) if they run on a separate DB host."
default: "<value-from-Question-4>"
```

**Question 6 — Patch LIVE for UAT wiring:**
```
question: "Should LIVE be patched in this run to wire EXTERNAL_SERVERS + GDB_CLIENT_URL_1?"
options:
  - label: "Yes — patch LIVE now (Recommended)"
    description: "Add the 4 env vars to LIVE bpa-backend and gdb"
  - label: "No — emit draft only"
    description: "Skip the LIVE patch; user will wire it manually"
default: "Yes"
```

**Question 7 — Branch / commit behavior:**
```
question: "How should the changes be committed?"
options:
  - label: "Create branch + commit + open PR (Recommended)"
    description: "feature/<instance>-draft-instance, one commit, gh pr create"
  - label: "Commit on current branch"
    description: "Use the active branch as-is"
  - label: "No commit — leave changes in working tree"
    description: "User reviews and commits manually"
default: "Create branch + commit + open PR"
```

### Phase 2: Validate LIVE source

Run these checks in order. Each is a hard abort — surface the message and stop.

1. **Swarm-shape check (compose-mode rejection)**: if `Conf-LIVE/compose/<instance>/docker-stack.yml` does NOT exist but `Conf-LIVE/compose/<instance>/docker-compose.yml` does, abort with:
   > Instance `<instance>` is still on legacy `docker-compose.yml`. Draft generation requires Swarm shape. Run `/docker-swarm-migration` against the LIVE instance first, merge that, then re-run `/create-draft-instance`.
   This check is duplicated from Phase 1 input validation deliberately — it remains the second hard gate so the skill cannot silently proceed on compose-mode input.
2. Read `Conf-LIVE/compose/<instance>/docker-stack.yml` fully into memory.
3. **CAS rejection**: if any service block is named `cas-backend` or `cas-frontend`, OR any env var matches `AUTH_SERVICE_TYPE=CAS`, abort with the CAS out-of-scope message.
4. **Keycloak presence**: there must be a `keycloak:` service block — if not, abort: "Could not detect Keycloak service in LIVE; this skill assumes a Keycloak-based instance."
5. Detect the LIVE primary domain. Strategy:
   a. Look for the most-frequently-occurring domain in `DISPLAY_HOME=`, `BASE_URL=`, `EREG_CMS_BACKEND=`, `PARTA_URL=`, `E_REGISTRATIONS_HOME_URL=`, `KC_HOSTNAME:` values.
   b. Strip protocol, trailing slash, and known subdomain prefixes (`bpa.`, `gdb.`, `stats.`, `graylog.`, `ds.`, `login.`, `eid.`, `partc.`, `services.`, `myaccount.`, `home-*.`, `admin-*.`).
   c. The remaining bare domain is the LIVE primary (e.g. `investkenya.go.ke`, `myaccount.investkenya.go.ke` for kenya).
   d. Show it to the user and ask for confirmation if multiple candidates tie.
6. Detect LIVE Keycloak URL — usually `https://login.<live-primary>` or `https://login.<sibling-live-domain>`. Persist it; PREVIEW services keep it literal.
7. Detect LIVE BPA URL — usually `https://bpa.<live-primary>`. Persist it; PREVIEW services keep it literal.
8. Detect SYSTEM_CODE, KEYCLOAK_REALM, KEYCLOAK_INSTITUTIONS_GROUP_ID, TIME_ZONE — copy from LIVE camunda / ds-backend / gdb env blocks.

### Phase 3: Service-set transformation

Apply this exact rule set when building the PREVIEW service map. Every service block in LIVE is processed once.

**Strip from LIVE (drop completely):**

| LIVE service name | Reason |
|---|---|
| `keycloak` | Draft uses LIVE Keycloak realm; no own KC instance |
| `bpa-frontend` | Draft uses LIVE BPA |
| `bpa-backend` | Draft uses LIVE BPA |
| `websocket` | Tied to BPA; lives on LIVE |
| `pp-backend` / `pp-frontend` | Public pages are LIVE-side only |
| `public-pages-backend` / `public-pages-frontend` / `public-pages-next` | Same as above (kenya names them `backend` / `frontend` — match by image, not name) |
| any service whose `image:` starts with `unctad/public-pages-` | Catch-all for naming variants |
| any service whose `image:` starts with `unctad/bpa-` (frontend/backend/websocket) | Catch-all |

Match by **image name**, not by service block name — kenya names the public-pages blocks `backend` / `frontend`, while apiex names them `pp-backend` / `pp-frontend`.

**Keep from LIVE (carry over with transformations from Phase 4):**

All other services. Including:
- `portainer`, `activemq`, `graylog`, `opensearch-node1`, `formio`, `restheart`, `camunda`, `mule`, `dataweave`, `chrome-url-to-pdf`, `clamav`
- `ds-backend` (rename: `license-registry` → `gdb` if encountered, but kenya already uses `gdb`)
- `cashier`, `js-assistant`, `gdb`, `statistics-backend`, `statistics-frontend`, `ds-frontend`
- Country-specific mule extensions: `mule-<country>`, `mule4-<country>`
- `minio`, `minio-init`

If an unknown LIVE-only service is detected (image namespace `unctad/*` not in the keep list and not stripped above), use **AskUserQuestion** with options "Keep" / "Strip" / "Show env block first".

**Add (PREVIEW-only):**

`publisher` — modeled on the kenya PREVIEW publisher block (`unctad/publisher:2.17`, env vars for FORMIO, RESTHEART, INTERNAL/EXTERNAL Keycloak auth, `BOT_SWAGGER_URLS`, `GDBS_URL=http://gdb:8080`, `LOCAL_COUNTRY_MULE_URL` listing every kept `mule-*` service). Use `draft-publisher` as the Keycloak client ID.

### Phase 4: Per-service transformations

Apply these rewrites to each kept service:

**Domain rewrites** (in env-var values, image-tag fields are exempt):

```
<live-primary>           → <prefix>.<base>.eregistrations.org
<sub>.<live-primary>     → <sub>.<prefix>.<base>.eregistrations.org   (for sub in gdb, stats, graylog, ds)
bpa.<live-primary>       → (kept literal — BPA stays on LIVE)
login.<live-primary>     → (kept literal — Keycloak stays on LIVE)
eid.<live-primary>       → (kept literal — only relevant for legacy CAS, but skill should pass through)
partc.<live-primary>     → (kept literal)
services.<live-primary>  → (kept literal — public-pages on LIVE)
admin-*.<live-primary>   → (kept literal — public-pages admin on LIVE)
home-*.<live-primary>    → (kept literal)
```

**Keycloak client IDs**: each draft service uses a `draft-` prefixed client in the LIVE realm. Mapping:

| Service | LIVE client ID | PREVIEW client ID |
|---|---|---|
| camunda | `camunda-client` | `draft-camunda-client` |
| ds-backend | `ds-client` | `draft-ds-backend-client` |
| ds-frontend | `display-system-frontend` | `draft-ds-frontend-client` |
| statistics-backend | `statistics-backend` | `draft-statistics-backend` |
| statistics-frontend | `statistics-frontend` | `draft-statistics-frontend` |
| gdb | `gdb-client` | `draft-gdb-client` |
| publisher | n/a (new) | `draft-publisher` |
| mule | `camunda-client` (shares camunda's) | `draft-camunda-client` |

Naming is not strictly mechanical — `statistics-*` keep their LIVE names without `-client` suffix, while DS clients gain the `-backend-`/`-frontend-` qualifier even though LIVE is less explicit. The skill emits the exact strings above; do not derive at runtime.

`KEYCLOAK_INSTITUTIONS_GROUP_ID` and `KEYCLOAK_REALM` are copied verbatim from LIVE.

The skill emits a Keycloak client seeding script alongside the docker-stack.yml — see Phase 5b.

**Specific service env tweaks** (mirror what kenya / apiex PREVIEW do):

- **graylog**: `GRAYLOG_HTTP_EXTERNAL_URI` and `GRAYLOG_TRANSPORT_EMAIL_WEB_INTERFACE_URL` → `https://graylog.<prefix>.<base>.eregistrations.org/`. Bridge IPs in `extra_hosts` swap to draft host bridge IP.
- **camunda**: `DISPLAY_HOME` → `https://<prefix>.<base>.eregistrations.org`. `KEYCLOAK_URL` stays literal (draft uses LIVE KC). `KEYCLOAK_RESOURCE=draft-camunda`.
- **mule**: `DISPLAY_MACHINE_EXTERNAL_LINK` → draft domain. `AUTH_SERVICE_URL` stays literal (LIVE KC). `AUTH_RESOURCE=draft-camunda`.
- **mule-`<country>`**: keep as-is, but if `MULE_ENV` / `ENV` are present, leave the values alone — both `live` and `draft` are observed in the wild and the choice is country-specific.
- **ds-backend**: `ALLOWED_HOSTS` rewritten for draft domain + bridge IP. `ADDITIONAL_ALLOWED_FRAMES` updated. `EREG_CMS_BACKEND`, `PARTA_URL`, `RESTHEART_PUBLIC_URL`, `STATS_URL`, `NEW_FRONTEND_ORIGIN`, `REDIRECT_ANONYMOUS_URL`, `STRAPI_UPLOAD_URL` → draft variants. `BPA_URL` stays literal. `AUTH_SERVICE_BACKEND_URL` / `AUTH_SERVICE_PUBLIC_URL` stay literal. `AUTH_SERVICE_CLIENT_ID=draft-ds-backend-client`. **Standard ds-backend extras** (always emit; absent in LIVE source means `unctad/eregcms` will use defaults that may not be desirable on a draft): `CHROME_URL_TO_PDF_URL=https://<draft-domain>/chrome-url-to-pdf`, `ADMIN_ERROR_REPORTS_ENABLED=1`, `CACHE_FORMS=True`, `PREVENT_AUTO_GOOGLE_TRANSLATION=False`, `DEFAULT_REQUESTS_TIMEOUT_SECONDS=30`, `GUNICORN_HTTP_TIMEOUT=120`, `REDIRECT_ANONYMOUS_URL=https://<draft-domain>`, `DOCKER_NETWORK=<draft-host-bridge-cidr>` (e.g. `172.18.0.0/16`). `GA_ID` is intentionally NOT carried over (LIVE's analytics ID does not belong on a draft — operator can set per-instance via the deployment bootstrap if telemetry is wanted).
- **Mail / SMTP env vars are critical and MUST be preserved**: `MAIL_*` (mule), `EMAIL_*` (camunda, ds-backend, gdb, publisher), `GRAYLOG_TRANSPORT_EMAIL_*` (graylog) — keep all keys. **VALUES** are deployment-specific: LIVE typically points at AWS SES (`email-smtp.eu-west-1.amazonaws.com:587` with an `AKIA*` access-key ID), while drafts often use the country's own SMTP relay (e.g. lesotho2 draft → `ping.eregistrations.org:25` no-auth + `MAIL_USER=none` + from-address `no-reply@eregulations.org`). The skill should preserve LIVE's mail-key inventory verbatim and SURFACE the host/port/user/from values with a warning so the operator can decide whether to swap them for the draft's SMTP gateway. `EMAIL_SERVER_PASSWORD` secret stays in the secrets block even when `MAIL_USER=none` (no-auth) — the secret is still referenced by some images and dropping it triggers `secret not found` failures on deploy.
- **gdb**: `ALLOWED_HOSTS` includes `gdb.<prefix>.<base>.eregistrations.org`. `CORS_ORIGIN_WHITELIST=https://bpa.<live-primary>` (LIVE BPA). `AUTH_SERVICE_*_URL_1` stay literal. `AUTH_SERVICE_CLIENT_ID_1=draft-gdb`. `DS_URL=https://gdb.<prefix>.<base>...`. `APP_TITLE="<prefix-titlecase> <Country>"` (e.g. `"Draft Kenya"`). The 3 `GDB_CLIENT_URL_1` lines from LIVE are NOT carried over to PREVIEW.
- **statistics-backend**: `ALLOWED_HOSTS`, `FE_BASE_URL` → draft. KC client `draft-statistics-backend`.
- **statistics-frontend**: `API_BASE_URL`, `DS_URL` → draft. `BPA_URL` stays literal. `APP_TITLE="<Country> - <prefix>"`. KC client `draft-statistics-frontend`.
- **ds-frontend** (if present in LIVE): `BASE_URL`, `BASE_API_URL`, `RESTHEART_URL`, `OAUTH_REDIRECT_URL`, `WS_URL`, `STATS_URL` → draft. `BPA_URL` stays literal. `KEYCLOAK_URL` stays literal.
- **portainer**, **activemq**, **dataweave**, **chrome-url-to-pdf**, **clamav**, **js-assistant**: copy verbatim.
- **All published ports MUST use Swarm long-form `mode: host`** (post-2.17→2.18 convention). Convert any short-form `- "<published>:<target>"` mapping to:
   ```yaml
   - target: <target>
     published: <published>
     protocol: tcp
     mode: host
   ```
   This bypasses Swarm's ingress mesh so the haproxy frontend on the draft host sees real client IPs (no SNAT) and the eRegistrations apps' rate-limit/log/audit logic stays meaningful. Applies to every service that publishes ports — portainer, activemq, graylog, formio, restheart, camunda, mule, mule-`<country>`, minio, ds-backend, ds-frontend, cashier, gdb, statistics-backend, statistics-frontend, clamav, publisher, chrome-url-to-pdf.
- **opensearch-node1**: copy verbatim.
- **formio**, **restheart**: docserver_mongo / mongodb_host extra_hosts swap to draft bridge IP. Otherwise verbatim.
- **cashier**: postgres_host swap to draft bridge IP. Verbatim otherwise.
- **minio**, **minio-init**: copy verbatim from kenya PREVIEW pattern. Do NOT touch user directives, mem/cpu reservations, or healthcheck.

**Networks block** (Swarm shape): replace whatever LIVE has with the standard draft block:

```yaml
networks:
  ingress:
    external: true
    driver: overlay
  eregistrations_default:
    driver: overlay
  bridge:
    external: true
    driver: bridge
```

If LIVE uses additional named networks (e.g. `fortinet`), warn the user and ask whether to carry them over.

**Secrets block** (Swarm shape): copy LIVE's secrets list, **dropping** secrets that only kept services don't reference (e.g. `BPA_DB_PASSWORD`, `BPA_BE_OAUTH_SECRET`, `KEYCLOAK_DB_PASSWORD`, `STRAPI_DB_PASSWORD`, `VITE_GA_MEASUREMENT_ID`, etc. — anything used solely by stripped services). Add `PUBLISHER_OAUTH_CLIENT_SECRET` (used by the new publisher service).

**Secret naming normalization** — LIVE source may use either `_OAUTH_SECRET` or `_OAUTH_CLIENT_SECRET` for the four confidential KC client secrets (kenya/lesotho2 LIVE use the short form; bootstrap convention is the long form). The skill MUST emit the long form: `CAMUNDA_OAUTH_CLIENT_SECRET`, `DS_OAUTH_CLIENT_SECRET`, `GDB_OAUTH_CLIENT_SECRET`, `STATS_BE_OAUTH_CLIENT_SECRET`, `PUBLISHER_OAUTH_CLIENT_SECRET`. When the LIVE source has the short form, rename both the secret declaration and every `DOCKER_SECRET:<name>` reference inside service env blocks. The matching `<instance>-draft-keycloak-secrets.env` mirror keys (Phase 5b output) MUST also use the long form so `init-swarm.sh` on the draft host loads Docker secrets under the names that `docker-stack.yml` references.

**Container-level cleanup**: drop `extra_hosts` entries that pointed at services no longer in the stack (e.g. anything pointing at `<live-primary>` or referencing stripped services).

### Phase 5: PREVIEW haproxy.cfg

Generate `Conf-PREVIEW/haproxy/<instance>/haproxy.cfg` modeled on existing PREVIEW haproxy files (apiex / burundi / kenya share the same shape). Key elements:

- No `crt-base` directive (bootstrap convention is a single combined cert at a fixed path; `crt-base` is only useful when each domain gets its own Letsencrypt-managed dir)
- `bind *:443 ssl crt /etc/haproxy/haproxy.crt alpn h2,http/1.1` — single combined PEM at `/etc/haproxy/haproxy.crt`. The operator concatenates cert+key+chain into that one file at deploy time (same convention as LIVE eRegistrations stacks).
- Standard frontends: `stats` (8444), `www_80` (HTTP→HTTPS redirect), `www-https` (the 443 frontend)
- ACLs and denies for: swagger, form-preview3, restheart actions/users/acl, formio paths (with forbidden-endpoints whitelist support)
- Path ACLs: `is_restheart`, `is_mule`, `is_publisher`, `formio_path`, `is_options`, `is_stat_be_path`
- Host ACLs: `is_display_system` (`<prefix>.<base>...`), `is_stats` (`stats.<prefix>.<base>...`), `is_ds_frontend` (`ds.<prefix>.<base>...` — only if ds-frontend is kept)
- `use_backend` rules: restheart_backends, mule_backends, publisher_backends, cors (OPTIONS), display_system, formio, graylog_backends (Host match), statistics_backends/frontend, gdb_backends (Host match)
- Backends: `cors`, `display_system → 127.0.0.1:6020`, `formio → :3001`, `gdb_backends → :3003`, `graylog_backends → :9005`, `mule_backends → :8081`, `restheart_backends → :9080`, `statistics_frontend → :4205`, `statistics_backends → :6021`, `publisher_backends → :6050`. Add `ds_frontend → :<published-port>` only if ds-frontend was kept (port is whatever the docker-stack.yml publishes — `4201` and `4202` are both observed).
- Drop CAS, partC, BPA backends — they don't run on draft.

**MANDATORY when ds-frontend is kept** — without this block the new Angular DS frontend is unreachable and `/` redirects in a loop (`/?redirectTo=/?redirectTo=...&next=...`):

1. **New-DS-frontend path ACLs** (paths served by the Angular ds-frontend container, NOT ds-backend's old display_system on port 6020):
   - `is_ds_frontend_path`   path beg `/parta/`
   - `is_ds_frontend_path_1` path beg `/services/`
   - `is_ds_frontend_path_2` path beg `/manage-business-entity/`
   - `is_ds_frontend_path_3` path beg `/redirect/`
   - `is_ds_frontend_path_4` path beg `/business-list`
   - `is_ds_frontend_path_5` path beg `/login`
   - `is_ds_frontend_path_6` path beg `/version`
   - `is_ds_frontend_path_7` path beg `/health`
   - `is_ds_frontend_path_8` path reg `^(\/{0,1}$)` (root path)
2. **New Angular module path ACLs**: `is_ds_partb_path` (`/part-b`), `is_partb_edit_path` (`/part-b/edit` — stays on display_system!), `is_ds_inspector_path` (`/inspector`), `is_ds_financial_report_path` (`/financial-report`), `is_ds_files_path` (`/files`)
2a. **Angular static-asset extension ACL** — without this, `.map` (sourcemaps), `.js`, `.css`, `.svg`, font, image extensions on the main draft host fall through to ds-backend (Django) and 404 noisily in logs:
    ```
    acl is_angular_asset path_reg -i \.(js|css|js\.map|css\.map|svg|woff2?|ttf|eot|png|jpg|jpeg|ico|webp|html)$
    use_backend ds_frontend if is_display_system is_angular_asset
    ```
    Place this `use_backend` BEFORE the path-based new-Angular routing so the asset shortcut wins.
3. **Language-prefix redirects** (strip `^/<2-letter>/` from `/part-b`, `/inspector`, `/financial-report`; rewrite `/files` → `/inspector`)
4. **Form-preview / WS sub-routing of display_system** (ds-backend exposes 4 different ports for these features):
   - `is_form_preview_pdf` path beg `/form-preview-pdf/` AND `is_form_preview_pdf_backend` path beg `/backend/form-preview-pdf/` → **display_system2** (`127.0.0.1:6028`)
   - `is_form_preview3` (raw deny ACL above; legitimate path) AND `is_form_preview3_backend` path beg `/backend/form-preview3/` → **display_system3** (`127.0.0.1:6029`)
   - `is_display_system_ws` path beg `/backend/ws/user-updates-stream/` + `Connection: upgrade` + `Upgrade: websocket` → **display_system_ws** (`127.0.0.1:6024`, `timeout tunnel 24h`)
5. **`use_backend ds_frontend`** for every new-DS path AND new-Angular path (with `!is_partb_edit_path` exclusion so /part-b/edit/* stays on display_system).
6. **`use_backend display_system`** must be guarded with `!is_form_preview_pdf !is_form_preview_pdf_backend !is_form_preview3 !is_form_preview3_backend` to NOT swallow form-preview/ws traffic.

The `display_system_ws`, `display_system2`, `display_system3` backends are MANDATORY whenever the matching ds-backend ports (`6024`, `6028`, `6029`) are published. They are not optional even if the new-DS frontend is missing.

Also create `Conf-PREVIEW/haproxy/<instance>/forbidden-endpoints-whitelist.lst` (empty file or copy from LIVE — empty is safer; user can populate).

### Phase 5b: Keycloak client seeding script + pre-generated secrets

Generate `Conf-PREVIEW/compose/<instance>/init-keycloak-clients.sh` — a self-contained bash script that uses the Keycloak Admin REST API to create the seven `draft-*` clients in the LIVE realm, modeled on the canonical client representations under `templates/`. Five of the seven are confidential and carry pre-generated secrets; two (`draft-ds-frontend-client`, `draft-statistics-frontend`) are public and have no secret.

The script is idempotent: each client is created via PUT-on-UUID if it exists, otherwise POST. Redirect URIs and web origins are templated from the new draft domain so the same script can seed any instance.

**Secret pre-generation** (in-memory, at skill run time):

For each of the five confidential clients, generate a fresh 32-byte hex secret:

```bash
openssl rand -hex 32
```

The generated secrets are used in two places:
1. **Embedded as the `secret` field** of each client representation in the seeding script's POST/PUT body — Keycloak honors the supplied `secret` on create.
2. **Written to a `<instance>-draft-keycloak-secrets.env` file** outside the eregistrations repo (default: `~/<instance>-draft-keycloak-secrets.env`, or operator-chosen via Question 8 below). The file maps each secret to its matching draft-host env-var name so it can be sourced by `init-swarm.sh` on the draft host.

The mapping (matches the env-var names used by Conf-PREVIEW/compose/<instance>/docker-stack.yml services):

| Client ID | env-var name (in `.env` / Docker secret) |
|---|---|
| `draft-camunda-client` | `CAMUNDA_OAUTH_CLIENT_SECRET` |
| `draft-ds-backend-client` | `DS_OAUTH_CLIENT_SECRET` |
| `draft-gdb-client` | `GDB_OAUTH_CLIENT_SECRET` |
| `draft-publisher` | `PUBLISHER_OAUTH_CLIENT_SECRET` |
| `draft-statistics-backend` | `STATISTICS_BE_OAUTH_CLIENT_SECRET` |

The seeding script itself is git-tracked, but the values flow through env vars at runtime — `init-keycloak-clients.sh` is parameterized on `KC_CLIENT_SECRET_<NAME>` env vars and refuses to run if any are unset. The script never embeds the actual secrets into git-tracked files.

**Question 8 — secrets output path:**
```
question: "Where should the pre-generated draft-* client secrets be written?"
hint: "MUST be outside the eregistrations-v4 repo. Default ~/<instance>-draft-keycloak-secrets.env"
default: "~/<instance>-draft-keycloak-secrets.env"
```

Validate that the path is outside the repo root (refuse to write inside `Conf-LIVE/`, `Conf-PREVIEW/`, or any other tracked dir). If the file exists, ask before overwriting.

**Reference templates** live as sanitized JSON files under `templates/` next to this `SKILL.md`. They are the canonical kenya-draft client representations with KC-assigned UUIDs stripped, secrets removed, and the kenya-specific draft domain / realm replaced by literal `${DRAFT_DOMAIN}` and `${REALM}` placeholders. Per-client artefact set:

```
templates/<client-id>.client.json.tpl              # ClientRepresentation
templates/<client-id>.default-scopes.json.tpl      # array of scope NAMES
templates/<client-id>.optional-scopes.json.tpl     # array of scope NAMES
templates/<client-id>.protocol-mappers.json.tpl    # array of mapper objects (only present if non-empty)
templates/<client-id>.sa-user.json.tpl             # SA user representation (confidential clients only)
templates/<client-id>.sa-realm-roles.json.tpl      # SA realm-level role mappings (FLAT ARRAY of RoleRepresentation; confidential clients only)
templates/<client-id>.sa-role-mappings.json.tpl    # SA composite role mappings (OBJECT with .realmMappings + .clientMappings; confidential clients only)
```

**Refreshing the templates**: edit the `.tpl` files directly when client shape changes (new scopes, new mappers, new redirect URI patterns). Bump `metadata.version-date` in this `SKILL.md` when committing template changes so consumers can see when templates last drifted.

#### Assembly algorithm (skill runtime)

When the skill produces `init-keycloak-clients.sh` for a new instance, it builds a single self-contained bash file that ships with the inlined client representations as bash heredocs. Steps:

1. **Generate fresh client secrets** (in memory):
   ```
   KC_CLIENT_SECRET_CAMUNDA   = openssl rand -hex 32
   KC_CLIENT_SECRET_DS        = openssl rand -hex 32
   KC_CLIENT_SECRET_GDB       = openssl rand -hex 32
   KC_CLIENT_SECRET_PUBLISHER = openssl rand -hex 32
   KC_CLIENT_SECRET_STATS_BE  = openssl rand -hex 32
   ```
   Public clients (`draft-ds-frontend-client`, `draft-statistics-frontend`) get no secret.

2. **Write secrets file** (outside the repo, 0600 perms) — see Phase 8 file list for layout.

3. **Resolve per-instance values** (Phase 2 detected):
   - `DRAFT_DOMAIN` = `<prefix>.<base>.eregistrations.org`
   - `REALM` = LIVE realm (e.g. `ke`, `BJ`, `BI`)
   - `LIVE_KC_URL` = LIVE Keycloak URL (e.g. `https://login.investkenya.go.ke`)
   - `INSTANCE_LOGIN_THEME` = take from kenya template's `attributes.login_theme` (`"kenya"` in templates) and replace with the new instance's theme name (default: `<instance>`); ask user via AskUserQuestion if the LIVE Keycloak doesn't have a matching theme deployed yet.

4. **Per-client substitutions** (apply to each `<cid>.client.json.tpl`):
   - Replace literal `${DRAFT_DOMAIN}` → resolved draft domain
   - Replace literal `${REALM}` → resolved realm
   - Replace literal `"kenya"` (under `attributes.login_theme`) → `INSTANCE_LOGIN_THEME`
   - For confidential clients, inject `"secret": "<KC_CLIENT_SECRET_*>"` at the top level

5. **Emit `init-keycloak-clients.sh`**: a self-contained script that contains:
   - Header: `KC_BASE`, `REALM`, `DRAFT_DOMAIN` defaults sourced from skill detection
   - Required-env-var guards on `KC_CLIENT_SECRET_*`
   - `get_token()`: admin-cli password grant against `realms/master`
   - `upsert_client(repr_var)`: POST if new, PUT if exists (matched by `clientId`); for confidential clients also `POST /clients/{uuid}/client-secret` to force-set the secret on update paths
   - `assign_default_scopes(client_uuid, scope_names_var)`: for each scope name, GET `/client-scopes` to find the scope UUID, then PUT `/clients/{uuid}/default-client-scopes/{scope-uuid}`
   - `assign_optional_scopes(...)`: same pattern for optional scopes
   - `assign_sa_realm_roles(client_uuid, sa_realm_roles_var)`: input is the **flat array** from `sa-realm-roles.json.tpl` — extract names with `jq -r 'if type == "array" then .[].name else (.realmMappings // [] | .[].name) end'` (the `if` form is defensive in case a future template ships the composite shape instead). Skip any role matching `default-roles-*` (KC auto-assigns); for other realm role names, GET `/roles/{name}` to fetch role obj, POST the accumulated array to `/users/{sa-user-uuid}/role-mappings/realm`
   - `assign_sa_client_roles(client_uuid, sa_role_mappings_var)`: input is the **composite object** from `sa-role-mappings.json.tpl`; iterate `.clientMappings | keys[]` for container clientIds, resolve each container's UUID, fetch each named role from `.clientMappings[<cid>].mappings[].name`, POST to `/users/{sa-user-uuid}/role-mappings/clients/{container-uuid}`
   - For each of the seven clients, an inline heredoc with the substituted JSON, followed by:
     - `upsert_client "$CLIENT_REPR"` → captures returned/looked-up `client_uuid`
     - `assign_default_scopes` and `assign_optional_scopes`
     - For confidential clients only: `GET /clients/{uuid}/service-account-user` → capture `sa_user_uuid`, then `assign_sa_realm_roles` and `assign_sa_client_roles`
   - **`seed_client` MUST end with an explicit `return 0`.** Otherwise the function inherits the exit code of its last `[ -n "${!var:-}" ] && fn` test; for public clients (no SA / no protocol-mappers templates), several of those tests evaluate false, the function returns 1, and the tolerant outer loop reports a phantom failure even though every API call succeeded.

6. **Wrap each per-client invocation in a tolerant subshell** so a single client's failure does NOT abort the rest of the seeding:
   ```bash
   declare -a FAILED=()
   for cid in <list>; do
     set +e
     ( set -e; seed_client "$cid" )
     rc=$?
     set -e
     [ "$rc" -ne 0 ] && FAILED+=("$cid")
   done
   ```
   At the end print the failure list and exit non-zero only if `${#FAILED[@]}` > 0.

7. **Per-instance scope override**: for `draft-camunda-client`, `draft-ds-backend-client`, `draft-ds-frontend-client`, append `"eregistrations"` to `defaultClientScopes` in the substituted client repr (the eregistrations realm scope is the standard role-mapper aggregator on these three clients across all UNCTAD instances). The other four draft clients keep the standard 6-scope default. The seeding script's PUT/POST sends the augmented array; KC honors the assignment idempotently.

8. **Per-instance theme handling**: KC realms set `Login theme` and `Email theme` at the realm level (e.g. `lesotho` on `LS`). A per-client `login_theme` attribute takes precedence over the realm theme — undesirable for drafts, which should always inherit the realm theme. The `seed_client` function MUST defensively force-clear `login_theme` on every upsert by re-setting it to empty in the substituted repr:
   ```bash
   CLIENT_REPR=$(jq '.attributes."login_theme" = ""' <<<"${!repr_var}")
   upsert_client "$CLIENT_REPR"
   ```
   This is required because KC PUT does not remove unspecified attributes; any residual `login_theme` from a prior POST persists unless the body explicitly overwrites it. Templates SHOULD also be free of `login_theme` (the kenya-derived public-client templates have it stripped in this skill's `templates/`).

9. **Write to** `Conf-PREVIEW/compose/<instance>/init-keycloak-clients.sh` (executable, 0755 perms).

**Idempotency contract**: re-running `init-keycloak-clients.sh` against a realm that already has the seven `draft-*` clients must not corrupt them. The script:
- Matches clients by `clientId` (not by UUID, which differs between runs)
- PUTs the representation when the client exists; POSTs when it doesn't
- Force-sets the secret via `POST /clients/{uuid}/client-secret` after every PUT (KC PUT does not always honor the inline `.secret` field)
- Skips `default-roles-<realm>` in SA role assignments (KC auto-assigns; explicit assignment can fail with 409)
- Drains `client-roles` blocks idempotently — KC returns 204 if a role mapping already exists

**Lockstep with draft-host secrets**: the same `KC_CLIENT_SECRET_*` values that the seeding script POSTs to KC are also written to `~/<instance>-draft-keycloak-secrets.env` for the operator to ship to the draft host (via `scp` + Docker secrets / `init-swarm.sh`). KC-side and draft-host-side stay aligned without console rotation.

### Phase 6: Patch LIVE for UAT wiring

If Question 6 was "Yes":

1. **bpa-backend**: in `Conf-LIVE/compose/<instance>/docker-stack.yml`, set:
   ```
   - "EXTERNAL_SERVERS=[{\"id\":\"<PrefixTitleCase>\", \"name\": \"<PrefixTitleCase>\", \"host\":\"https://<prefix>.<base>.eregistrations.org\"}]"
   ```
   - If the line exists and is commented, uncomment and replace.
   - If the line exists and is uncommented, validate it matches; if not, ask the user before overwriting.
   - If the line doesn't exist, insert it within `bpa-backend.environment`, near the bottom of the env list, between the `JAVA_OPTS=` and `AI_USERNAME=` lines if those are present, otherwise at the end.

2. **gdb** (or `license-registry` for older instances): add the 3-line block:
   ```
   # Reference: https://unctad.atlassian.net/browse/TOBE-15219?focusedCommentId=56293
   - "GDB_CLIENT_URL_1=https://gdb.<prefix>.<base>.eregistrations.org"
   - "GDB_CLIENT_AUTH_ID_1=0"
   - "GDB_CLIENT_EXPORT_ALL_SCHEMAS_1=True"
   ```
   - Same idempotent rules: replace if present, insert at bottom of `gdb.environment` if not.

3. Do NOT modify LIVE haproxy — the LIVE haproxy needs no changes; the draft is on its own host with its own haproxy.

### Phase 7: Commit + PR (if Question 7 selected branch+PR)

1. Verify branch with `git -C <repo> branch --show-current`.
2. Create branch `feature/<instance>-draft-instance` from current HEAD (always create new — never reuse an existing branch unless user explicitly directs).
3. Stage only the files this skill produced/modified — never `git add -A`.
4. Commit. Message format follows the repo convention (see memory: instance-first, no co-authored, prefix `feat:`):
   ```
   feat: <instance> add draft instance config and wire LIVE for UAT TOBE-XXXXX
   ```
   Ask the user for the ticket id (don't make one up).
5. `git push -u origin feature/<instance>-draft-instance`.
6. `gh pr create` with title and a body listing: services stripped, services added (`publisher`), domain rewrites applied, LIVE wiring patches. Assignee `@me`, reviewer `benoumemen`.

If Question 7 was "Commit on current branch": skip step 2, commit on whatever branch is checked out (after confirming with user).

If Question 7 was "No commit": skip 2-6 entirely.

### Phase 8: Final summary + warnings

Print a single block to stdout:

```
=== create-draft-instance summary ===
Instance:        <instance>
Draft domain:    <prefix>.<base>.eregistrations.org
Auth model:      Keycloak (realm <realm>, LIVE KC at <live-kc-url>)
Files written (in repo, git-tracked):
  Conf-PREVIEW/compose/<instance>/docker-stack.yml                    (NEW, <N> services)
  Conf-PREVIEW/compose/<instance>/init-keycloak-clients.sh            (NEW, executable, parameterized on env vars)
  Conf-PREVIEW/haproxy/<instance>/haproxy.cfg                         (NEW)
  Conf-PREVIEW/haproxy/<instance>/forbidden-endpoints-whitelist.lst   (NEW, empty)

Files written (outside repo, sensitive — DO NOT commit):
  ~/<instance>-draft-keycloak-secrets.env                             (NEW, 0600 perms)
    KC_CLIENT_SECRET_CAMUNDA=<random-32-byte-hex>
    KC_CLIENT_SECRET_DS=<random-32-byte-hex>
    KC_CLIENT_SECRET_GDB=<random-32-byte-hex>
    KC_CLIENT_SECRET_PUBLISHER=<random-32-byte-hex>
    KC_CLIENT_SECRET_STATS_BE=<random-32-byte-hex>
    # Mirror values for draft-host Docker secrets:
    CAMUNDA_OAUTH_CLIENT_SECRET=<same-as-KC_CLIENT_SECRET_CAMUNDA>
    DS_OAUTH_CLIENT_SECRET=<same-as-KC_CLIENT_SECRET_DS>
    GDB_OAUTH_CLIENT_SECRET=<same-as-KC_CLIENT_SECRET_GDB>
    PUBLISHER_OAUTH_CLIENT_SECRET=<same-as-KC_CLIENT_SECRET_PUBLISHER>
    STATISTICS_BE_OAUTH_CLIENT_SECRET=<same-as-KC_CLIENT_SECRET_STATS_BE>
Files patched:
  Conf-LIVE/compose/<instance>/docker-stack.yml                       (bpa-backend.EXTERNAL_SERVERS, gdb.GDB_CLIENT_URL_1)
Services stripped from LIVE → not in PREVIEW:
  keycloak, bpa-frontend, bpa-backend, websocket, <public-pages-blocks>, <other>
Services added in PREVIEW:
  publisher
Services kept (carried over with transformations):
  <list>

=== ACTION REQUIRED before deploying draft ===
  [ ] Create draft Keycloak clients in LIVE realm <realm>:
        draft-camunda-client, draft-ds-backend-client, draft-ds-frontend-client,
        draft-gdb-client, draft-publisher,
        draft-statistics-backend, draft-statistics-frontend
        (mule shares draft-camunda-client)
        → set -a; source ~/<instance>-draft-keycloak-secrets.env; set +a
        → bash Conf-PREVIEW/compose/<instance>/init-keycloak-clients.sh
        Secrets are pre-generated and embedded in the .env file — no console rotation needed.

  [ ] Copy the same secrets to the draft host's .env (or Docker secrets):
        scp ~/<instance>-draft-keycloak-secrets.env <draft-host>:<draft-stack-dir>/.env.keycloak
        Then run init-swarm.sh on the draft host to load them as Docker secrets:
          DS_OAUTH_CLIENT_SECRET, CAMUNDA_OAUTH_CLIENT_SECRET,
          GDB_OAUTH_CLIENT_SECRET, PUBLISHER_OAUTH_CLIENT_SECRET,
          STATISTICS_BE_OAUTH_CLIENT_SECRET
  [ ] Pre-create draft DBs on the draft host:
        Postgres: display_system, gdb, statistics, camunda, cashier
        Mongo:    formio, restheart, graylog
  [ ] Initialize Docker secrets on the draft Swarm:
        cd Conf-PREVIEW/compose/<instance> && bash init-swarm.sh
        (init-swarm.sh is generated by the docker-swarm-migration / correct-db-passwords skills,
         not by this skill — run them next if absent)
  [ ] DNS: ensure <prefix>.<base>.eregistrations.org and gdb./stats./graylog./ds. CNAMEs point at the draft host
  [ ] Letsencrypt: provision certs for the four (or three) draft hostnames
  [ ] Verify LIVE patch deployed: bpa-backend env now exposes the EXTERNAL_SERVERS dropdown to BPA admins
```

The summary lines should be exact — operators paste them into Jira.

## Idempotency

A re-run on the same instance should:
1. Detect existing `Conf-PREVIEW/compose/<instance>/docker-stack.yml` and ask before overwriting.
2. Detect existing LIVE EXTERNAL_SERVERS / GDB_CLIENT_URL_1 lines that match the target — leave them alone.
3. Show a diff before any destructive write.

## Common pitfalls

- **Forgot to flag CAS abort**: catch in Phase 2; CAS instances exist (lesotho, elsalvador) but are out of scope.
- **Stripped a country mule**: `mule-<country>` and `mule4-<country>` MUST stay; only `mule` (the generic) plus stripped frontends/backends are touched. Match by image, not by name pattern.
- **Bridge IP collision**: if the draft host shares Docker networks with another stack on the same machine, 172.17.0.1 / 172.18.0.1 may already be taken. Operator must verify on the host.
- **Cert path mismatch**: haproxy `bind` directive expects `/etc/haproxy/haproxy.crt` — a single combined PEM (cert + intermediate chain + private key concatenated) that the operator creates at deploy time on the draft host. eRegistrations LIVE/preview stacks use this single-file convention (NOT per-domain Letsencrypt dirs).
- **Touching minio resource limits**: existing memory note — don't change `mem_reservation` / `cpus` on minio or minio-init during sync. Copy verbatim.
- **`extra_hosts` for stripped services**: scrub them; otherwise haproxy / mule will fail DNS for vanished container names.
- **Infinite `/?redirectTo=/?redirectTo=...&next=...` loop** on the draft's root URL: the haproxy is missing the new-DS-frontend path block. The root `/` lands on the OLD display_system backend (ds-backend port 6020) because no rule diverts root to the Angular ds-frontend (port 4201/4202). ds-backend then redirects to itself with `?redirectTo=`; each round-trip URL-encodes the previous redirect, accumulating `&next=` from a second mechanism. Fix: add the full new-DS-frontend ACL + use_backend block from Phase 5 (mandatory when ds-frontend is kept).
- **`Not Found: /<component>.css.map` 404 spam** in ds-backend logs: Angular per-component sourcemaps (and other build artefacts: `.js`, `.css`, fonts, images) live on ds-frontend (nginx), but without the `is_angular_asset` extension ACL they fall through to ds-backend (Django) and 404. Fix: add the `is_angular_asset` rule from Phase 5 step 2a — places extension-based asset requests on ds_frontend before the path-based routing kicks in.

## Notes

- Authoritative LIVE template: `Conf-LIVE/compose/kenya/docker-stack.yml` (Keycloak + Swarm + 2.17 + already-wired EXTERNAL_SERVERS / GDB_CLIENT_URL_1).
- Authoritative PREVIEW shape: `Conf-PREVIEW/compose/apiex/docker-stack.yml` and `Conf-PREVIEW/compose/burundi/docker-compose.yml` (Keycloak; apiex is the cleaner Swarm-mode reference).
- Authoritative KC client templates: shipped as sanitized JSON under `templates/` in this skill directory. Originally derived from the kenya draft realm; refresh by editing the `.tpl` files directly when client shape needs to change.
- Companion skill: `/upgrade-eregistrations-instance` — run after draft creation if the draft should run a newer platform version than LIVE.
- Companion skill: `/correct-db-passwords` — run on the draft host if Postgres / Mongo passwords drift from `.env`.
- Companion skill: `/docker-swarm-migration` — run on LIVE first if it's still on legacy `docker-compose.yml`.
