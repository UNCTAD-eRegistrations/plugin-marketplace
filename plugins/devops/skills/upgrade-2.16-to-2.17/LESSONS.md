# Lessons learned — upgrade-2.16-to-2.17

Retrospective from running the 2.16→2.17 step as part of the elsalvador LIVE 2.13→2.18 chain (May 2026).

## Rule 5b (`ds-frontend` add) overlaps with cas-to-keycloak-migrate-apps and neither owns it

The 2.16→2.17 step has a Rule 5b that adds the `ds-frontend` service block when missing. The `cas-to-keycloak-migrate-apps` STEP 4.5 has env-var rules for ds-frontend with a note "if absent, leave it alone — Rule 5b adds it." Both skills defer to each other; the result is that an instance which never had ds-frontend (e.g. elsalvador LIVE — shipped the legacy `eregcms` UI on `ds-backend` since 2.13) ends both chains *still* without the service.

On elsalvador LIVE the operator drove the question: "ds-frontend service still missing, it was not added as you expected." The agent had explicitly skipped Rule 5b citing "Phase 6 of the cas-to-keycloak chain creates it" — which it doesn't. The whole rollout reached the post-cutover smoke test before the gap surfaced.

**Patch:** Rule 5b should be **deprecated** (made a no-op with a warning, or removed entirely). The right place to own ds-frontend creation is `cas-to-keycloak-migrate-apps/STEP 4.5` — it's a CAS→KC concern, not a 2.16→2.17 mechanical bump. See `cas-to-keycloak-migrate-apps/LESSONS.md` lesson #20 for the receiving side.

## Country-image renames the skill performs but doesn't sweep

Rule 2 renames `unctad/eregbpafrontend → bpa-frontend`, `eregbpabackend → bpa-backend`, `eregcms → ds-backend`, `license-registry → gdb`. The IMAGE references are rewritten cleanly. What the skill DOESN'T touch (but probably should):

1. **Service block names** — `service: eregcms:` stays `eregcms:` even though the image is now `unctad/ds-backend:`. Other LIVE countries all use `ds-backend:` as both the service-block key and the image. This isn't broken (Docker doesn't care what the service block is named), but it diverges from convention and confuses readers.

2. **Internal hostname references in env vars** — `ALLOWED_HOSTS=…,license-registry,…` (gdb on the new image, but internal DNS still resolves the old name only if the service block name is also `license-registry`). On elsalvador LIVE the operator caught this when verifying ds-backend networking — internal references to `http://license-registry:8080/swagger.json` worked accidentally because the service block was still named `license-registry`; if it had been renamed to `gdb:` (per convention), the internal-hostname refs would have broken until updated.

The split is: Rule 2 owns the **image** rename; nothing else does the **service block name** + **internal hostname ref** rewrites. The convention-following way is to do all three together.

**Patch:** extend Rule 2 (or add Rule 2b) to do the service-block-name rename and an internal-hostname-ref sweep when the image is renamed:

| Image-rename pair | Service block rename | Hostname-ref rewrite |
|---|---|---|
| `eregbpafrontend → bpa-frontend` | (already `bpa-frontend:` on most instances) | n/a |
| `eregbpabackend → bpa-backend` | (already `bpa-backend:` on most instances) | n/a |
| `eregcms → ds-backend` | `eregcms:` → `ds-backend:`, but check first | `,eregcms,` → `,ds-backend,`, `http://eregcms:` → `http://ds-backend:` |
| `license-registry → gdb` | `license-registry:` → `gdb:` | `,license-registry,` → `,gdb,`, `http://license-registry:` → `http://gdb:` |

Idempotent: if the service is already named `gdb:`, skip silently.

## ds-frontend OAuth `client_id` template mismatch (`display-system-frontend` vs `ds-fe-client`)

Rule 5b adds a `ds-frontend:` service block (when missing) modeled on the mali docker-stack.yml — including `OAUTH_CLIENT_ID=display-system-frontend`. But the realm template at `eregistrations-starter-conf/scripts/keycloak-realm.template.json` (consumed by `cas-to-keycloak-prepare-realm`) creates the public client as `ds-fe-client`. Result: a freshly-generated realm has no client named `display-system-frontend`, so the auth flow from ds-frontend fails with a 400 (Keycloak can't resolve the client_id) — or worse, falls back to `ds-client` (the backend confidential client) and surfaces a redirect_uri mismatch.

On elsalvador LIVE the redirect_uri 400 was the operator-visible symptom; the underlying cause was the mali template mismatch.

**Patch options:**
1. **Update the mali template** in Rule 5b to use `OAUTH_CLIENT_ID=ds-fe-client`. Simple but assumes the realm always uses this name.
2. **Resolve from realm.json at apply-time**: read `Conf-<UPPER_ENV>/compose/<country>/keycloak-realm.json`, find the public client (`publicClient: true`) whose name matches either convention, use that. Robust against future realm renames.
3. **Update mali's own compose** to match the starter-conf convention, then the template stays correct. Cuts at the source.

Option 3 is the cleanest long-term. Option 1 is the quickest patch. Option 2 is the most defensive.

## Opensearch volume paths assume `/opt/volumes/opensearch/...` already exists

Rule 5 bumps `opensearchproject/opensearch:2.12.0 → 2.19.4`. The data is persisted in `/opt/volumes/opensearch/data` (per the compose). On a fresh upgrade the directory already exists (created in 2.13→2.14 step 3.6), so the bump is a re-pull + re-mount and the data carries over. On elsalvador LIVE the upgrade worked cleanly because the 2.13→2.14 step had already created the volume.

But there's a latent risk: the major bump from 2.12 to 2.19 crosses **multiple OpenSearch major versions** with breaking index changes. Production data may not auto-migrate cleanly. Kenya's running 2.19.4 on indices originally created under 2.12 with no issue, but a production upgrade should still take a snapshot first.

**Patch:** add a STEP 2 confirmation prompt — "OpenSearch jumps 2.12.0 → 2.19.4 (3 major versions). Have you taken an OpenSearch snapshot (`POST /_snapshot/<repo>/<name>`) or confirmed indices auto-migrate cleanly? (y/N)" with default-abort. The BACKUP_CONFIRMED flag covers Postgres backups but OpenSearch needs its own gate.

## DS-backend port mapping for the WebSocket endpoint isn't covered

The skill bumps the ds-backend image but doesn't ensure the WS port (`6024:8081`) is mapped. Kenya's compose has both `6020:8080` (HTTP) and `6024:8081` (WS) on ds-backend; elsalvador's only had `6022:8080` (HTTP), even after the 2.16→2.17 step. The DS frontend's `WEBSOCKET_INTEGRATION_ACTIVE=1` reconnects forever without the WS port + haproxy route.

This is adjacent to lesson 5b above — both gaps lead to "DS frontend doesn't fully work after the upgrade."

**Patch:** add Rule 5c: ensure `ds-backend.ports` includes the WS port mapping (default `6024:8081`, or whatever the country convention uses). Idempotent.

## Quick reference — where each lesson landed

| # | Lesson | Patch landing site |
|---|---|---|
| 1 | Rule 5b (ds-frontend add) and cas-to-keycloak-migrate-apps STEP 4.5 both defer to each other | deprecate Rule 5b; move ownership to cas-to-keycloak-migrate-apps |
| 2 | Image rename in Rule 2 doesn't touch service-block name or internal hostname refs | Rule 2b: service-block rename + internal hostname sweep |
| 3 | Mali ds-frontend template hardcodes `OAUTH_CLIENT_ID=display-system-frontend`; starter-conf realm uses `ds-fe-client` | update Rule 5b template OR resolve client name from realm.json at apply-time |
| 4 | OpenSearch 2.12 → 2.19 major-version jump has no operator backup gate | new STEP 2 anomaly + confirmation prompt |
| 5 | ds-backend WebSocket port mapping not added (kenya has 6024:8081, others typically don't) | new Rule 5c: ensure `ds-backend.ports` includes `6024:8081` |
