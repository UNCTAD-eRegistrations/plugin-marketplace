# eRegulations HTTP API surfaces, by version line

> **This file is a reference, not a source of truth.** Like `versions.md`, nothing
> enforces it: it was read from the source code of every eRegulations repository
> on 2026-09-04 and re-read against the `main` tips of 2026-09-11 (§11); it
> will drift as branches move. When it
> conflicts with a repository's own `README.md` or `CLAUDE.md`, this file is the
> more likely to be right — the API repo's `CLAUDE.md` in particular documents
> routes and settings that do not exist. When it conflicts with the code at the
> branch tip you are on, **the code wins**; re-read the controller before asserting
> a route. The router's gates (`gates.md`) still decide what may be changed.

Read this when a request is about calling, debugging, extending or migrating an
eRegulations / TradePortal HTTP API. Start at §1 to identify which surface and
version you are facing; §2–§4 hold the per-version contracts and endpoint
indexes; §7 covers moving between versions; §8 lists defects already known so
they are neither rediscovered nor silently patched.

---

## 0. Ground rules

1. **There are three unrelated API surfaces.** Never assume a route from one exists on another.
   - **A — ERegWebApi**: standalone read-only API for external systems. Repo `eRegulations-4.0-API`, project `ERegWebApi`. Routes have **no `api/` prefix** (`/Procedures/12`).
   - **B — Public embedded API**: `/api/*` inside the citizen-facing web app. Repo `eRegulations-4.0-Public`. Same-origin only, cookie auth, consumed by the site's own JS/Angular.
   - **C — Admin API**: `/api/*` in `eRegulations-4.0-Admin/Project/WebAppCore`, image `unctad/eregulations-admin-api`, consumed by the Angular 19 SPA (`eRegulations-5.0-Admin-SPA`). JWT bearer.
2. **Version lines**: 4.x (original, .NET Framework, IIS) · 5.x (TradePortal, .NET Framework, IIS) · 6.x (.NET 8 port, transitional, officially dropped) · **7.x (the only supported line; .NET 8; Docker/Coolify on Ubuntu)**. Since 2026-09-07 the 7.x line is branch `main` in Public, Admin, SPA and Statistics (renamed from `feature/implement-advanced-user-rights`, and from `database-layer-update-NET8` for Statistics); `master` in the same repositories is still 4.x. New code goes to 7.x only. Changes to 4.x/5.x/6.x are allowed only as part of an upgrade to 7.x.
3. **Do not infer the version from a directory or repo name.** `eRegulations-4.0-Admin` carries 7.x on `main` and 4.x on `master`. Identify by probing (§1) or by branch/file shape (§1.2). Use this skill's scripts: `scripts/fleet_resolve.py <slug>` says which line an instance runs; `scripts/branch_pair.py <public-csproj> <admin-root>` says whether the Public and Admin checkouts pair (SKILL.md Steps 2 and 4a).
4. **Surface A does not exist on 7.x.** It is not built, not in `eRegulations-deploy`, not in any 7.x release (7.4.2 at the time of writing). If asked to add something to "the public API" on 7.x, clarify whether they mean Surface B (public site) or Surface C (admin-api).
5. **Pairing constraint**: Public and ERegWebApi reference Admin's `Unctad.eRegulations.Library` as a project reference. Checkouts must pair or nothing compiles. The 7.x pair is Public `main` + Admin `main` + Statistics `main`: `channel/stable`'s `release.yml` pins all three build inputs (plus the SPA) by SHA per release, and Public's `release-pins.yml` pins its siblings to `main`. The former Public branch `dot-net8-roxana-user-rights` is retired (§3.6): 34 commits that never reached `main`, and everything on it that mattered was re-done on `main`.
6. **Admin 7.x crashes at startup if `/app/media` is not mounted** (`PhysicalFileProvider` on a missing directory). Any compose you write for admin-api must bind-mount it.
7. Nothing here was verified at runtime. Facts that depend on the compiled `Unctad.eRegulations.Library` are marked *[unverified]*.

---

## 1. Identify what you are facing

### 1.1 Probing a live host

Run these in order; stop at the first decisive answer.

| Probe | Result → conclusion |
|---|---|
| `GET /release.json` | `200 {track:"admin-api-core",version,…,release}` → **C 7.x**. `200 {…}` on a public site host → **B 7.x** (`main` build; the route is exempt from the Basic-auth gate, as is `/version.json`). `{"release":"…"}` only → admin-web nginx (the SPA container, not an API). 404 → 6.x, or a Public image built before 2026-09 from the retired roxana branch. |
| `GET /health` | `{"status":"ok"}` → **C 7.x**. `ok` (text) or `{"status":"up","version":…}` → admin-web nginx. 404 on an `/api`-serving host → C 6.x or B. |
| `GET /swagger/v1/swagger.json` | JSON with `api/permission` paths → C 7.x; with `api/user` but no `api/permission` → **C 6.x**. `GET /swagger/v1.1/swagger.json` with `/Procedures/{id}` paths → **A 6.x**. `GET /swagger/docs/v1` with `/Procedures/{id}` → **A 4.x**. |
| `GET /Country` | `{id:1,name,links[]}` → **A** (4.x or 6.x). Then `GET /Country/Details?lang=xx` in a non-default language: translated → 4.x; untranslated → 6.x (`?lang=` broken). |
| `GET /api/isauthenticated` | 401/`{Username…}` → **B**. Check casing of any `/api/procedure/{id}` response: `{"Id":…,"Name":…}` PascalCase → B 7.x/6.x (.NET 8); PascalCase too on 5.x (Web API 1) — distinguish by `/api/procedure/{id}/requirements` (7.x spelling) vs `/requeriments` (5.x spelling). |
| `401` + `WWW-Authenticate: Basic realm="eRegulations"` on `/` | **B 7.x** behind the pre-launch Basic-auth gate (`BASIC_AUTH_ENABLED=true`; on `main` since 2026-09-04 (#42), shipped from release 7.3.2; before that only on the retired roxana branch). |
| `GET /api/tariffs/search?query=` | 200 → B 7.x `main` with `TariffsApi*` configured. **404 is inconclusive**: 5.x, 6.x, the retired roxana branch and an unconfigured 7.x all answer 404 here. Use `/release.json` and the `/requirements` spelling instead. |

### 1.2 Identifying a checkout

| Evidence | Surface / version |
|---|---|
| `ERegWebApi/Startup.cs` + `Web.config` + `Authorization/ERegCASJwtAuthorizeAttribute.cs` | A 4.x (`master`) or the EF6 `database-layer-update` branch |
| `ERegWebApi/Program.cs` + `appsettings.json`, no `Authorization/` folder | A 6.x (`database-layer-update-NET8`) |
| `Project/WebApp/Global.asax.cs` with `MapHttpRoute` calls; `Api/Controllers/*.cs` (11 files) | B 4.x (`master`) |
| `Project/WebApp/Api/{Presentation,UseCases,Data,Infrastructure}` + `AppCode/TariffsFeature.cs` | B 5.x (`tradeportal`) |
| `Project/WebAppCore/Program.cs`; `Api/Presentation/Controllers/UserApiController.cs` **and** `Api/Presentation/Controllers/TariffsController.cs` (not the MVC `Controllers/TariffsController.cs`, which 6.x and roxana also have); `Middleware/BasicAuthMiddleware.cs`; `ReleaseEndpoint.cs` at the `WebAppCore` root; `Dockerfile` at the repository root | B 7.x (`main`) |
| `Project/WebAppCore` with `UserApiController.cs` + `Middleware/BasicAuthMiddleware.cs` but **no** `Api/Presentation/Controllers/TariffsController.cs` and no `ReleaseEndpoint.cs` | B 7.x retired `dot-net8-roxana-user-rights` checkout — rebase onto `main`, do not build on it (§3.6) |
| `Project/WebAppCore` with `Api/Presentation/Controllers/TariffsController.cs` + `ReleaseEndpoint.cs` but the API user controller still `UserController.cs` (and, before 2026-09-04, no `Middleware/BasicAuthMiddleware.cs`) | B 7.x `main` before 2026-09-08 (releases ≤ 7.3.3) — behind; pull |
| `Project/WebAppCore` without any of the above, `UserController.cs` under `Api/Presentation/Controllers` | B 6.x |
| `Project/Website/**/*.aspx`, `eRegulationsVer3.0.sln`, no `WebAppCore` | Admin 4.x/5.x — **no HTTP API** |
| `Project/WebAppCore/Controllers/` with `PermissionController.cs`, `AuditController.cs`, `HealthController.cs`, `Authorization/RequirePermissionAttribute.cs` | C 7.x |
| `Project/WebAppCore/Controllers/` with 23 controllers, no `PermissionController.cs` | C 6.x |
| SPA: `src/app/features/users/services/permissions.service.ts` exists | SPA 7.x (`main`); absent → the pre-May-2026 SPA (`archive/main-2026-05`), which targets C 6.x |

### 1.3 Common asks: which surface can answer them

Verified in code on every branch in §11 and live on a 5.x Public site on 2026-09-07. "none" means the route does not exist on that surface/version, not that it is empty.

| Need | A. ERegWebApi 4.x / 6.x | B. Public site 4.x | B. Public site 5.x / 7.x | C. Admin 6.x / 7.x |
|---|---|---|---|---|
| **Filter catalog** (filter names + their options) | `GET /Filters` (names, `order`, `label`, `isInclusive`), `GET /Filters/{id}` (with `options[]`), `GET /Filters/{id}/Options` — anonymous even when CAS is on | none | **none.** `/api/filter` and `/api/filters` are 404. Only `GET /api/filter/search?filterId=N` (options of one *known* filter id, no filter name), `/api/filter/product`, and `/api/filter/combinations` / `/api/filterobjective` (bare `{Key:filterId,Value:optionId}` pairs) | `GET /api/filter` → `FilterModel[]` with options — JWT + `filters.read\|procedures.read` on 7.x (plain `[Authorize]` on 6.x) |
| Filter/option combinations actually used by procedures | `GET /Objectives/Filters` | none | `GET /api/filter/combinations`, `GET /api/filterobjective` | — |
| **Results of a procedure** | per step: `results[]` inside `GET /Procedures/{id}` and `GET /Procedures/{pid}/Steps/{sid}`; procedure level: `GET /Procedures/{id}/ResumeDetail.results` (4.x `master` and 6.x; **not** on the 2018 `master-diverged` snapshot) | **none** (no procedure read model at all) | `GET /api/procedure/{id}/results`, `GET /api/procedure/{p}/step/{s}/results` | `GET /api/step/{id}/results` — `steps.read` |
| **Laws of a procedure** | per step: `laws[]` in the same routes; procedure level: `/ResumeDetail.laws`; catalog: `GET /Laws`, `/Laws/{id}` | **none** | `GET /api/procedure/{id}/laws`, `…/step/{s}/laws` | `GET /api/step/{id}/laws`; catalog `GET /api/law/search`, `/api/law/{id}/{showDependencies}` — `laws.read` |
| Requirements of a procedure | per step `requirements[]`; `/ResumeDetail.requirements` (only `+`-aggregated, non-`info`/`other`); catalog `GET /Forms` | none | 5.x `GET /api/procedure/{id}/requeriments` (sic), 7.x `/requirements`; per step likewise | `GET /api/step/{id}/documents` |
| Institutions / units / people | `GET /Contacts`, `/Units`, `/People` (+ `/{id}`) | none | `GET /api/procedure/{id}/institutions`, `…/step/{s}/contact` | `GET /api/{entityincharge\|unitincharge\|personincharge}/search` |

Read the table as: **the Public site API never exposes a filter catalog on any version, and on 4.x it exposes no procedure content at all**; ERegWebApi exposes all of it on every version; the Admin API exposes all of it behind a token. Three caveats that can look like "missing data":

- On ERegWebApi every step section is blanked by the step's `StepSectionVisibility` flags: a step whose "Legal justification" or "Expected results" section is hidden in Admin comes back with an empty `laws[]` / `results[]`, not an error. `recourses[]` is never populated on Surface A, on either version (the property is assigned nowhere).
- On Public 7.x an object hidden from guests raises `ObjectNotVisibleException` → 400 for anonymous callers; hidden and ABC data are loaded only when the caller is authenticated.
- `ResumeDetail.requirements` on ERegWebApi deliberately drops `or`-aggregated, `info` and `other` requirements and anything under a global-filter separator, and `ResumeDetail.results` / `Resume.results` keep only results flagged final (`ProcedureService.GenerateResumeResults`); use the per-step `requirements[]` / `results[]` for the full lists.

---

## 2. Surface A — ERegWebApi

### 2.1 Common to both versions

- Routing: attribute routes, case-insensitive, **no prefix**. 14 controllers: `Categories, Contacts, Country, CountryParameters, DocumentCosts, Filters, Forms, Laws, Layouts, Menus, Objectives, People, Procedures, Units`.
- One deployment = one country instance (`SystemInstanceID` + one country DB). No tenant header.
- Envelope on most list/detail routes: `{ "links": [{href,rel}…], "data": … }`. Bare (no envelope): `/Categories`, `/Country/Details|About|Contact|Data|Progress`, `/CountryParameters`, `/DocumentCosts/{id}`, `/Filters/Tabs`, `/Filters/{id}/Tabs`, `/Layouts*`, `/Objectives/Filters`, `POST /Objectives/SearchByFilters`, `/Procedures/{id}/Totals`, all `/ABC*` routes.
- `links[].href` base = `ApiServerUrl` setting. Media URLs = `PublicSiteURL/media/<file>` (or `CdnDistributionUrl`).
- No pagination, no filtering parameters, no HTTP cache headers. Lists are whole.
- Error convention: business failure → `400` (lists) / `404` (single), empty body. Exceptions → 500.
- Known dangling links: `steps[].links` on Contacts/Units/People/Forms point to `/Steps/{id}`, and Laws to `/Laws/{lawId}/Steps/{stepId}` — **these routes do not exist**. Steps are only under `/Procedures/{pid}/Steps/{sid}`.
- Route quirks: `{menuId}` in `/Procedures/{pid}/{menuId}[/Resume|/Steps/{sid}]` is ignored; `/Procedures/{pid}/{menuId}/Resume` returns the **ResumeDetail** shape; `/Procedures/{id}/ABC/Full.adminBurdenTable` is `null` when every step is online; `/Procedures/{pid}/Steps/{sid}` returns **500** (not 404) if the step is in no block; step ABC `Zone`/`Requirements` return **401 to mean "section hidden"**, not "unauthenticated".

### 2.2 Endpoint index (both versions unless marked)

```
GET  /Categories                                   -> CategoryModel[]            homepage bottom menus
GET  /Contacts                                     -> {links,data:ContactBaseModel[]}
GET  /Contacts/{id}                                -> {links,data:DetailedContactModel}   units[], steps[]
GET  /Country                                      -> {id:1,name,links[]}        anonymous on both
GET  /Country/Details                              -> CountryModel {id=SystemInstanceID,name,currency,availableLangs[],thirdPartyList[]}
GET  /Country/About                                -> TeamModel
GET  /Country/Contact                              -> SiteContactInformation (Library type)
GET  /Country/Data                                 -> {procedures,publishedProcedures,certifiedProcedures,steps,documents,people,laws}  slow
GET  /Country/Progress/{id}                        -> {steps,certifiedSteps,statusA..D,openedTickets,archivedTickets}
GET  /CountryParameters                            -> {staffLevelList[],zoneList[],priceOfPrinting,priceOfUsingComputer}  cached
GET  /DocumentCosts/{id}                           -> {id,numberOfPages,totalCost,documentCost,printCost}   documentCost: 4.x [{key,value}] / 6.x object
GET  /Filters                                      -> {links,data:FilterModel[]}
GET  /Filters/{id}                                 -> {links,data:DetailedFilterModel{options[]}}
GET  /Filters/{id}/Options                         -> {links,data:{id,name}[]}
GET  /Filters/Tabs                                 -> FilterSetModel[]
GET  /Filters/{id}/Tabs                            -> FilterSetModel             id = tab id; 500 if ids not 1..N
GET  /Forms                                        -> {links,data:RequirementBaseModel[]}
GET  /Forms/{id}                                   -> {links,data:RequirementModel}
GET  /Laws                                         -> {links,data:GenericDocumentBaseModel[]}
GET  /Laws/{id}                                    -> {links,data:GenericDocumentModel}
GET  /Layouts                                      -> {headerLogos[],footerLogos[]}
GET  /Layouts/Homepage                             -> {backgroundImage,htmlContent}
GET  /Menus                                        -> {links,data:MenuBaseModel[]}   recursive subMenus
GET  /Menus/{id}                                   -> {links,data:MenuBaseModel}
GET  /Objectives                                   -> {links,data:ObjectiveBaseModel[]}   6.x adds description (null in tree)
GET  /Objectives/{id}                              -> {links,data:ObjectiveBaseModel}     6.x adds description
GET  /Objectives/Filters                           -> [[{key:filterId,value:optionId}]]  anonymous on both
POST /Objectives/SearchByFilters  body [{key,value}] -> FilterSearchResultModel[]   400 empty body, 404 no result
POST /Objectives/Search           body "keyword"     -> BaseLinkableModel[]        6.x NET8 ONLY; body is a JSON string
GET  /People, /People/{id}, /Units, /Units/{id}
GET  /Procedures/{id}                              -> {links,data:ProcedureModel{url,additionalInfo,blocks[].steps[]}}
GET  /Procedures/{id}/Totals                       -> ResumeTotalModel            500 if steps fail
GET  /Procedures/{id}/Resume                       -> {links,data:ResumeModel{steps,institutions,results,requirements,laws,costs[],timeframe}}
GET  /Procedures/{id}/ResumeDetail                 -> {links,data:ResumeDetailModel}
GET  /Procedures/{id}/ABC                          -> AdminBurdenInPersonModel | AdminBurdenOnlineModel
GET  /Procedures/{id}/ABC/Levels|Zones|Requirements|Full
GET  /Procedures/{pid}/{menuId}                    (= /Procedures/{pid})
GET  /Procedures/{pid}/{menuId}/Resume             (= ResumeDetail shape)
GET  /Procedures/{pid}/Steps/{sid}                 -> {links,data:StepModel}
GET  /Procedures/{pid}/{menuId}/Steps/{sid}        (= above)
GET  /Procedures/{pid}/Steps/{sid}/ABC             400 if step internal
GET  /Procedures/{pid}/Steps/{sid}/ABC/Zone        401 if contact section hidden
GET  /Procedures/{pid}/Steps/{sid}/ABC/Requirements 401 if requirements hidden/empty
GET  /Procedures/{pid}/Steps/{sid}/ABC/Full
GET  /swagger  (UI)   4.x spec: /swagger/docs/v1   6.x spec: /swagger/v1.1/swagger.json
```

`StepModel` (both): `id,name,order,isOnline,isOptional,isCertified,links[], online{url,type}, results[], contact{entityInCharge,unitInCharge,personInCharge}, requirements[], laws[], recourses[] (never populated, either version), certification{entityInCharge,date,attachments}, timeframe{timeSpentAtTheCounter{hours{min,max},minutes{min,max}},waitingTimeInLine{…},waitingTimeUntilNextStep{days{min,max}},comments,attachments}, costs, additionalInfo{text,attachments}`. `costs` is `{cost,unit,individualCosts[]}` on 4.x and `CostModel[]` on 6.x.

### 2.3 Version 4.x (`master`, net48, OWIN Web API 2, IIS)

| Aspect | Contract |
|---|---|
| Auth | `[ERegCASJwtAuthorize]` on all controllers except `Country`, `Filters`, and `GET /Objectives/Filters`. Active **only if appSetting `CasActivated=true`**; otherwise every route is anonymous. When active: `Authorization: Bearer <RS256 JWT>`; issuer must equal `ERegCASTokenAuthority`; audience not checked; public key fetched once from `ERegCASServerURL + ERegCASPublicKeyPath` (rotation needs an app-pool recycle). 401 bodies: empty, `"Invalid Token"`, or `"JWT is rejected: …"`. |
| Language | `?lang=xx` (also `lang` cookie). Default: Library `DefaultLang`. Propagates into `links[].href`. |
| JSON | camelCase; **every dictionary serialized as `[{key,value}]`**; `Accept: text/html` gets indented JSON. |
| CORS | **None**, and `OPTIONS` is unhandled → browsers cannot call cross-origin. |
| Config | External gitignored files next to `Web.config`: `appSettings.config` (`CasActivated, ERegCASServerURL, ERegCASPublicKeyPath, ERegCASTokenAuthority, ApiServerUrl, CdnDistributionUrl, AbcActivated, LoadingStepStatus, IsNationalSystem, CurrencyRefreshTime`), `applicationSettings.config` (Library: `DefaultLang, CountryName, Currency, SystemInstanceID, publicSiteURL`), `connectionStrings.config`. |
| Caching | `/CountryParameters` 5 min in `MemoryCache`; nothing else. |
| Build | Requires sibling checkout `..\..\eregulations-4.0-admin\Project\Unctad.eRegulations.Library` on a compatible (legacy) branch. |
| Tests | `ERegWebApi.Tests` (MSTest+Moq) — use as usage examples. |
| Concurrency bugs | DI "scoped" = process-wide; app context built from the **first** request. Do not add per-request state to services. |

`master-diverged` is an ancestor snapshot from 2018, not a live line. Ignore it unless asked about history.

### 2.4 Version 6.x (`database-layer-update-NET8`, net8.0, EF Core)

| Aspect | Contract |
|---|---|
| Auth | **None.** All 50 routed actions anonymous. No bearer scheme registered. |
| Language | Read from `Session[LANGUAGE_KEY]`; **nothing in the repo sets it** → always `ApplicationSettings:DefaultLang` *[unverified whether the Library sets it]*. `?lang=` is ignored (but still echoed into links). |
| JSON | camelCase (framework default); dictionaries are objects. |
| CORS | Hard-coded two-origin policy in `Program.cs` (a localhost dev origin and one external partner origin). Change `Program.cs` to add origins; nothing is configurable. |
| Config (`appsettings.json`) | `ConnectionStrings:{DefaultConnection,GlobalConnection,ConsistencyConnection}` — all three **required** at boot. `ApplicationSettings:{SystemInstanceID (string?, Convert.ToInt32 → 0 when absent), DefaultLang, CountryName, Currency, PublicSiteURL, ApiServerUrl, PublicConfigFolder, CentralRepositoryPath, CdnDistributionUrl, CurrencyRefreshTime, IsLoadingStepStatus, IsNationalSystem}`. `IsAbcActivated` and `CacheSlidingTime` are dead. `ApiServerUrl` has **no fallback**: unset → links like `/Contacts/1`. Shipped file has developer-machine values. |
| Errors | `UseDeveloperExceptionPage()` is on in Production → 500s return HTML stack traces. |
| Caching | `CountryParameters` and cost-parameter catalog cached **forever**; restart after editing staff levels/zones/cost variables. |
| Build | Project reference `..\..\eregulations-4.0-admin-api\Project\Unctad.eRegulations.Library` (note the `-api` suffix — a different sibling folder name than 4.x). The `Dockerfile` copies only the repo root, so `dotnet restore` fails unless the build context is the parent directory. |
| Tests | Project exists but is empty. |
| Diverged sibling | `database-layer-update` (net48 + EF6, still has CAS auth and `?lang=`): its `POST /Objectives/Search` takes `{"keyword":"…","onlyProcedures":true}` and returns `description`; NET8 takes a bare JSON string and returns no description. |

### 2.5 Recipes

```bash
# 4.x, CAS off / 6.x
curl -s "$A/Country/Details?lang=fr"
curl -s "$A/Procedures/123"
curl -s "$A/Procedures/123/Steps/456"
curl -s -X POST "$A/Objectives/SearchByFilters" -H 'Content-Type: application/json' -d '[{"key":3,"value":17}]'
# 4.x, CAS on
curl -s "$A/Procedures/123" -H "Authorization: Bearer $CAS_JWT"
# 6.x only
curl -s -X POST "$A/Objectives/Search" -H 'Content-Type: application/json' -d '"import licence"'
```

### 2.6 Modifying Surface A

- Do it only as part of an upgrade to 7.x, or with an explicit, recorded `unsupported_version` override (`scripts/audit.py`).
- 4.x: controllers in `ERegWebApi/Controllers/*.cs` with `[RoutePrefix]`+`[Route]`; DI registrations in `Startup.ConfigureServices` (`DI/ServiceProviderExtensions.cs` registers only the controllers; `DI/DefaultDependencyResolver.cs` bridges the container to Web API); JSON settings and Swagger in `Startup.cs`; config via `Helpers/Impl/ConfigHelper.cs`.
- 6.x: `Program.cs` holds DI, CORS, Swagger, static `/media`; controllers `[Route("Xxx")]`+`[HttpGet("…")]`; settings class `Infrastructure/ApplicationSettings.cs`; language/context `Infrastructure/WebApplicationContext.cs`. Business classes `Business/Impl/*Data.cs`, mappers `Services/Impl/*Service.cs`, models `Models/*.cs`. There is no `[ApiController]`; add it if you want ProblemDetails/400 auto-validation.
- Keep `[ProducesResponseType]` honest — several are currently wrong (`/Layouts`, `/Procedures/{id}/ABC/Zones|Levels`, `/{pid}/{menuId}/Resume`, `SearchByFilters`).

---

## 3. Surface B — Public site embedded API

### 3.1 Common to all versions

- Same-origin, browser-facing. Consumers: the site's jQuery/Backbone scripts and, from 5.x, the Angular 9 sub-app under `angular/` (built into `assets/js/angular`, mounted only on the procedure summary page `Views/Summary/Index.cshtml`).
- Auth = the site's own cookie login (`.Auth`) + a roles cookie; `[Authorize]` means "any logged-in user". Consistency-review tickets/comments, ABC editing, visibility toggles and step status are behind it. Optional CAS/OAuth2 SSO on 5.x/7.x (`ERegCAS*` / `Cas:*`).
- Language: `?l=xx` (constant `WebAppGlobals.REQUEST_LANG`). Not `lang`.
- Embedding = the same HTML pages with `?embed=true` (`Objective/Index|Search`, `Menu/Index`, `Summary/Index|StepDetail`, `Procedure/Index|Details`, `Tariffs/Index`, `EmbedSearch`). There is no JSON widget endpoint.
- Public ↔ Admin share the databases and content folders; the only HTTP hop is the SSO handoff (§5).
- `BaseController` actions are reachable on every MVC controller path: `/{Any}/GetAuthorized?logged=`, `/{Any}/ToggleConsistency`, `/{Any}/ToggleAdminBurden` (5.x+), `/{Any}/Logout` (clears the consistency cookie only).

### 3.2 Version 4.x (`master`, .NET Framework 4.0, Web API 1, routes in `Global.asax.cs`)

```
GET    /api/ticket/{pageId}/{menuId}/{objectiveId}/{stepId}           anon   -> TicketDTO[]
GET    /api/ticket/{pageId}/{section}/{menuId}/{objectiveId}/{stepId} anon   -> TicketDTO[] | null
PUT    /api/ticket   body TicketDTO (Id required)                     cookie -> TicketDTO
POST   /api/ticket   body TicketDTO                                   cookie -> TicketDTO
POST   /api/comment  body {TicketId,Comment,IsTicketFinished:0|1}     cookie -> CommentDTO
DELETE /api/comment/{id}                                              cookie    author only
POST   /api/{document|entityincharge|personincharge|unitincharge|law}/{id}/SetPublicVisibility  cookie  body {IsVisible} -> "ok"
GET/POST/PUT/DELETE /api/{same five}[/{id}]                           anon      VS scaffold stubs ("value1","value2")
GET    /api/login?username=&pwd=                                      anon   -> {Username,FullName} + persistent cookie
GET    /api/logout, /api/isauthenticated                              anon
GET    /Consistency/LoadMore?text=&status=&page=&procedureId=         cookie -> ReviewSearchItemDTO[]
GET    /SystemDashboard/CompareSystemIndicators|CompareStatusIndicators?currentDate=dd.MM.yyyy&previousDate=  anon
```
`pageId` = `ReviewPageNameType` (homepage=1, menu=2, stepsummary=3, step=4, objective=5). `TicketStatus`: Opened=1, Pending=5, Finished=8, Archived=-1, Deleted=-99. `DateCreated` format `dd/MM/yyyy hh:mm:ss tt`. `Web.config` is gitignored; appSettings read: `Authorization.Cookie.Name`, `Authorization.Cookie.Timeout` (**required, throws if absent**), `FeedbackUrl`, `IsCustomFeedbackUrl`, `GoogleAnalyticsAcc`, `GoogleTranslateContent`, `IsNationalSystem`, `LocalCurrency`, `Country`, `City`, `RequirementsFilterDefaultOption`, `CdnDistributionUrl`, `ConfigFolder`, `AdminSiteUrl`, `StatisticsMinDate`. Connection strings are Library `applicationSettings` names (`Unctad.eRegulations.Library.Properties.Settings.DBConnectionString|ConsistencyDBConnectionString|GlobalDBConnectionString`, `Unctad.eRegulationsStatistics.Library.Properties.Settings.StatisticsConnString`).

### 3.3 Version 5.x (`tradeportal`, .NET Framework 4.0, Web API 1, clean-architecture `Api/` layer)

Routing is explicit in `Global.asax.cs` (first match wins). Generic route `api/{controller}/{id}` defaults `action=DefaultAction`, so verb-named actions carry `[ActionName("DefaultAction")]`. Exception filter on the "clean" controllers: `KeyNotFoundException`→404, `ArgumentException`→400, else 500, body `"<ExceptionType>::<message>"`. Legacy controllers (Ticket, Comment, IsAuthenticated, FilterObjective, Feedback, Tariffs) have no filter → 500.

```
# procedure read model (anon)
GET /api/procedure/{id}                          -> {Id,Name}
GET /api/procedure/{id}/breadcrumb | /api/procedure/{menuId}/{id}/breadcrumb -> MenuPathDTO[]
GET /api/procedure/{menuId}/{id}/details         -> {Id,Name,AdditionalInfo,Breadcrumb[]}
GET /api/procedure/{id}/details                  -> {Id,Name}   (route quirk: hits Get, not Details)
GET /api/procedure/{id}/additionalinfo|contextinfo|institutions|blocksteps|results|laws|requeriments|costs|timeframe
GET /api/procedure/usecontactpage                -> {UseContactPage,ExternalContactPage}
# procedure ABC (cookie)
GET /api/procedure/{id}/calculate | /step/{stepId}/calculate | /abc | /institutionzones | /stepslevel | /requerimentscost
# step (anon unless marked)  base = /api/procedure/{procedureId}/step/{stepId}
GET  <base>                                       -> StepDTO
GET  <base>/contact|results|laws|requeriments|costs|timeframe|additionalinfo|recourse|certifier
GET  <base>/status                       cookie   -> ConsistencyStatusModel
POST <base>/setstatus  body StatusChangeModel  cookie -> true | 500
GET  <base>/abc|contactzone|requerimentscost   cookie
POST /api/step/{id}/savenumberofusers {NumberOfUsers}   cookie
POST /api/step/{id}/savelevel {LevelId}                 cookie
# tickets / comments: as 4.x, but 4-segment GET is cookie, 5-segment {section} GET is anon, menuId int?
# session
GET /api/isauthenticated, /api/logout      (GET /api/login is commented out → use POST /User/AjaxLogin)
# editing (cookie)
POST /api/{document|entityincharge|personincharge|unitincharge|law}/{id}/setpublicvisibility {IsVisible}
POST /api/document/{id}/toggleebiflag
POST /api/entityincharge/{id}/savezone {ZoneId}
GET/POST /api/countryparameters             CountryParametersDTO
GET/POST /api/documentcost/{id}             DocumentDTO ; POST /api/documentcost/calculatepreview -> DocumentDTO | 502
# filters (anon)
GET /api/filter/search/{query}?filterId=    -> {Query,Results:[{Id,Parent,Name,ProductCode}]}
GET /api/filter/search?filterId=            full option list (cap ProductSelectorMaxResults)
GET /api/filter/product?filterId=&filterOptionId=&productId=
GET /api/filter/combinations | /api/filterobjective   -> [[{Key,Value}]]
# currency (anon)
GET  /api/currency                          -> [{Code,Name}]
POST /api/currency/convert {From,To}        -> {From,To,Value}   (proxies an external currency-converter API; Value must be empty in request)
# translation (anon)
GET  /api/translation?l=xx                  -> {label:text}
POST /api/translation {Label,DefaultValue}  -> 201 string
# feedback (anon)
GET  /api/feedback/countries | /api/feedback/allprocedures?showObjectives=
POST /api/feedback/sendfeedback?showObjectives=   body FeedbackModel; header RequestVerificationToken: <cookieToken>:<formToken> (antiforgery)
POST /api/feedback/validaterecaptchatoken {Token} -> bool (Google siteverify, action must be "feedback")
# tariffs (anon; ALL 404 unless TariffsApiUrl+TariffsApiUserId+TariffsApiKey are set)
GET  /api/tariffs/search/{query} | ?query=   -> {Query,HsCodes[]}
GET  /api/tariffs/GetCommodityDetails/{code} -> {Code,Description,Unit1,Unit2,Unit3}
GET  /api/tariffs/getexchangerates | /api/tariffs/getcountrypreferences
POST /api/tariffs/estimate  body TariffsTaxEstimationData -> TariffsTax | 400 TariffsErrorList
# MVC JSON / flows
POST /objective/linear-search  form lang, filters{filterId:optionId} -> LinearObjectiveResult[]
POST /User/AjaxLogin  form UserName,Password[,returnUrl] -> {status:"ok"|"error",content}
GET  /User/GoToAdmin?returnUrl=  cookie  -> 302 to {AdminSiteUrl}/auth/sso?token=  (see §5)
GET  /User/CasLogin | /User/CasAccessToken?code=&state=   OAuth2 code flow (JWT signature NOT verified)
GET  /Home/DownloadFile?filePath=   anon, server-relative path
```
Config keys read on 5.x (appSettings, `Web.config` gitignored; `TariffsCacheTime` is a 7.x key that the 5.x `CLAUDE.md` mentions but no 5.x code reads): instance/urls `Country, CountryCode, City, LocalCurrency, AdminSiteUrl, AdminApiUrl, SsoSharedSecret, CdnDistributionUrl, ConfigFolder, StatisticsMinDate`; also read `GoogleTranslateContent, CrmPixelCode, FacebookPixelCode, IsUsingDifferentLogosInLeftDrawer, RightDrawerOpenByDefault, redcuba`, and `Authorization.Cookie.Name` / `Authorization.Cookie.Timeout` (throw if absent, as on 4.x); flags `AbcActivated, IsBookmarksObjectiveActivated, IsStepSummaryActivated, IsStrictProductCodes, UseContactPage, ExternalContactPage, ShowInvestorFieldsInFeedbackWindow, ShowOthersFieldInFeedbackWindow, WorkingOffline, IsNationalSystem, RequirementsFilterDefaultOption`; third-party `GoogleAnalyticsAcc, GoogleTagAccessCode, GoogleMapsApiKey, GoogleReCaptchaApiKey, GoogleReCaptchaSecretKey, HJID, CurrencyConverterAPIkey, CurrencyRefreshTime, HSCodeApi`; cache `CacheSlidingTime (30), ProductSelectorMaxResults`; CAS `ERegCASServerURL, ERegCASAuthorizationEndpoint, ERegCASTokenEndpoint, ERegCASInvalidateTokenEdpoint, ERegCASUserProfileURL, ERegCASClient, ERegCASClientSecret, ERegCASSessionCookie, CheckingCASTokenBlacklist, ERegCASTokenBlacklistEndpoint`; tariffs `TariffsApiUrl, TariffsApiUserId, TariffsApiKey, TariffsAdditionalVariableName (cylinderCapacity), TariffsAdditionalVariableHsPrefixes, TariffsAdditionalVariableMin/Max`.

Branches: `tradeportal-spa` = older snapshot of `tradeportal`, nothing extra. `tp-tariffs-calculation` = older state, no extra endpoints, lacks the tariffs 404 guard and `GoToAdmin`.

Angular 5.x consumer facts: base URL `location.origin`; ids from the router URL; language from `?l=`; auth/feature flags from DOM markers (`input.checkCR`, `input.checkAB`); about half the services re-append `window.location.search` to GETs (procedure, step, step-status, document, institution, country-parameters); the ticket and currency services do not; translations via `GET /api/translation?l=`; ticket GET hard-codes `menuId=0`.

### 3.4 Version 6.x (`database-layer-update-NET8`, .NET 8)

Same routed API controllers and routes as 7.x (§3.5) **except**: no `Api/Presentation/Controllers/TariffsController.cs` (the MVC `Controllers/TariffsController.cs` page exists), no `GET /release.json`, no `Middleware/BasicAuthMiddleware.cs`; API user controller is still `UserController` → MVC `POST /User/Logout` collides with `GET api/logout` → 405; no `UserId` claim (tickets stamped with the system id); `POST /api/currency/convert` returns 400 (not 502) on upstream failure and reads root key `CurrencyConverterAPIkey`; `GET /api/translation` returns the local dictionary only; no `GET /Home/CustomCss`.

### 3.5 Version 7.x — `main` (release 7.4.x)

One branch since 2026-09-07: `main`, renamed from `feature/implement-advanced-user-rights`.
Between 2026-09-04 and 2026-09-11 it absorbed what the retired `dot-net8-roxana-user-rights`
branch had over it — the Basic-auth gate (#42, shipped in 7.3.2), then the `UserApiController`
rename, `UserId` stamping, 502 currency semantics and `Home/CustomCss` (shipped from 7.4.0) —
plus the fixes listed in §8. Re-read at `5c0a8efdf`,
the Public SHA that release 7.4.2 pins.

| Aspect | Contract |
|---|---|
| Runtime | `net8.0`, one app: Razor MVC (conventional routes) + API (attribute routes `[Route("api/…")]` spelled per action; `BaseApiController` has no route prefix). `SuppressImplicitRequiredAttributeForNonNullableReferenceTypes=true`. |
| JSON | **PascalCase** (`DefaultContractResolver`, set in `AppCode/ApiJson.cs`), indented, `ReferenceLoopHandling.Ignore`. Anonymous-type members keep their declared case (`{error}`, `{status}`). |
| Errors | Global `ControllerExceptionFilterAttribute` (applies to MVC pages too): `ArgumentOutOfRangeException`→404, `ArgumentException`/`ObjectNotVisibleException`→400, `KeyNotFoundException`/`*NotFoundException`→404, else 500; body `{"error":"<message>"}`. |
| Pipeline | forwarded headers (`X-Forwarded-Proto`, so redirects and generated URLs say https behind the proxy) → **Basic-auth gate** → HTTPS redirect → licensed-assets gate → WebOptimizer → static files (`Cache-Control: public, max-age=3600` on `wwwroot`; `/PublicContent`, `/Content`, `/media` if dirs exist) → routing → rate limiter → CORS → authentication → authorization → session → role middleware → `GET /release.json` → controllers. |
| Basic-auth gate | Env `BASIC_AUTH_ENABLED=true` → every request incl. `/api/*` needs `Authorization: Basic` matching one pair of `BASIC_AUTH_USERS` (`u:p,u2:p2`). **No built-in credential**: enabled with an empty list it refuses everyone. Exempt: `/release.json` and `/version.json`, so the healthcheck still passes. Else 401 + `WWW-Authenticate: Basic realm="eRegulations"`. |
| Cookie auth | Scheme `Cookies`, cookie `.Auth` (`Authorization:Cookie:Name`), `SameSite=Lax`, timeout `Authorization:Cookie:Timeout` (300 min), claims `Name`, `UserId`, roles. Unauthenticated `[Authorize]` call → **302 to `/?ReturnUrl=`** unless `X-Requested-With: XMLHttpRequest` (then 401) *[framework default, inferred]*. Send that header from scripts/curl to get a 401. |
| Role middleware | Authenticated user with **zero roles → 302 `/User/Unauthorized` on every request, API included**. CAS session token expiry/blacklist checked per request. |
| CORS | `AllowAnyOrigin().AllowAnyMethod().WithHeaders("Content-Type")`, no credentials → anonymous routes callable cross-origin; cookie routes effectively same-origin; `RequestVerificationToken` header not allowed cross-origin. |
| Language | `?l=` → session → `LibrarySettings:DefaultLang`. |
| Antiforgery | Header `RequestVerificationToken`; validated by `POST /api/feedback/sendfeedback` (the only API action) and by the MVC `POST /Procedure/ChangeStatus`. |
| Health | `GET /release.json` = `/app/version.json` + `EREG_RELEASE` (mapped before `MapControllers`). The Dockerfile has no `HEALTHCHECK`; the compose healthcheck reads `/release.json` and accepts 200 or 404. |
| Caching | None on API. `ApiInMemoryCache` registered but unused. |
| Config | `appsettings.json` sections (env form `Section__Key`): `ConnectionStrings:{CountryDbContext,GlobalDbContext,ConsistencyDbContext,StatisticsDbContext}`; `Authorization:Cookie:{Name,Timeout}`; `AppSettings:{ConfigFolder,LocalCurrency,Country,CountryCode,City,AdminSiteUrl,StatisticsMinDate,WorkingOffline,ShowLocations,AbcActivated,FilterForProductsTab,ProductSelectorMaxResults,HJID}`; `Google:{AnalyticsAcc,TagAccessCode,MapsApiKey,TranslateContent}` (+ ad-hoc `ReCaptchaApiKey`,`ReCaptchaSecretKey`); `CurrencyConverter:ApiKey`; `LibrarySettings:{DefaultLang,PublicConfigFolder,CentralRepositoryPath,CountryName,CountryId,Currency,SystemInstanceID,PublicSiteURL,PublicSiteVersion,ErrorCodeItemDeleted,OwnershipStatusDefault,ProductsURL,ProductsWidgetURL}`; `Cas:*`; `Feedback:{SmtpServer,UseSmtpAuthentication,SmtpUserName,SmtpPassword,SmtpSSL,SmtpPort,SendFrom,SendToList[]}`; `Mail:*` (unbound). Read ad hoc, **absent from the file**: `AppSettings:AdminApiUrl`, `AppSettings:SsoSharedSecret`, `AppSettings:HSCodeApi`, `AppSettings:CrmPixelCode`, `FacebookPixelCode`, `IsNationalSystem`, `CacheSlidingTime`, `CdnDistributionUrl`, `RightDrawerOpenByDefault`, `ShowOthersFieldInFeedbackWindow`, `ShowInvestorFieldsInFeedbackWindow`, `UseContactPage`, `ExternalContactPage`, `IsUsingDifferentLogosInLeftDrawer`, `redcuba`, `IsStrictProductCodes`, `RequirementsFilterDefaultOption`. `appsettings.Development.json`/`appsettings.Docker.json` mentioned by README **do not exist**. |
| Docker | `Dockerfile` at the repository root, `EXPOSE 8080`, runs as `$APP_UID`; build context must be the parent dir holding `eregulations-4.0-public/`, `eregulations-4.0-Admin/`, `eregulations-statistics/` (case-sensitive; the casing changed on 2026-09-08 with the Qodana CI). Compose volumes: `/app/media`, `/app/Logs`, `/app/Multilang`, `/app/MultilangCentralRepository`, `/app/Config`, `/app/Content`, `/app/PublicContent`. |

Endpoint index (18 routed controllers plus `BaseApiController`; `anon`/`cookie`):

```
# ApiProcedureController
GET  /api/procedure/{id}                                  anon   -> {Id,Name}
GET  /api/procedure/{id}/breadcrumb | /api/procedure/{menuId}/{id}/breadcrumb   anon -> MenuPathDTO[]
GET  /api/procedure/{id}/details | /api/procedure/{menuId}/{id}/details        anon -> {Id,Name,AdditionalInfo,Breadcrumb[]}
GET  /api/procedure/{id}/additionalinfo|contextinfo|institutions|blocksteps|results|laws|requirements|costs|timeframe   anon
GET  /api/procedure/usecontactpage                        anon
GET  /api/procedure/{id}/calculate | /step/{stepId}/calculate | /abc | /institutionzones | /stepslevel | /requirementscost   cookie
# StepController  base=/api/procedure/{procedureId}/step/{stepId}
GET  <base> | <base>/contact|results|laws|requirements|costs|timeframe|additionalinfo|recourse|certifier   anon
GET  <base>/status                       cookie -> ConsistencyStatusModel{Status,Version,Cycle,LastModified,LastModifiedBy,NextOption,BackOption,StepId,MinRole,Content,AdminStepURL,CanModifyStatus}
POST <base>/setstatus  {StepId,StepVersion,Status,Version,Cycle,Lang,StatusComments,NextAction}  cookie -> 200 | 400 | 403 | 500
GET  <base>/abc|contactzone|requirementscost     cookie
POST /api/step/{id}/savenumberofusers {NumberOfUsers} ; POST /api/step/{id}/savelevel {LevelId}   cookie
# TicketController / CommentController
GET  /api/ticket/{pageId}/{menuId}/{objectiveId}/{stepId}             cookie -> TicketDTO[]   (menuId is required; send 0 for a menu-less page, #58)
GET  /api/ticket/{pageId}/{section}/{menuId}/{objectiveId}/{stepId}   cookie (anonymous bypass until #59, 2026-09-08) -> TicketDTO[] | null
PUT  /api/ticket ; POST /api/ticket   body TicketDTO                  cookie   creator/modifier = UserId claim
POST /api/comment ; DELETE /api/comment/{id}                          cookie   (non-author delete → 500)
# editing
GET/POST /api/countryparameters                                       cookie
GET/POST /api/documentcost/{id} ; POST /api/documentcost/{id}/calculatepreview   cookie
POST /api/{document|entityincharge|law|personincharge|unitincharge}/{id}/setpublicvisibility {IsVisible}   cookie  ([FromBody] JSON)
POST /api/document/{id}/toggleebiflag ; POST /api/entityincharge/{id}/savezone {ZoneId}   cookie
# read-only utilities (anon)
GET  /api/filter/search/{query}?filterId=   ⚠ binds query from ?query=, path segment ignored
GET  /api/filter/search?filterId= ; /api/filter/product?filterId=&filterOptionId=&productId= ; /api/filter/combinations ; /api/filterobjective
GET  /api/currency ; POST /api/currency/convert {From,To} -> {From,To,Value} | 400 | 502
GET  /api/translation?l= (local+central merged) ; POST /api/translation {Label,DefaultValue} -> 201
GET  /api/feedback/countries ; /api/feedback/allprocedures?showObjectives=
POST /api/feedback/sendfeedback (RequestVerificationToken header) ; POST /api/feedback/validaterecaptchatoken {Token}
GET  /api/login?username=&pwd= ; /api/logout ; /api/isauthenticated      (UserApiController)
# Api/Presentation/Controllers/TariffsController  [Route("api/tariffs")]  anon, [TariffsFeatureGate] -> 404 unless AppSettings:TariffsApiUserId|TariffsApiKey|TariffsApiUrl, [EnableRateLimiting]
GET  /api/tariffs/search?query= ; /api/tariffs/GetCommodityDetails/{code?} ; /api/tariffs/GetExchangeRates ; /api/tariffs/GetCountryPreferences
POST /api/tariffs/estimate   (256 KB body cap)
GET  /release.json   anon, exempt from the Basic-auth gate -> {track,version,revision,…,release}
# MVC JSON
GET  /Base/GetAuthorized?logged= | /Base/ToggleConsistency | /Base/ToggleAdminBurden | /Base/Logout   anon
GET  /Consistency/LoadMore?text=&status=&page=&procedureId=   cookie   page 20, cursor in session
POST /Objective/LinearSearch (= objective/linear-search) {Lang,Filters:{id:optionId}}   anon
POST /Procedure/ChangeStatus     cookie + RequestVerificationToken  (menuId, procedureId, stepVersion, stepId, status, versionT, cycle, statusComments, statusnextaction)
GET  /SystemDashboard/CompareSystemIndicators|CompareStatusIndicators?currentDate=&previousDate=   anon (Statistics DB)
POST /User/AjaxLogin form UserName,Password ; POST /User/Login ; GET /User/GoToAdmin?returnUrl= (cookie) ; /User/Cas*
GET  /Home/CustomCss  (text/css, max-age=300) ; GET /Home/DownloadFile?filePath=  (confined to the content root; anything else -> 404)
```

### 3.6 Retired 7.x branch — `dot-net8-roxana-user-rights`

Parallel branch (merge-base `69b857c1d`, 2026-06-15) that carried the Docker-working Public until September 2026. Not a target any more: 34 commits never reached `main`, and everything operationally relevant was re-done on `main` (§3.5). A Public image hand-built from it (no `channel/stable` release ever used the branch) differs from `main` in that it **lacks** `GET /release.json`, the API `Api/Presentation/Controllers/TariffsController.cs`, the rate limiter, the licensed-assets gate and the `DownloadFile` containment, its `POST /Procedure/ChangeStatus` is a no-op stub answering `{success:true}`, and its Basic-auth gate falls back to a hard-coded default user:password pair when `BASIC_AUTH_USERS` is empty (the value is in that branch's `Middleware/BasicAuthMiddleware.cs`; do not copy it anywhere). Identify such an image with the probes in §1.1 and redeploy from `channel/stable`; do not patch the branch.

### 3.7 Recipes (7.x)

```bash
B=https://<public-host>
curl -s "$B/api/procedure/123/details?l=fr"
curl -s "$B/api/procedure/123/step/456/costs"
curl -s -X POST "$B/api/currency/convert" -H 'Content-Type: application/json' -d '{"From":"USD","To":"EUR"}'
curl -s -u "$BASIC_USER:$BASIC_PASS" "$B/api/translation?l=en"        # behind the pre-launch gate: one pair from BASIC_AUTH_USERS, there is no default
curl -s -c jar -X POST "$B/User/AjaxLogin" --data-urlencode 'UserName=…' --data-urlencode 'Password=…'
curl -s -b jar -H 'X-Requested-With: XMLHttpRequest' "$B/api/procedure/123/step/456/status"
curl -s -b jar -H 'Content-Type: application/json' -X POST "$B/api/law/9/setpublicvisibility" -d '{"IsVisible":false}'
```

### 3.8 Modifying Surface B (7.x)

- API controllers: `Project/WebAppCore/Api/Presentation/Controllers/*.cs` (`[ApiController]`, explicit `[Route("api/…")]` per action, `[FromBody]` JSON). Use cases `Api/UseCases/Services/*`, data `Api/Data/Impl/*`, DTOs `Api/Presentation/Models/*`. DI registrations in `Program.cs` (~lines 370–415).
- MVC JSON actions: `Controllers/*.cs`, base `AppCode/BaseController.cs`.
- Angular sub-app endpoints: `angular/common/environments/environment.ts` (`$argN` placeholders) + `angular/services/**`. Rebuild with Angular CLI 9 / TypeScript 3.7.5 into `wwwroot/assets/js/angular`; do not change build flags without updating `Views/Summary/Index.cshtml`.
- Legacy jQuery callers live under `wwwroot/assets/js/**`; several already target wrong routes (§8) — fix the JS, not the API, unless asked.
- There is one 7.x branch. A checkout matching the retired shape in §1.2 is rebased onto `main` (§3.6), never built on.

---

## 4. Surface C — Admin API (`admin-api`)

### 4.1 Versions

- **4.x / 5.x: none.** Admin `master`/`tradeportal` is WebForms. `Unctad.eRegulations.APIPublisher` is a RestSharp *client* (settings `eRegApiBaseURI`, `APIUsername`, `APIPwd`); its receiver is unknown and is not this fleet's ERegWebApi.
- **6.x (`database-layer-update-NET8`)**: same codebase lineage as 7.x with 23 controllers, JWT bearer, CORS `CorsOrigins`, Swagger. No `PermissionController`, `AuditController`, `CustomisationController`, `HealthController`, no `/release.json`, no `POST /api/user/refresh`, no `[RequirePermission]` (role checks in code), no object permissions, SHA-256 password compare. Targeted by the pre-May-2026 SPA (`archive/main-2026-05`).
- **7.x (`main`, renamed from `feature/implement-advanced-user-rights` on 2026-09-07)**: documented below. `Project/WebAppCore` is byte-identical between the 2026-09-04 read (`e4fb3881d`) and the 7.4.2 tip (`5fc3e0c81`); what landed in between is a migration granting `recyclebin.delete` to Admin-Super (#29), a Library-side fix so public search reads its filter rows again (#27), and CI.

### 4.2 Runtime and config (7.x)

| Aspect | Contract |
|---|---|
| Stack | ASP.NET Core `net8.0`, Newtonsoft camelCase, Serilog to `./Log/log-<date>.txt`. Image `unctad/eregulations-admin-api`, `EXPOSE 8080`, non-root, bakes `/app/version.json`. |
| Pipeline | Swagger UI + **DeveloperExceptionPage in Production too** → static `/media` (**dir must exist**) → static `/PublicContent` (if exists) → routing → CORS `_myAllowSpecificOrigins` → session → authentication → authorization → `MapReleaseJson()` → `MapControllers()`. No HTTPS redirect/HSTS. |
| Connection strings | `ConnectionStrings:DefaultConnection` (country DB — users/roles/permissions live here now), `GlobalConnection` (still mandatory at boot), `ConsistencyConnection`. Boot throws if any is missing — and the deploy compose sets no `ConnectionStrings__GlobalConnection`, so admin-api boots on the developer value shipped in `appsettings.json` (§6). |
| Keys | `SecretKey` (JWT HMAC; **placeholder in `appsettings.json`, not set by compose — inject**), `CorsOrigins` array (`CorsOrigins__0…`; `WithOrigins().AllowAnyMethod().AllowAnyHeader()`, no credentials), `EREG_RELEASE` env (echoed by `/release.json`), `ASPNETCORE_HTTP_PORTS=8080`. |
| `ApplicationSettings` | `SystemInstanceID` (required), `ApplicationName`, `IsTradeportal`, `AdminBurdenCostEnabled`, `DefaultLang`, `DefaultCurrency`, `PublicConfigFolder` (`PublicConfig`), `CentralRepositoryPath`, `CacheSlidingTime` (hours), `PublicUrl`, `SsoSharedSecret` (**placeholder — inject**), `ProductsWidgetUrl`, `ProductsUrl`, `BugReportEnabled`, `BugReportRecipient`, `SmtpServer`, `SmtpPort`, `SmtpUseAuthentication`, `SmtpUserName`, `SmtpPassword`, `SmtpSendFrom`. |
| Library settings | `Constants.PublicSiteURL`, `PublicSiteVersion`, `ProductsURL`, `ProductsWidgetURL`, `Currency`… come from the Library's compiled `Properties.Settings`, **not** `appsettings.json` *[unverified how deployments override them]*. |
| Volumes | `/app/media` (required; uploads), `/app/Multilang`, `/app/PublicContent` (homepage videos → `/PublicContent/videos/*`), `/app/PublicConfig` (`homepage.<lang>.json`, `custom.css`), `/app/MultilangCentralRepository`. Content dirs must be writable by uid 1654. |
| Language | Catalog routes take `{currentLang}` as a path segment; translation routes take `?lang=`; `IApplicationContext.CurrentLanguage` reads a session key nothing sets → effectively `DefaultLang` (affects step validation messages and `GET /api/team/member/{id}`). |
| Single-replica | SSO tokens and the permission cache are in-memory. Do not scale admin-api horizontally without sticky routing. |

### 4.3 Authentication and authorization (7.x)

```
POST /api/user/login  {username,password}
  -> 200 {fullName,username,accessToken,expiresIn:1800,roles:[{name}]}
  -> 400 "Invalid credentials" (empty)  | 401 (bad)
  password check: bcrypt (PasswordHasher), transparently re-hashes legacy plaintext/SHA-256 rows
JWT: HS256 with SecretKey; claims id (user id), unique_name; exp = now+30min; no iss/aud; NO roles/permissions in the token
Use: Authorization: Bearer <accessToken> on every /api/* call
POST /api/user/refresh  (bearer) -> new 30-min token; 401 user inactive/deleted; 503 lookup failed (do not log out on 503)
     no refresh token, no rotation, no revocation, no logout endpoint
POST /api/user/sso/generate {username,sharedSecret}  anon -> {token}   30-second, one-time, in-memory
POST /api/user/sso {token}  anon -> AuthenticationResponseModel (no roles)
```

Authorization:
- Controllers carry `[Authorize]`; **no fallback policy** — a controller without `[Authorize]` is anonymous (this is why `TranslationController` is open).
- `[RequirePermission("res.action")]` on class or action; `|` = OR. 401 `{error:"Unauthorized",message,timestamp}` without a parseable `id` claim; 403 `{error:"Forbidden",message:"Missing required permission: …",requiredPermission,timestamp}` on failure.
- Effective set = role permissions ∪ user grants − user denials; cached 5 min per user (roles 30 min); **fails closed** on exceptions.
- Object-level: `ObjectPermissions(UserId, ObjectType∈{Objective,Procedure,Block,Step}, ObjectId, PermissionId, Granted)`. For `objectives.*|procedures.*|blocks.*|steps.*` the filter passes if the user holds that permission on **any** object; only `GET /api/objective` filters by object server-side. Everything else is enforced client-side by the SPA (`ObjectAccessService`). If you add a per-object endpoint, check the object yourself via `PermissionBO.HasObjectPermission`.
- Permission names (seeded): `audit.read`; `blocks|objectives|steps.{create,read,update,publish}`; `procedures.{certify,create,publish,read,translate,update}`; `documents.{create,read,update}`; `feedback|filters|homepage|institutions|laws|menus|offices|persons|roles|settings|teampage.{create,delete,read,update}`; `recyclebin.{delete,view}`; `system.admin`; `consultant.admin`. Referenced in code but verify they exist in the instance DB: `users.{read,create,update,delete,assignrights}`, `menus.visibility`, `blocks.delete`, `steps.delete`, `objectives.delete`, `documents.delete`.
- Hard-coded guards: only role `Admin-Administrators` may assign `*.assignrights`; a caller may only assign roles whose permission set ⊆ their own; `menus.visibility` required to see/edit/create public menus.
- Anonymous routes: `GET /health`, `GET /release.json`, `POST /api/user/login|sso|sso/generate`, `GET /api/resources/languages`, `GET /api/resources/appsettings`, `/swagger`, `/media/*`, `/PublicContent/*`, and all of `/api/translation/*`.

### 4.4 Endpoint index (7.x; permission after `—`; `JWT` = `[Authorize]` only)

```
GET  /health -> {status:"ok"}                     anon
GET  /release.json -> {track,version,image,revision,source,built_at,release}   anon, no-store
# user
POST /api/user/login | /api/user/sso | /api/user/sso/generate   anon
POST /api/user/refresh — JWT
GET  /api/user/search?roleId= — users.read|feedback.update|homepage.update|objectives.read -> [{id,fullName,roles}]
GET  /api/user/{id} — same -> ProfileInfo{id,lang,username,email,title,firstName,lastName,timezone,stamp,skype,dateCreated,lastLogin,isCRAlertReceiver,roles[],permissions[]}
POST /api/user (ProfileInfo, id<=0 creates) — users.create -> int ; PUT /api/user — users.update -> int   (password ≥8 chars, ≥2 digits/uppercase; role-subset guard → 403)
DELETE /api/user/{id} — users.delete -> true
POST /api/user/encrypt — users.assignrights -> PasswordMigrationResult
GET  /api/user/feedback?sectionId=&objectId= — feedback.read|objectives.read|homepage.update -> [{id,name}]
POST /api/user/feedback {objectId,userId,sectionId} — feedback.update|homepage.update|objectives.read -> true
DELETE /api/user/feedback/{id} + body {objectId,userId,sectionId} — feedback.delete|homepage.update|objectives.read -> true
# permission
GET  /api/permission | /{id} | /by-name/{name} | /user/{userId} | /user/{userId}/names | /me | /check/{permissionName} | /role/{roleName} | /me/objects | /object/{objectType}/{objectId}/{permissionName} — JWT
GET  /api/permission/user/{userId}/overrides | /user/{userId}/objects | /object/{objectType}/{objectId} — users.read
POST /api/permission/role {roleName,permissionId} — roles.update ; DELETE /api/permission/role/{roleName}/{permissionId} — roles.update
POST /api/permission/role/create {name,description?} — roles.create ; PUT /api/permission/role/{roleName} {description} — roles.update ; DELETE /api/permission/role/{roleName}/delete — roles.delete (400 if users assigned)
POST /api/permission/user/grant | /user/deny {userId,permissionId,reason?} — users.assignrights ; DELETE /api/permission/user/{userId}/{permissionId} — users.assignrights
PUT  /api/permission/user/{userId}/permissions {permissions:[{permissionId,granted:true|false|null}]} — users.assignrights (null removes override)
POST /api/permission/object/grant {userId,objectType,objectId,permissionId} — users.assignrights
PUT  /api/permission/object/{objectType}/{objectId}/{userId} [{permissionId,granted}] — users.assignrights
DELETE /api/permission/object/{objectType}/{objectId}/{userId}/{permissionId} — users.assignrights
# resources (catalogs -> [{val,text}])
GET  /api/resources/languages -> [{val,text,isPrincipal,isRTL}]   anon
GET  /api/resources/appsettings -> {defaultLang,applicationName,defaultCurrency,publicUrl,isTradeportal,adminBurdenCostEnabled,bugReportEnabled,productsWidgetUrl,productsUrl}   anon
GET  /api/resources/sitemenu/{lang} -> [{key,title,pageUrl,id,childItems[]}] — JWT   (admin navigation; DB tables SiteMenu/SiteMenu_i18n)
GET  /api/resources/{stepresulttypes|aggregateoperators|genericrequirementtypes|globalfilters|laws|stepnocostsreasons|costcurrencies|costoperators|costparameters|costtypes|steponlinetypes}/{lang} — procedures.read
GET  /api/resources/{countries|entitiesincharge|unitsincharge|physicalrepresentations|representationthirdparties|regions|days|hours|minutes|mediatypes}/{lang} — JWT
GET  /api/resources/roles -> [{val,text,userCount}] — users.read ; GET /api/resources/roles/assignable — JWT ; GET /api/resources/categorytypes — feedback.read
# objective (procedure tree)
GET  /api/objective?showBlocks=true&showSteps=true — objectives.read -> RegulationTreeItem[] (object-filtered)
GET  /api/objective/treerecyclebin — recyclebin.view ; GET /api/objective/parentstree/{objectivesOnly} — objectives.read
GET  /api/objective/{id} — objectives.read -> ObjectiveModel ; POST /api/objective — objectives.create -> int ; PUT /api/objective — objectives.update -> int ; DELETE /api/objective/{id} — objectives.delete
POST /api/objective/recyclebin/{id} — objectives.delete ; POST /api/objective/duplicate (ObjectiveModel, id=source) — objectives.create ; POST /api/objective/publish — procedures.publish ; POST /api/objective/emptyrecyclebin — recyclebin.delete
POST /api/objective/moveobjective | /moveblock | /movestep  {id,oldParentId,oldParentChildrenIdList,newParentId,newParentChildrenIdList} — objectives.update | blocks.update | steps.update
POST /api/objective/stepalternative {stepId,blockId,isAlternative} — steps.update ; POST /api/objective/deletefilter {filterId,objectiveId} — objectives.update
GET  /api/objective/feedbackusers/{objectiveId} — objectives.read ; POST /api/objective/feedbackusers?objectiveId= [ProfileInfo] — JWT only
# block
GET  /api/block/{id} — blocks.read ; POST /api/block — blocks.create ; PUT /api/block — blocks.update ; DELETE /api/block/{id} — blocks.delete
POST /api/block/recyclebin/{id} — blocks.delete ; POST /api/block/duplicate — blocks.create ; POST /api/block/publish — blocks.publish
# step
GET  /api/step/{id}?loadCertifyer=false — steps.read -> StepModel + stepSectionVisibility, parentsIds[, certifier]
GET  /api/step/{id}/contact | /results | /documents | /costs ({stepCosts[],attachments[]}) | /timeframe | /laws | /additionalinfo | /recourse | /review/{lang} | /statushistory | /certification — steps.read
POST /api/step — steps.create -> int ; PUT /api/step — steps.update -> int | {id,warnings[]} ; DELETE /api/step/{id} — steps.delete
POST /api/step/recyclebin/{id} — steps.delete ; POST /api/step/duplicate — steps.create ; POST /api/step/publish — steps.publish
PUT  /api/step/{id}/certification {isCertificationVisible,certificationDate,certificationUser,certificationEntityInCharge_Id,attachments[]} — JWT only
# document / law
GET  /api/document/search?name= — documents.read ; GET /api/document/{id}/{showDependencies} — documents.read ; POST/PUT /api/document — documents.create/update ; DELETE /api/document/{id} — documents.delete
GET  /api/law/search?name= — laws.read|steps.read ; GET /api/law/{id}/{showDependencies} — laws.read ; POST/PUT /api/law ; DELETE /api/law/{id}
# contacts  (x = entityincharge→institutions | unitincharge→offices | personincharge→persons)
GET  /api/{x}/search?searchTerm= — {perm}.read|steps.read ; GET /api/{x}/{id} ; POST /api/{x} ; PUT /api/{x} ; DELETE /api/{x}/{id}
# media / upload
GET  /api/media?type=&showMediasNotLinked=true&searchTerm= — documents.read (400 when empty!) ; POST/PUT /api/media — documents.create/update
POST /api/upload (multipart file) — documents.create -> {name,thumbnail:"",size} ; POST /api/upload/{thumbnailType 0..11} -> {name,thumbnail,size}   files served at /media/<name>
# settings-like
GET  /api/filter — filters.read|procedures.read ; POST/PUT /api/filter ; DELETE /api/filter/{id} ; POST /api/filter/updateorder {filterId:order}
GET  /api/costvariable | /by-operator | /{id} | /search?searchLang=&translationLang=&searchTerm= — settings.read|steps.read ; POST /api/costvariable ; PUT /api/costvariable/{id} ; DELETE /api/costvariable/{id} — settings.*
GET  /api/currency — settings.read ; POST /api/currency/select | /unselect (CurrencyItem, uses symbol) — settings.update
GET/POST/PUT /api/thirdparty ; DELETE /api/thirdparty/{id} — settings.*
GET  /api/adminburden — settings.read ; POST /api/adminburden/level | /zone | /cost — settings.update
# feedback
GET  /api/feedback?sortingField=Feedback_registerDate|Feedback_countryID|Feedback_id|Feedback_type|Feedback_status&sortOrder= — feedback.read (404 when none)
GET  /api/feedback/{id} — feedback.read -> HTML string (use responseType text)
GET  /api/feedback/categories | /categories/{id} ; POST/PUT /api/feedback/categories ; DELETE /api/feedback/categories/{id} — feedback.*
# menus
GET  /api/menu/menutree | /menurecyclebin | /tree | /{id} — menus.read ; POST /api/menu ; PUT /api/menu ; DELETE /api/menu/{id} — menus.create/update/delete (+menus.visibility for public menus)
POST /api/menu/emptyrecyclebin — menus.delete (POST, not DELETE) ; POST /api/menu/searchmenus (FilterRules) — menus.read ; POST /api/menu/movetorecyclebin?id= — menus.delete
# homepage / customisation / team
GET/PUT /api/homepage/{lang} — homepage.read/update (HomePage JSON doc) ; POST /api/homepage/upload-video (mp4 webm mov avi mkv wmv mpeg mpg) — homepage.update -> {url,fileName}
GET  /api/customisation -> CSS as JSON string — homepage.read ; PUT /api/customisation  body = JSON string literal — homepage.update
GET/PUT /api/team — teampage.read/update ; GET /api/team/member/list/{type 0=Authorities|1=EregTeam}/{lang} ; GET /api/team/member/{id} ; POST/PUT /api/team/member ; DELETE /api/team/member/{id}
# translation  (ANONYMOUS — no [Authorize])
GET  /api/translation?lang= -> {label:text} ; POST /api/translation?lang= {label,defaultValue} -> string
GET  /api/translation/<c>?lang= ; GET /api/translation/<c>/{id}?lang= ; PUT /api/translation/<c>/{id}?lang=   c ∈ labels, filters, filter-options, cost-variables, options, site-menus, menus, persons-in-charge, units-in-charge, entities-in-charge, objectives, blocks, steps, laws, documents
POST /api/translation/{objectives|blocks|steps}/{id}/publish -> id   (publishes as unique_name or "system")
# audit / bug report
GET  /api/audit?objectId=&objectType=&username=&dateFrom=&dateTo=&lastId=&pageSize=100 — audit.read -> {nbItemsReturned,lastIdProcessed,hasMore,records[{id,action,actionLabel,entityTable,entityTableKey,objectName,auditDate,userName}]}   keyset: pass lastIdProcessed as lastId
GET  /api/audit/{id}/fields — audit.read -> [{id,fieldName,oldValue,newValue}]
POST /api/bugreport (multipart description, link, attachments[]) — JWT -> {message}   (400 if BugReportEnabled=false)
```

Key request DTOs: `ObjectiveModel{id,name,isInRecycleBin,additionalInfo,explanatoryText,webPageKeywords,webPageDescription,isVisibleToGuest,image1..3,isFilterSearchResult,objectiveBlocks[{id,objectiveId,blockId,order}],objectiveParent{id,parentId,childId,order},objectivePerLangVisibilities[{lang,visible}],objectiveSectionVisibility{is*Visible},objectiveFilters[{id,name,isActive,isAppliedToParent,defaultOptionId,options[{id,name,isApplied,isInherited,isOwned,order}]}],attachments[ObjectMediaModel]}`; `BlockModel{id,name,isOptional,isInRecycleBin,parentsIds[]}`; `StepModel` (~50 scalar fields + `stepCosts[]`, `stepLaws[]`, `stepDocuments[]`, `stepResults[]`, `attachments[]`, `stepSectionVisibility`, `parentsIds[]`); `DocumentModel{id,name,isVisibleInPublicDirectory,documentType,isAttachmentURL,attachmentURL,attachmentFilename,attachmentFilesize,thumbnailFilename,numberOfPages,documentCosts[],documentDependencies[]}`; `LawModel{…,lawDependencies[]}`; `EntityInChargeModel` (address/contact fields + `scheduleDay{1..7}*` + `zone_Id` + `linkedSteps[]`, `linkedUnitsInCharge[]`, `attachments[]`); `MenuModel{id,name,isVisibleToGuest,isWidePage,explanatoryText,webPageKeywords,webPageDescription,isVisibleInPublicMenu,isVisibleInPublicHomePage,image1..3,iconURL,iconActiveURL,nbCols,langsMenuVisible[],objectiveId,blockId,parentId,isInRecycleBin,children[{id,name,order}],attachments[]}`; `ObjectMediaModel{id,name,fileName,fileExtension,previewImageName,type(AttachmentType name),length,order,isUrl}`. `AttachmentType`: StepResult=1, ContactSection=2, GenericRequirement=3, Law=4, CostSection=5, TimeframeSection=6, AdditionalInfo=7, Certification=8, Menu=9, PublicTeam=10, Recourse=11, Objective=12, EntityInCharge=13, ObjectiveSummary=14. Thumbnail types for `/api/upload/{n}`: 0 LAYOUT_LEFT_LOGO, 1 LAYOUT_RIGHT_LOGO, 2 LAYOUT_LEFT_IMAGE, 3 LAYOUT_MIDDLE_IMAGE, 4 MENU_IMAGE, 5 STEP_RESULT, 6 DEPARTMENT_IMAGE, 7 UNIT_IN_CHARGE_IMAGE, 8 PERSON_IN_CHARGE_IMAGE, 9 CONTACT_ATTACHMENTS, 10 FORM, 11 CONTEXT_ATTACHMENTS. `FeedbackSection`: LayoutHomePage=1, Menu=2, StepInProcedure=3, BlockInProcedure=4, Procedure=5. Full DTO field lists: read `Project/WebAppCore/Models/*.cs` on the branch you target.

### 4.5 Recipes

```bash
C=https://api.<instance>
TOKEN=$(curl -s -X POST "$C/api/user/login" -H 'Content-Type: application/json' -d '{"username":"…","password":"…"}' | jq -r .accessToken)
H="Authorization: Bearer $TOKEN"
curl -s "$C/api/permission/me" -H "$H"                                   # what can this user do
curl -s "$C/api/objective?showBlocks=true&showSteps=true" -H "$H"         # regulation tree
curl -s "$C/api/step/456" -H "$H" | jq '{id,name,parentsIds}'
curl -s -X PUT "$C/api/step" -H "$H" -H 'Content-Type: application/json' -d @step.json   # full StepModel, id required
curl -s -X POST "$C/api/step/publish" -H "$H" -H 'Content-Type: application/json' -d '{"id":456}'
curl -s -F file=@logo.png "$C/api/upload/0" -H "$H"                       # -> {name,thumbnail,size}; then /media/<name>
curl -s "$C/api/audit?pageSize=50" -H "$H"
curl -s -X POST "$C/api/user/refresh" -H "$H"
curl -s "$C/api/translation/steps/456?lang=fr"                            # anonymous (bug, see §8)
```

### 4.6 SPA behaviour you must stay compatible with

- Base URL: `window.__env.apiUrl` (injected by the deploy nginx `sub_filter` from `ADMIN_API_URL`), with a hard-coded fallback host baked into the bundle. All URLs from `src/environments/environment.ts`.
- Login → `POST /api/user/login`, then `GET /api/permission/me` (explicit bearer header) to enrich the principal. `sessionStorage`: `accessToken`, `tokenExpiresIn` (absolute ms), `fullName`, `username`, `userId` (decoded `id` claim), `sessionActive`; `localStorage`: `roles`, `permissions`, `languages`, `language`.
- Interceptor chain: bearer injection when token valid → activity-based `POST /api/user/refresh` throttled to one per 5 min (30 s timeout) → any 401 (except on refresh) clears the session and routes to `/auth/login`. 60-s expiry poll; logout is client-side only.
- Guards: `authGuard`, `permissionGuard` (route `data.permission`/`permissions[]`+`requireAll`), `roleGuard`. Object access: `GET /api/permission/role/{name}` per role + `GET /api/permission/me/objects`.
- SSO entry: SPA route `/auth/sso?token=` → `POST /api/user/sso`.
- Known SPA→API mismatches (do not "fix" the API to match unless asked): `DELETE /api/menu/emptyrecyclebin` (API is POST → 405); `…/search/{term}` path form (API reads `?searchTerm=`/`?name=`; only called with `''`); dead calls `GET /api/user/{id}/permissions/denied`, `POST /api/user/{id}/roles`.
- SPA `main` (renamed from `feature/implement-advanced-user-rights` on 2026-09-07) is 241 commits ahead of `archive/main-2026-05`, the old `main`, which targets C 6.x.

### 4.7 Modifying Surface C (7.x)

- Controllers `Project/WebAppCore/Controllers/*.cs`: `[Authorize] [Route("api/<name>")]` on the class, `[RequirePermission("x.y")]` on class or action. Add `[RequirePermission]` to every new action — there is no default policy.
- Services `Services/Impl/*`, models `Models/*`, filters `Authorization/RequirePermissionAttribute.cs`, settings `Infrastructure/ApplicationSettings.cs`, DI/pipeline `Program.cs`. Business/data layer in `Project/Unctad.eRegulations.Library` (EF Core contexts `CountryDbContext`, `GlobalDbContext`, `ConsistencyDbContext`; `*BO` classes).
- New permission names must be seeded in SQL (`Database/*.sql`, `openspec/changes/implement-backend-permissions/scripts/*.sql`) and assigned to roles; `openspec/.../permission-matrix.md` is stale — do not trust it.
- Tests: `Project/WebAppCore.Tests` (xUnit). Run them.
- Any change to login/token shape must be mirrored in the SPA `AuthService`/`UserContextService`.
- After changing translation-related behaviour, remember only `LangAdmin.txt` is read by the SPA for labels (skill `merged-eregulations-translations-into-langadmin`).

---

## 5. Cross-application flows

**Public → Admin SSO ("Go to Admin")** (5.x `tradeportal` since 2026-08-04, and 7.x):
1. Browser: `GET {public}/User/GoToAdmin?returnUrl=…` (needs the public cookie).
2. Public server: `POST {AppSettings:AdminApiUrl}/api/user/sso/generate` `{Username, SharedSecret: AppSettings:SsoSharedSecret}` → `{token}`.
3. Browser: `302 {AppSettings:AdminSiteUrl}/auth/sso?token=…&returnUrl=…`.
4. SPA: `POST {apiUrl}/api/user/sso` `{token}` → JWT. Token is one-time, 30 s, in-memory on admin-api.
Config must match: public `AppSettings__AdminApiUrl` = the browser/server-reachable admin-api URL, public `AppSettings__SsoSharedSecret` = admin-api `ApplicationSettings__SsoSharedSecret`. Missing config degrades silently to a plain redirect to `AdminSiteUrl`.

**Content sharing**: no HTTP. Admin writes uploads to `/app/media` and homepage JSON/CSS to `/app/PublicConfig`; Public serves the same bind mounts. Both read the same SQL Server DBs.

**Monitor** (`eRegulations-Monitor`) probes `GET {public}/`, `GET {admin-api}/health` (expects `{version, errors:{last24h}}` — admin-api actually returns `{status:"ok"}`), `GET {admin-web}/health` and `/version` (deploy compose overrides the SPA nginx config and drops `/version`). Retries once with Basic auth on 401. Legacy Windows instances: root URL only.

**External services called by the platform**: the HS-code service (`LibrarySettings:ProductsURL`), the product widget (`ProductsWidgetURL`), a currency-converter API (`CurrencyConverter__ApiKey`), Google reCAPTCHA (`Google:ReCaptchaSecretKey`), the ASYCUDA tariff API (`TariffsApi*`), the legacy CAS/eID server (`ERegCASServerURL` / `Cas:ServerURL`).

---

## 6. Deployment cheat sheet (7.x, `eRegulations-deploy`)

| Service | Image | Port | Host name (docs / provisioner) | Health |
|---|---|---|---|---|
| admin-api | `unctad/eregulations-admin-api` | 8080 | `api.<country>.<suffix>` (legacy scheme) / `api-<slug>.<suffix>` | `/release.json`, `/health`, `/swagger` |
| admin-web | `unctad/eregulations-admin-web` (nginx) | 4200 | `admin.<country>.<suffix>` (legacy scheme) / `admin-<slug>.<suffix>` | `/health` → `ok`; injects `window.__env.apiUrl` |
| public | `unctad/eregulations-public` | 8080 | `<country>.<suffix>` (legacy scheme) / `<slug>.<suffix>` | `/release.json` (compose healthcheck accepts 200 or 404) |
| sqlserver | `mcr.microsoft.com/mssql/server:2022-latest` | 1433 | alias `eregulations-shared-sqlserver` or `eregulations-<slug>-sqlserver` on network `eregulations-shared` | `sqlcmd SELECT 1` |

Coolify "Domains" format: `https://<host>:<internal port>`. No path prefixes anywhere. `channel/stable` carries `release.yml` (format 2; 7.4.2 on 2026-09-11), which pins Public, Admin, Statistics and SPA to `main` by SHA and records every image's tag and digest — read it rather than guessing which branch an image came from. `docker-compose.yml` on `main` references the `:unreleased` tags. Instance lifecycle and creation are in `docs/INSTANCE-LIFECYCLE.md` and `docs/NEW-INSTANCE.md`; the `eregulations migrate` CLI (eight resumable phases) is in the repo since 2026-09-08 although `NEW-INSTANCE.md` still calls it planned.

Env → .NET mapping (both apps unless noted):

```
SHARED_SQL_HOST, SA_PASSWORD, COUNTRY_DB, CONSISTENCY_DB, STATISTICS_DB(public)
   admin-api: ConnectionStrings__DefaultConnection, __ConsistencyConnection   (GLOBAL_DB legacy, no longer set)
   public:    ConnectionStrings__CountryDbContext, __ConsistencyDbContext, __StatisticsDbContext
SYSTEM_INSTANCE_ID -> ApplicationSettings__SystemInstanceID (admin) / LibrarySettings__SystemInstanceID (public)
DEFAULT_LANG, CURRENCY, COUNTRY_NAME, COUNTRY_CODE, APP_NAME -> ApplicationSettings__*/LibrarySettings__*/AppSettings__*
PUBLIC_URL      -> ApplicationSettings__PublicUrl + CorsOrigins__3 (admin) ; LibrarySettings__PublicSiteURL (public)
ADMIN_WEB_URL   -> CorsOrigins__2 (admin) ; AppSettings__AdminSiteUrl (public)
ADMIN_API_URL   -> admin-web nginx sub_filter: <script>window.__env={"apiUrl":"…"}</script>   (browser-reachable!)
HOST_PORT_ADMIN_WEB/HOST_PORT_ADMIN_API -> CorsOrigins__0/__1 (localhost dev)
SecretKey                               -> admin-api JWT key   (NOT in compose; set explicitly)
ApplicationSettings__SsoSharedSecret    -> admin-api ; AppSettings__SsoSharedSecret + AppSettings__AdminApiUrl -> public   (set by provisioner or by hand)
BASIC_AUTH_ENABLED, BASIC_AUTH_USERS    -> public (release 7.3.2 and later; no default credential; /release.json stays open)
CONTENT_DIR/{media,Multilang,PublicConfig,PublicContent}, MULTILANG_CENTRAL_REPOSITORY_HOST_PATH -> bind mounts, uid 1654 ; /app/media REQUIRED for admin-api
EREG_RELEASE                            -> /release.json (origin/main rings)
```

Smoke test after deploy: `curl -i -X POST https://api.<inst>/api/user/login -H 'Content-Type: application/json' -d '{"username":"…","password":"…"}'` → 200 + JWT; `curl -I https://<inst>/`; `curl -I https://<inst>/procedure/<id>`; `curl -I https://<inst>/media/<file>`; compare `RolePermissions` counts with a healthy sibling instance (a working login alone does not prove permissions).

---

## 7. Migration notes (moving a consumer between versions)

| From → To | What breaks |
|---|---|
| A 4.x → A 6.x | Bearer auth gone (drop the header; expect nothing to be protected). `?lang=` ignored → deploy per-language instances or fix the session writer. Dictionaries become objects (`documentCost`). `StepModel.costs` becomes an array. `ApiServerUrl` must be set or links are host-less. Browser callers need their origin added to the hard-coded CORS policy in `Program.cs`. |
| A (any) → 7.x | No target. Options: (a) port `ERegWebApi` to pair with the 7.x Library (its Library reference path and `SnapshotBuilder` signature already changed on 6.x); (b) expose the needed read routes on Public 7.x (`Api/Presentation`) — it already has the procedure/step read model, PascalCase; (c) expose them on admin-api with `[AllowAnonymous]` (not currently done). Decide with the product owner; record the choice. |
| B 5.x → B 7.x | Spelling `requeriments`→`requirements`, `requerimentscost`→`requirementscost`. `/api/procedure/{id}/details` now returns the details object. `/api/login` GET is back. Currency failure 400→502. Tariffs routes answer 404 until the `TariffsApi*` settings are set. Unauthenticated cookie calls return 302 unless `X-Requested-With` is sent. Site may sit behind Basic auth. JSON stays PascalCase. |
| C 6.x → C 7.x | Every endpoint now needs a permission; users with roles but no `RolePermissions` rows get 403 everywhere (seed permissions). `POST /api/user/refresh` available. Login response unchanged. Passwords re-hashed to bcrypt on first login (older 7.x images: SHA-256 hex compare; the `deploying-legacy-eregulations-instance` skill's `references/phase-5-credential-hashing.md` hashes with `HASHBYTES('SHA2_256', CONVERT(VARCHAR(200), Password))`). New controllers: Permission, Audit, Customisation, Health. |
| SPA `archive/main-2026-05` → SPA `main` | Requires C 7.x (permission endpoints on login). |

---

## 8. Known defects — do not rediscover, do not silently "fix" without a ticket

The list lives in the private repository `UNCTAD-eRegistrations/eregulations-knowledge-base`
(`api-surfaces-defects.md` for the prose, `defects.json` for the routing rules the
`eregulations-issue` skill reads at runtime). This repository is public, and a list of
open defects on lines running in production does not belong in it. Read it with

```bash
gh api repos/UNCTAD-eRegistrations/eregulations-knowledge-base/contents/api-surfaces-defects.md -H 'Accept: application/vnd.github.raw'
```

No access → treat every symptom as unknown; do not reconstruct the list from memory.

---

## 9. Things you must not do

- Do not add endpoints, features or fixes to 4.x/5.x/6.x branches unless the task is itself the upgrade to 7.x (or an `unsupported_version` override is recorded with `scripts/audit.py`).
- Do not send `?lang=` to Surface A 6.x or Surface B (use `?l=`); do not send `?l=` to Surface A or C.
- Do not look for a filter catalog on the Public site API, or for procedure results/laws on the Public site API of a 4.x instance — they do not exist there (§1.3); use ERegWebApi or the Admin API.
- Do not assume camelCase on Surface B 7.x (PascalCase) or PascalCase on Surface C (camelCase).
- Do not call Surface C without `Authorization: Bearer` (except the anonymous routes listed in §4.3); do not put roles/permissions in the JWT (the server ignores them; permissions are looked up server-side).
- Do not scale admin-api to multiple replicas without sticky sessions (SSO tokens, permission cache).
- Do not deploy admin-api without `/app/media`.
- Do not trust `eRegulations-4.0-API/CLAUDE.md`, `eRegulations-4.0-Admin/openspec/.../permission-matrix.md`, `eRegulations-4.0-Public/README.md` (Docker appsettings), or `eRegulations-deploy/docs/ADMIN-SETUP.md` (`GLOBAL_DB`) for endpoint or config facts.
- Do not send form-encoded bodies to `[FromBody]` actions on .NET 8 (`[ApiController]` → 415).
- Do not paste credentials or host addresses from any repository file into docs, tickets, or this plugin — fleet data lives only in the operator overlay (`resolution.md`).

---

## 10. Unverified / open

1. Whether ERegWebApi still runs on any Windows host and who (ITC? comparators?) calls it — no source in the fleet references those consumers.
2. ~~Which 7.x Public branch is canonical~~ — settled 2026-09-07: `main`; `dot-net8-roxana-user-rights` is retired (§3.6).
3. Library-side behaviour: session `LANGUAGE_KEY` writer (A 6.x), `SiteContactInformation` fields, per-deployment override of compiled Library settings (`Constants.PublicSiteURL`, `ProductsURL`).
4. Where production admin-api gets `SecretKey` (image placeholder vs Coolify var).
5. Password hashing on the deployed 7.4.x images (bcrypt on the Admin tip since PR #19/#20; SHA-256 before).
6. Runtime behaviour of cookie-scheme 302-vs-401 on Public 7.x (inferred from framework defaults).
7. `APIPublisher`'s target (`eRegApiBaseURI`) on Admin 4.x.

---

## 11. Source snapshot (read 2026-09-04, re-checked 2026-09-11)

On 2026-09-07 the 7.x branches were renamed to `main` in Public, Admin, SPA and Statistics;
the 2026-09-04 read commits are ancestors of every `main` below. "read at" gives the commit
the section text was derived from where the tip has since moved.

| Repo | Branch | Commit | Date | Role |
|---|---|---|---|---|
| eRegulations-4.0-API | `master` | `324748e` | 2025-11-25 (functional: `d1e69e4` 2022-07-01) | A 4.x |
| eRegulations-4.0-API | `master-diverged` | `0ff6c13` | 2018-12-10 | ancestor snapshot |
| eRegulations-4.0-API | `database-layer-update` | `7050453` | 2026-09-01 | A net48+EF6 |
| eRegulations-4.0-API | `database-layer-update-NET8` | `23635f7` | 2026-01-20 | A 6.x |
| eRegulations-4.0-Public | `master` | `aedcbdae3` | 2026-01-27 | B 4.x |
| eRegulations-4.0-Public | `tradeportal` | `d9231082c` | 2026-09-02 | B 5.x |
| eRegulations-4.0-Public | `database-layer-update-NET8` | `239655363` | 2026-04-24 | B 6.x |
| eRegulations-4.0-Public | `dot-net8-roxana-user-rights` | `173a77063` | 2026-09-01 | retired 7.x branch, 34 commits not on `main` (§3.6) |
| eRegulations-4.0-Public | `main` (was `feature/implement-advanced-user-rights`) | `5c0a8efdf` (release 7.4.2 pin; tip `1419cbde5`) | 2026-09-11 | B 7.x — §3.5 re-read here; first read at `99c6ba9a1` (2026-09-04) |
| eRegulations-4.0-Admin | `master` | `6243b0131` | 2026-02-26 | WebForms, no API |
| eRegulations-4.0-Admin | `database-layer-update-NET8` | `92f5f5777` | 2026-09-01 | C 6.x |
| eRegulations-4.0-Admin | `main` (was `feature/implement-advanced-user-rights`) | `5fc3e0c81` (release 7.4.2 pin and tip) | 2026-09-09 | C 7.x — `Project/WebAppCore` unchanged since the read at `e4fb3881d` (2026-09-04) |
| eRegulations-5.0-Admin-SPA | `archive/main-2026-05` (the old `main`) | `0dc31e10` | 2026-05-04 | targets C 6.x |
| eRegulations-5.0-Admin-SPA | `main` (was `feature/implement-advanced-user-rights`) | `eba020fb` (release 7.4.2 pin and tip) | 2026-09-10 | targets C 7.x; read at `f49340fa`, only the customisation screen changed since |
| eRegulations-Statistics | `main` (was `database-layer-update-NET8`) | `a461524` | 2026-09-09 | Library referenced by the Public build; pinned in `release.yml` |
| eRegulations-deploy | `main` | `f3ac736` | 2026-09-11 | compose/Coolify, docs, `eregulations migrate` CLI |
| eRegulations-deploy | `channel/stable` | `d76af97` | 2026-09-11 | `release.yml` = 7.4.2 (Public 7.4.2; admin-api and admin-web images reused from 7.4.1) |

Key file paths (7.x): Admin `Project/WebAppCore/{Program.cs,Controllers/,Authorization/RequirePermissionAttribute.cs,Services/Impl/UserService.cs,Infrastructure/ApplicationSettings.cs,appsettings.json,Dockerfile}`; Public `Dockerfile` (repository root), `release-pins.yml`, `Project/WebAppCore/{Program.cs,ReleaseEndpoint.cs,AppCode/ApiJson.cs,AppCode/LicensedAssetsGate.cs,Api/Presentation/Controllers/,Api/Presentation/Infrastructure/ControllerExceptionFilterAttribute.cs,Middleware/BasicAuthGate.cs,Middleware/BasicAuthMiddleware.cs,Configuration/ForwardedHeadersSetup.cs,Controllers/,appsettings.json}`, `angular/common/environments/environment.ts`; SPA `src/environments/environment.ts`, `src/app/shared/auth/services/auth.service.ts`, `src/app/shared/backend/interceptors/*.ts`; deploy `docker-compose.yml`, `docs/*.md`, `instances/_template/.env.example`.
