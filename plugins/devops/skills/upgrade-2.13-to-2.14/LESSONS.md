# Lessons from 2.13 → 2.14 upgrades on existing instances

Captures the non-mechanical gotchas — Keycloak realm drift, the `KEYCLOAK_CLIENT_SCOPE_ID` env var, swarm vs `$VAR` interpolation, missing `ds-frontend` service, HAProxy gaps. The mechanical rules are in `SKILL.md`; this file is the **why** behind STEP 3.7 and the post-handoff manual steps the skill cannot automate.

Cross-references TOBE-17814 (chain orchestration) and the prelive.benin / Burundi-2.18-prep incident (May 2026) which surfaced most of these.

## Why a realm patch is needed at all

Fresh-deployed instances built via the `cas-to-keycloak-prepare-realm` / `-seed` pipeline ship with the canonical realm shape: the `display-system-frontend` OIDC client, the `eregistrations` client scope (with `firstName` / `lastName` / `institution` / `unit` protocol mappers), declarative user-profile attributes, and the realm-management role grants every backend service-account needs.

Instances **upgraded from 2.13** carry an older realm dump (CAS-era migration, ~2023). That dump is missing all four things. The 2.14+ application code assumes they're present and fails hard when they aren't:

- **bpa-backend** publish flow calls `GET /admin/realms/<realm>/client-scopes/<KEYCLOAK_CLIENT_SCOPE_ID>` via the bpa-backend service account. Without `view-clients` on `realm-management`, the call returns `403`. Without the `eregistrations` scope existing, the env var resolves to a UUID that doesn't exist. Both surface as `KeycloakConnectionException: HTTP 403 Forbidden` in `ServicePublishController`.
- **ds-backend** log enrichment (`apps/utilities/logging_utils.py:_enrich_with_user_data`) does `record.user = str(user_data["sub"])` with unguarded bracket access. If the issued token lacks `sub`, the filter itself raises `KeyError: 'sub'` from inside Django's exception logger, masking the real request error. `sub` is missing whenever the consuming client has no default OIDC scopes attached — which is exactly what happens to `display-system-frontend` after a `partialImport` (see next section).

## What gets emitted, and why each file is separate

Keycloak's `POST /admin/realms/<realm>/partialImport` accepts only `clients`, `groups`, `roles`, `identityProviders`, and `users`. **It silently drops `clientScopes`** — the field is parsed and ignored. So:

- `partial-import.json` → clients only (`display-system-frontend`).
- `client-scope.json` → `eregistrations` scope. Posted to `/admin/realms/<realm>/client-scopes` separately. The starter template ships hardcoded UUIDs for the scope and each protocol mapper; those would collide with existing entities or fail validation. `strip_ids()` removes every `"id"` key recursively so Keycloak generates fresh ones on POST.
- `user-profile.json` → declarative user-profile config (`firstName`, `lastName`, `nationalNumber`, `birthDate` attributes). PUT to `/admin/realms/<realm>/users/profile` — realm components aren't carried by partial import at all.
- `apply.sh` → orchestrates the four PUT/POSTs plus the scope-attachment loops and realm-management role grants.

The scope attachment is the second non-obvious step. `partial-import.json` carries `defaultClientScopes: [web-origins, profile, roles, email, eregistrations]` on the client, but those are stored as **names**, not UUIDs. Keycloak resolves them against the realm's current scope set at import time; any name that doesn't yet exist is silently dropped. `eregistrations` was created in step 1b (after partial-import in step 1a), so the import sees no match — and the standard OIDC scopes (`web-origins`, `profile`, `roles`, `email`) appear to also drop in some Keycloak versions when the `clientScopes` block in the import body lists them by name. Net result: the client ends up with **zero** default client scopes, the issued token lacks `sub`, ds-backend's log filter raises `KeyError`. The fix in `apply.sh` step 1c: after partial-import + scope creation, iterate the 5 names and PUT `/clients/<uuid>/default-client-scopes/<scope-uuid>` for each.

## Realm-management role grants on backend service accounts

Both the starter realm template and `cas-to-keycloak-prepare-realm/keycloak-realm.json` assign **minimal** roles to every backend service account: `offline_access`, `bot`, `uma_authorization` realm roles + `account: [view-profile, manage-account]` client roles. None of those are sufficient for the admin-API calls 2.14+ backends make.

Specifically:
- `bpa-backend` calls `/client-scopes/<id>` (publish flow), `/groups/<id>`, `/groups/<parentId>/children` (institution lookup), and `POST /groups/<parentId>/children` (institution creation).
- `ds-client`, `gdb-client`, `camunda-client`, `statistics-backend` each make their own admin reads.

The role set `view-clients` + `view-realm` + `view-users` + `query-groups` + `manage-users` (from the `realm-management` client) covers all observed call paths without granting destructive admin powers. `apply.sh` step 4 grants this set to each backend client's service-account user, idempotent (409 on re-run).

Deployed countries running fine today (Kenya, Mali, etc.) presumably got these roles added manually post-deploy. The starter template and the historical seed flow never did. This is a long-standing latent bug surfaced by the bpa-backend publish 403.

## The KEYCLOAK_CLIENT_SCOPE_ID env var — not auto-inserted by this skill

The env var first appeared in `7e51bf3c2` (Sept 2024, elsalvador DEV on `EREGISTRATIONS_VERSION=2.14`) and is now present on 7 instances (timor, sandbox, lesotho2, syria, colombia-test, and a couple of others). All carry it as a **literal UUID** matching the eregistrations scope's id in that realm's Keycloak.

Earlier drafts of this skill auto-inserted `- "KEYCLOAK_CLIENT_SCOPE_ID=$KEYCLOAK_CLIENT_SCOPE_ID"` on bpa-backend. That's wrong for two reasons:

1. **Swarm doesn't expand `$VAR` in stack files.** The chain operates on `docker-stack.yml`. `docker stack deploy -c docker-stack.yml <stack>` passes the literal string `$KEYCLOAK_CLIENT_SCOPE_ID` to the container's environment. Only `docker compose -f docker-stack.yml config | docker stack deploy -c -` does interpolation, and that's not how production deploys run.
2. **The UUID isn't known until after the realm patch runs.** Keycloak generates a fresh ID for the `eregistrations` scope on POST. The operator needs to read it back (`GET /admin/realms/<realm>/client-scopes` and find the `name == "eregistrations"` entry's `id`) and put that literal into `docker-stack.yml`.

Manual post-handoff step the operator runs after the upgrade PR merges and `apply.sh` succeeds:

1. Resolve the scope id: `curl -sf -H "$AUTH" "$KC_URL/admin/realms/<realm>/client-scopes" | jq -r '.[] | select(.name == "eregistrations") | .id'`
2. Open a follow-up PR adding `- "KEYCLOAK_CLIENT_SCOPE_ID=<that-uuid>"` to bpa-backend's `environment:` list, right after `KEYCLOAK_RESOURCE=bpa-backend`.
3. Redeploy.

Until that env var is set, `bpa-backend`'s `getKeycloakClientScopeAttributes` short-circuits (Java `@Value("${keycloak.client_scope_id:null}")` → empty string → early return at `AuthServiceClient.java:420`), so the service keeps serving traffic. The publish flow that consumes the protocol-mapper output stays disabled but doesn't crash.

## Operator workflow after the upgrade PR merges

```bash
cd Conf-<UPPER_ENV>/compose/<country>/keycloak-patch
export KC_URL=https://login.<domain>
export KC_REALM=<realm>
export KC_ADMIN_USER=<master-admin>
export KC_ADMIN_PASS=<master-admin-pass>
./apply.sh
```

The script prints freshly-minted client-secret UUIDs (one per confidential client: bpa-backend, camunda, ds-client, gdb, statistics-backend). Mirror those into the operator's `.env` so `init-swarm.sh` seeds matching Docker secrets. If the realm already has secrets for those clients (instance was previously running), the `client-scope.json` POST will be a no-op for the client side (we only POST the scope, not the clients beyond display-system-frontend), so existing secrets stay intact.

After `apply.sh` succeeds, follow the `KEYCLOAK_CLIENT_SCOPE_ID` step above, redeploy, and verify bpa-backend can publish without 403.

## Why the patch directory is not committed

Each run generates fresh client-secret UUIDs. Committing them would publish credentials into the eregistrations-v4 git history (which is widely shared across deployments). The skill emits the artifacts under `Conf-<UPPER_ENV>/compose/<country>/keycloak-patch/` but the operator runs `apply.sh` locally and discards the directory afterwards. Adding a `.gitignore` entry for `**/keycloak-patch/` belongs in the eregistrations-v4 repo, not in this skill's output.

## Related drift on the docker-stack.yml side (not handled by this skill)

While preparing prelive.benin we also surfaced gaps that aren't strictly the 2.13→2.14 transition but get exposed during the upgrade chain. The orchestrator's post-handoff checklist (`upgrade-eregistrations-instance` STEP 6) should cover these:

- **`ds-frontend` service missing** from 2.13-era docker-stack.yml. Burundi LIVE never had a `ds-frontend:` block. The 2.16→2.17 skill is the right place to add it (when the new DS frontend becomes canonical), not 2.13→2.14.
- **HAProxy `chrome-url-to-pdf` route missing** vs the canonical Kenya LIVE config. The chain doesn't touch haproxy.cfg; the orchestrator should diff against a reference instance and prompt.
- **OPENSEARCH_ADMIN_PASSWORD via env-var interpolation** in the canonical 2.13→2.14 STEP 3.6 template. Production instances (mali, etc.) use the entrypoint-override pattern: `command: [ '/bin/sh', '-c', 'export OPENSEARCH_INITIAL_ADMIN_PASSWORD=$$(cat /var/run/secrets/OPENSEARCH_ADMIN_PASSWORD); ./opensearch-docker-entrypoint.sh opensearch' ]` plus `secrets: - OPENSEARCH_ADMIN_PASSWORD`. The skill currently emits the env-var form; consider following up to switch to the secrets pattern.
- **`restheart` missing `extra_hosts: mongodb_host:<IP>`** — `RESTHEART_MONGO_URI` baked by `init-swarm.sh` references `@mongodb_host` but the restheart service block has no `extra_hosts` entry to resolve it. The `cas-to-keycloak-migrate-apps` skill calls this out as a latent bug in mali / mali-amm references; the upgrade chain inherits it. Operators should add the `extra_hosts` entry alongside the migration.
- **Docker bridge gateway IP** (`172.17.0.1` vs `172.18.0.1`) varies between hosts. The skill leaves the literal in place — operators on a host with a different default bridge need a one-liner search-replace before deploy.

## CAS-era images (`casbackend`, `casfrontend`, `partcbackend`, `eregpartc`, `myaccount`) don't have platform-channel tags

Rule 2 bumps `unctad/<service>:<pinned-semver>` to `:RC` for everything outside the `mule3-/mule4-/cashier-` deny-list. On elsalvador LIVE 2.13 this swept up `casbackend:1.28.0`, `casfrontend:1.7.1`, `partcbackend:1.20.0`, `eregpartc:1.5.1`, `myaccount:0.2.103`. None of these have `:RC` in the registry — CAS / PARTC were retired before 2.14's RC channel started, and myaccount is country-specific (only elsalvador deploys it) and never joined the platform channels. `docker stack deploy` failed on `pull access denied` until a follow-up commit hand-reverted these 5 lines.

Subsequent steps in the chain re-bump them (`:RC` → `:BETA` → `:2.17` → `:2.18`) so the failure surfaces 4 times unless the operator unwinds each step. The pattern is invisible to the bumper because these services look exactly like normal platform images.

**Patch options:**
1. **Static deny-list extension:** add `casbackend`, `casfrontend`, `partcbackend`, `eregpartc`, `myaccount` to the country-image skip list (and the corresponding rules in 2.15→2.16, 2.16→2.17, 2.17→2.18). Conservative — if these images later magically get :RC tags the skip is still safe.
2. **Dynamic registry check:** query the docker registry for the target tag before bumping; skip if 404. More robust, adds network dependency.
3. **Anomaly fallback:** raise as STEP 2 anomaly 1 ("image has no :RC tag in registry") with default-skip. Cheapest to ship.

Option 1 is the most pragmatic. Option 2 is right long-term because the same trap will fire for any future "soon-to-be-removed" service.

## `unctad/formio:2.0.0-rc.122-6` bypasses Rule 2's pinned-semver regex

Rule 2's regex requires `[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?`. elsalvador 2.13's `unctad/formio:2.0.0-rc.122-6` includes `rc.122` (alpha component) that doesn't fit. Rule 2 silently skips formio; subsequent steps (2.16→2.17 `:BETA` → `:2.17`) also miss it because their regex matches require the source tag to be `:BETA`, which formio isn't. By the end of the chain formio is still pinned at `2.0.0-rc.122-6` while every other unctad image is on `:2.18`.

On elsalvador LIVE the operator caught this in diff review and bumped manually. The skill should at least warn.

**Patch:** loosen the pinned-semver regex to also match alpha-suffixed tags: `[0-9]+\.[0-9]+(\.[0-9]+)?(-[a-z]+\.[0-9]+)?(-[0-9]+)?` — captures `2.0.0-rc.122-6`. Or add anomaly 6 ("tag doesn't match either deny-list or platform-semver — manual review needed") with default-skip. The regex loosening is cleaner if formio is the only weird tag in practice.

## Quick reference — where this run's lessons landed

| # | Lesson | Patch landing site |
|---|---|---|
| 1 | CAS-era images lack platform tags; Rule 2 over-bumps them | extend deny-list to include `casbackend`, `casfrontend`, `partcbackend`, `eregpartc`, `myaccount`; OR add registry-check anomaly |
| 2 | `unctad/formio` alpha-tag breaks Rule 2's regex | loosen regex OR add anomaly 6 |

(The "Hibernate ddl-auto=update masks pre-existing migration gaps" lesson, initially drafted here, moved to `upgrade-eregistrations-instance/LESSONS.md` — it's BPA-backend Java behaviour that surfaces post-handoff during any upgrade, not specific to 2.13→2.14.)
