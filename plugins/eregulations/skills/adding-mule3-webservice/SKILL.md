---
name: adding-mule3-webservice
description: >
  Use when adding a new external webservice (a SOAP or REST backend exposed as
  a REST endpoint) to a `mule3-<country>` eRegistrations integration repo —
  e.g. "add VerifyX like VerifyTIN", "expose this SOAP proxy as /api/...",
  "new webservice in mule3-lesotho". Covers the Mule 3 flow, the Java
  `Callable` component, the SOAP template, and all the registration touchpoints
  that are easy to forget. This is the `dev` dispatch target of `ereg-router`
  for Mule 3 integration work. DO NOT TRIGGER for changing an EXISTING
  webservice's mapping in BPA (that is a bot/mapping change), or for the
  platform's own services outside the `mule3-<country>` repos.
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
metadata:
  version: "0.1.0"
  version-date: "2026-08-26"
  argument-hint: "[repo] [service-name]"
---

# Adding a webservice to a mule3-<country> repo

## Overview

mule3-`<country>` repos are Mule 3.9 (CE) ESB apps that wrap external government
backends (usually SOAP behind a WSO2/API-gateway proxy) and expose them as REST
JSON endpoints under `/api/...` for the eRegistrations platform to call.

Adding a webservice means **mirroring an existing one**. The cheapest reliable
path: find the closest existing service (e.g. `verify-tin`), copy its four moving
parts, rename, and adapt the request/response shape.

**The trap:** the code (flow + Java) is the obvious part. The service silently
fails to deploy or stays invisible to the platform if you forget the
**registration touchpoints** — and there are several, in different files.

## The five touchpoints (ALL required)

A working endpoint needs changes in **every** one of these. Missing any one is the
common failure mode:

| # | File | What | Forgetting it means |
|---|------|------|---------------------|
| 1 | `src/main/app/<name>.xml` | The Mule flow (listener → component → JSON) | No endpoint at all |
| 2 | `src/main/java/.../<Name>.java` | Java `Callable`: HTTP call, auth, XML→JSON | Flow has no logic |
| 3 | `src/main/resources/<Name>.xml` | SOAP request template (SOAP backends only) | No request body to send |
| 4 | `src/main/app/mule-deploy.properties` | Add `<name>.xml` to `config.resources` | **Flow never loads** (silent) |
| 5 | `src/main/resources/properties-*.properties` | Endpoint URL in **all** env files | NPE / wrong env at runtime |
| 6 | `src/main/resources/servicelist.json` | Service descriptor (inputs/outputs) | **Invisible to BPA bots** — platform can't map it |

Touchpoints 4 and 6 are the ones agents skip. They are not optional.

## Step-by-step

### 0. Find the reference service
```bash
grep -rl "implements Callable" src/main/java        # existing components
cat src/main/app/mule-deploy.properties              # what's registered
```
Pick the closest existing service and read its flow, Java class, template, and its
`servicelist.json` entry. Copy that, don't invent.

### 0b. Probe the live backend FIRST — don't assume the transport
**A `?wsdl` URL does not mean the backend speaks SOAP**, and "mirror the existing
SOAP service" can be wrong. Many gov gateways (WSO2 etc.) expose a generic
pass-through proxy whose WSDL has an empty `<wsdl:types/>` and a single `mediate`
operation — it tells you nothing about the payload. The API doc's sample is
authoritative: a JSON sample means send JSON. Confirm with one curl before writing
a line of code (credentials are in `properties-*.properties`: `user-ws`/`pwd-ws`):
```bash
# try JSON
curl -sk -u 'USER:PWD' -H 'Content-Type: application/json' \
     -X POST --data '{"param":"<sample>"}' -w '\n[%{http_code}]\n' "<endpoint>"
# try SOAP (text/xml) and compare which one the backend accepts
```
`{"status":"Unsupported Payload"}` / HTTP 400 = wrong transport. A 200 (or even a
404 with a sensible business message) = right transport. This single check would
have saved a SOAP-vs-JSON misimplementation.

### 1. Flow — `src/main/app/<name>.xml`
One flow per file. The HTTP listener uses the **shared** `HTTP_Listener_Configuration`
(defined in `servicelist.xml`, `basePath="/api"`), so a listener `path="/verifyX"`
is reached at **`/api/verifyX`**.

```xml
<flow name="<name>Flow">
    <http:listener config-ref="HTTP_Listener_Configuration" path="/verifyX" allowedMethods="GET" doc:name="HTTP"/>
    <set-variable variableName="param" value="#[message.inboundProperties.'http.query.params'.param]" doc:name="param"/>
    <logger message="starting verifyX with #[flowVars.param]" level="INFO" doc:name="Logger"/>
    <parse-template location="VerifyX.xml" doc:name="Parse Template"/>   <!-- SOAP backends only -->
    <component class="org.unctad.eregistrations.mule.<country>.VerifyX" doc:name="Java"/>
    <object-to-string-transformer doc:name="Object to String"/>
    <json:object-to-json-transformer doc:name="Object to JSON"/>
    <catch-exception-strategy doc:name="Catch Exception Strategy">
        <object-to-string-transformer/>
        <logger message="error on VerifyX #[message.payloadAs(java.lang.String)] error #[message]" level="ERROR"/>
        <set-payload value="{ &quot;status&quot;:false, &quot;message&quot;:&quot;Error sending information to the service&quot; }" mimeType="application/json"/>
    </catch-exception-strategy>
</flow>
```
Query params: `#[message.inboundProperties.'http.query.params'.NAME]`. For POST
bodies, read the existing POST services (e.g. `business-registrations.xml`).

### 2. SOAP template — `src/main/resources/<Name>.xml` (SOAP backends only)
```xml
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Header/>
   <soapenv:Body>
      <OperationName>
         <param>#[flowVars.param]</param>
      </OperationName>
   </soapenv:Body>
</soapenv:Envelope>
```
The SOAP operation/element names come from the backend **WSDL**. If the doc only
gives a JSON sample, infer from the analogous existing service and **flag the
assumption** — it's the one thing you can't derive and the only thing that breaks
against the live gateway.

### 3. Java component — `src/main/java/.../<Name>.java`
Copy the closest existing `Callable`. The reusable skeleton: Base64 Basic auth
from `${user-ws}`/`${pwd-ws}`,
`HttpPost` with the right `Content-Type` (`application/json` for a JSON backend —
see step 0b), parse the response, and **flatten** the nested response into the flat
keys that `servicelist.json` outputs declare. Inject the endpoint with
`@Value("${<service>.url}")`. (For a JSON backend, `new JSONObject(body)` — it
tolerates the trailing commas some gateways emit; for SOAP, strip namespaces then
`org.json.XML.toJSONObject(...)`.)

> **Trust-all SSL is in the existing components, and it is a development
> shortcut — do not carry it into anything that reaches production.**
> The reason it is there is real: some government gateways present self-signed
> certificates. But a trust-all `TrustManager` disables certificate *and*
> hostname verification for that client, so the connection it protects can be
> intercepted by anything on the path — and these components carry Basic-auth
> credentials in the very same request.
>
> If you copy a component that has it, treat removing it as part of the work,
> not as a follow-up. The supported fix is to import the gateway's certificate
> into a truststore and point the client at that, so exactly one unusual
> certificate is trusted rather than all of them. Where a local run genuinely
> needs it, keep it local: never in a component that gets deployed, and never
> in the reusable skeleton this section describes.

**Coerce values to the types the platform expects — flattening is not just
renaming.** The platform/form mappings expect real types, and backends rarely
match: a `"Yes"`/`"No"` flag must become a boolean (`"Yes".equalsIgnoreCase(v)`),
dates/masked IDs often need reformatting (there are shared helpers — `formatDate`,
`formatToDui`, etc. in `servicelist.xml`). Make the **error path agree on type
too**: if `status` is a boolean on success, the catch-exception-strategy's
`status` must also be boolean (`false`), not a string.

### 4. Register the flow — `mule-deploy.properties`
Append the filename to the comma-list (no spaces):
```
config.resources=...,verify-tin.xml,<name>.xml
```

### 5. Endpoint URL — every `properties-*.properties`
Add the URL to **all** of `properties-dev`, `-test`, `-live`, `-localhost`. Reuse
existing `user-ws`/`pwd-ws` for shared-credential backends.
```
verifyX.url=https://host:8243/services/SomeProxy
```

### 6. Service descriptor — `servicelist.json`
Add an entry so the platform/BPA bots can discover and map the service. `inputs`
match the query params; `outputs` match the flattened JSON keys the Java returns.
```json
{
  "id": "verify-x",
  "name": "Verify X",
  "description": "Verify X",
  "url": "/api/verifyX",
  "method": "GET",
  "inputs": [ {"id": "param", "name": "Param", "required": true} ],
  "outputs": [ {"id": "firstName", "name": "First Name"}, {"id": "status", "name": "status"} ]
}
```

## Verify & ship

- **JSON:** `python3 -m json.tool src/main/resources/servicelist.json >/dev/null` — a broken `servicelist.json` is easy to cause and breaks discovery.
- **Build:** there is usually **no local Maven/JRE** — builds run in Docker (see `Dockerfile`). **Do not fabricate or run `mvn clean package` locally** and claim it passed. Verify by code-review against the reference service (matching brace balance, identical structure) and let CI/Docker compile. Say plainly that you didn't compile locally.
- **Branch:** the repo enforces an **`eRegistrations branch naming`** ruleset — use `feature/<slug>` (also `fix/**`, `release/**`). `feat/<slug>` is **rejected** by the remote ("creations being restricted"). PRs target `develop`.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Forgot `mule-deploy.properties` | Flow silently never loads — always add it |
| Forgot `servicelist.json` | Endpoint works but platform can't see/map it |
| Updated only `properties-dev` | Add the URL to all four env property files |
| `feat/...` branch | Use `feature/...` — ruleset rejects the rest |
| Claimed `mvn`/local build passed | No local toolchain; build is Docker/CI only — don't pretend |
| Assumed SOAP because there's a `?wsdl` / a SOAP sibling | Probe with curl first (step 0b) — pass-through proxies often want JSON |
| Invented the SOAP operation name | Get it from the WSDL, or flag the assumption explicitly |
| Listener `path` includes `/api` | basePath `/api` is already on the shared listener config |
| Passed backend values through verbatim | Coerce to platform types ("Yes"→`true`, format dates/IDs); keep the error path's types consistent |
