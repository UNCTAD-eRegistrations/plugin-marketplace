# Phase 8 — Create the Coolify application

Create the Coolify application — **see the Coolify sections below.** Set env
vars matching a healthy sibling instance's pattern (`COUNTRY_DB`,
`SYSTEM_INSTANCE_ID`, `SHARED_SQL_HOST=eregulations-shared-sqlserver`,
`SA_PASSWORD` — **must be byte-identical to the shared sqlserver's actual value, not freshly generated; pull it from a sibling app's env vars or
ask the operator directly** — `CONSISTENCY_DB`/`STATISTICS_DB`, domains,
`CONTENT_DIR`, image tags — pin to whatever tag sibling instances use, e.g.
`:user-rights`, not `:latest`), including `INSTANCE` and `PUBLIC_DOMAIN`
(referenced by the compose file's basic-auth labels even when you don't use
basic auth) and the three SSO vars (see the SSO section below — not
wired in `docker-compose.yml`, easy to miss; these three, unlike
`SA_PASSWORD`, should be freshly generated per instance). See the env-var-quirks section below for how to actually set these via the API. Then
set `docker_compose_domains` and deploy.

## Coolify control panel may be a separate host

The Coolify *dashboard/API* and the *server you're deploying to* are commonly
different machines — Coolify's normal architecture is one central instance
managing many remote "servers" over SSH, with only a lightweight
`coolify-sentinel` agent (plus `coolify-proxy`/Traefik for app traffic)
running on the managed host itself. `docker ps` on the target host showing
just those two containers, and nothing listening on port 8000, means you're
on a managed server, not the control plane — ask the operator for the
Coolify dashboard's own base URL (e.g. `https://coolify.example.com`) rather
than assuming it's reachable on the deploy target.

## Coolify API git access

Coolify's REST API has separate creation endpoints per git-auth type:
`/api/v1/applications/public`, `/private-deploy-key`, `/private-gh-app`,
`dockercompose` doesn't exist as its own endpoint (404) — `dockercompose` is
a `build_pack` value you pass to one of the above.

**`/applications/public` silently accepts a `git@host:org/repo.git` SSH URL
at creation time and returns 200 — then every deploy fails instantly with
`Permission denied (publickey)`**, because that endpoint never attaches any
key at all. There's no error at creation to warn you. If a deploy fails in
under ~10 seconds with no containers ever created, this is almost always why
— check the deployment's log via the web UI (`{coolify_url}/project/.../
deployment/{uuid}`; the API's `/deployments/{uuid}` endpoint doesn't expose
log content).

Fix: delete the app, recreate via `/api/v1/applications/private-deploy-key`
with a `private_key_uuid` for a key that's actually registered as a GitHub
deploy key on that repo. **Don't call `GET /api/v1/security/keys` to pick
one** — it returns the actual private key material in plaintext (every field
including `private_key`), not just metadata, so it's both a needless credential exposure and not actually where you want to look first. Instead, cross-
reference a sibling app that already deploys successfully from the same repo:
`GET /api/v1/applications` and find one with the same `git_repository`, read
its `private_key_id` (a small integer), then look that same numeric `id` up
in the `/security/keys` list to get the matching `uuid` — this proves the key
is *actually working* rather than merely registered. `private_key_uuid` can
only be set at creation; it's rejected on `PATCH` after the fact.

Also: `docker_compose_domains` can't be set until `docker_compose_raw` is
populated, which only happens after a deploy has actually cloned the repo
successfully — so the first deploy (with a working key) runs without proper
domain routing, then you `PATCH` `docker_compose_domains` and redeploy once
more. Each service entry needs **both** `name` and `domain` — `{"public":
{"domain": "https://..."}}` alone 422s with `docker_compose_domains.public.name
field is required`; `name` is just the service key repeated
(`{"public": {"name": "public", "domain": "https://<instance-domain>"}}`).

## Coolify env var API quirks

Coolify pre-populates one blank env var entry per `${VAR}` reference in the
compose file the moment the app is created — before you've set anything.
`POST /api/v1/applications/{uuid}/envs` (create) then 409s on every one of
those keys. Use `PATCH /api/v1/applications/{uuid}/envs` instead (same
collection endpoint, not a per-var URL — `PATCH .../envs/{env_uuid}` 404s)
with `{"key": "...", "value": "...", "is_preview": false}`; it upserts by
key regardless of whether the key already exists, so you can use it for
every variable instead of POST-then-PATCH-on-409.

Every variable also exists in two copies — `is_preview: false` (what your
actual, non-preview deployment uses) and `is_preview: true` (Coolify's
separate slot for PR/preview-deployment builds). If you're not using preview
deployments, a leftover blank value on the `is_preview: true` copy is
harmless noise, not a bug — don't chase it.

`SA_PASSWORD` is the one variable that must match the shared sqlserver's
actual value, not be freshly generated per instance (unlike the SSO values above). If you try to read it out of a sibling app's env vars
programmatically and that gets blocked by a credential-handling safeguard,
don't route around the block — ask the operator to paste the value
directly instead.

## SSO env vars

Not wired anywhere in `docker-compose.yml` — set directly as Coolify app env
vars, per instance, or the public site's "Go to Admin" link and any
admin↔public handoff silently does nothing (no error, just a dead link):

- `AppSettings__AdminApiUrl` (public service) — same value as `ADMIN_API_URL`,
  just under a config key nothing else derives it from.
- `AppSettings__SsoSharedSecret` (public service) and
  `ApplicationSettings__SsoSharedSecret` (admin-api service) — must be
  byte-identical to each other. This is validated per-instance
  (`UserController`: public POSTs `{username, sharedSecret}` to admin-api's
  `/api/user/sso/generate`, which checks it against
  `_applicationSettings.SsoSharedSecret`) — there's no code path where one
  instance's public site talks to a different instance's admin-api, so a freshly generated value per instance is correct; it does not need to match
  sibling instances' values.
