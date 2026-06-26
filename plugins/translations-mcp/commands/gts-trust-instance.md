---
description: Self-onboard an OFF-DOMAIN Keycloak issuer to the GTS trusted-issuers list, auto-merging the GitOps PR only when proof-of-control is shown
argument-hint: [issuer-url]
effort: high
allowed-tools: Bash(curl *), Bash(git *), Bash(gh *), Bash(jq *), Bash(openssl *), Bash(mktemp *), Bash(rm *), Bash(sort *), Bash(grep *), Bash(awk *), Bash(python3 *), Read, Write, mcp__Keycloak__kc_decode_token, mcp__Keycloak__kc_validate_token
---

# GTS Trust Off-Domain Issuer

Onboards an **off-domain** Keycloak issuer to the Global Translation Service
(GTS, default https://translations.eregistrations.org) trust list so its
manager tokens are accepted by the GTS write API.

GTS auto-trusts **on-domain** realms by regex
(`^https://[a-z0-9.-]+\.eregistrations\.org/(auth/)?realms/[A-Za-z0-9_-]+$`).
**Off-domain** issuers — hosts that do NOT end in `.eregistrations.org`, e.g.
`login.gateway.nipc.gov.ng`, `login.uganda.easyaccounts.org`,
`login.businessregistrations.gov.ls`, `login.easybusiness.gov.gm`,
`login.invest.go.ke`, `login.monentreprise.ml`,
`login.guichet.investbenin.bj`, `login.testeregistrations.rik.ee` — are not
matched by that regex and must be listed explicitly.

This command **pairs with the GTS `GTS_TRUSTED_ISSUERS_FILE` mechanism**: the
GTS app reads a newline-delimited list of additional trusted issuer URLs from
that file at startup (mounted from the GitOps repo at
`Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst`). Adding a line
there — once the change syncs and the GTS redeploys — is what extends trust.
This command only edits that file via a PR; **it does not restart anything**.

Arguments: `$ARGUMENTS`

## Safety model (read before running)

The auto-merge gate is **proof-of-control**: the operator must present a valid
`translation_manager` / `global_translator` access token **issued by the very
issuer they want trusted**. Verifying that token's signature against that
issuer's own realm key proves they control a real manager account on that
instance — so trusting the issuer cannot be abused to inject an attacker's
realm. Without a passing proof-of-control, this command still opens the PR but
**leaves it for human review** rather than auto-merging.

Constants used below:
- `GITOPS_REPO` = `~/PROJECTS/00-eRegistrations-Next/eregistrations`
  (origin `https://github.com/UNCTAD-eRegistrations/eregistrations`, default
  branch **`master`**).
- `TRUST_FILE` = `Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst`
  (relative to the GitOps repo root).
- `ONDOMAIN_RE` = `^https://[a-z0-9.-]+\.eregistrations\.org/(auth/)?realms/[A-Za-z0-9_-]+$`

## Instructions

### 1. Input — resolve the issuer URL

- Take the issuer from `$ARGUMENTS` (e.g.
  `https://login.gateway.nipc.gov.ng/realms/NG`).
- If none was given but the operator has a currently-rejected token, decode it
  with `kc_decode_token` and read its `iss` claim — that is the issuer.
- Normalise: strip any trailing slash. Derive:
  - `HOST` = the hostname (e.g. `login.gateway.nipc.gov.ng`)
  - `REALM` = the last path segment (e.g. `NG`)
  - `SLUG` = lowercased `<host-without-dots-as-dashes>-<realm>` for the branch
    name (e.g. `login-gateway-nipc-gov-ng-ng`).
- Echo the parsed `ISSUER`, `HOST`, `REALM` back to the operator.

### 2. VALIDATE — confirm it is a real Keycloak realm

```bash
curl -fsS "${ISSUER}/.well-known/openid-configuration"
```

- Must return HTTP **200** with a JSON body.
- The body's `issuer` field MUST equal `${ISSUER}` exactly, and a `jwks_uri`
  field MUST be present.
- If the curl fails, the status is not 200, `issuer` mismatches, or `jwks_uri`
  is missing → **abort clearly**: report what was returned and stop. Do not
  open a PR.

### 3. SKIP-IF-COVERED — don't trust what is already trusted

- If `${ISSUER}` matches `ONDOMAIN_RE` → report
  *"Already trusted by the on-domain regex — no entry needed."* and **exit
  (no PR)**.
- If `${ISSUER}` is already a line in `${TRUST_FILE}` (exact match, after
  trimming whitespace) → report *"Already present in the trusted-issuers
  file."* and **exit (no PR)**.
- Otherwise continue.

### 4. PROOF-OF-CONTROL — the auto-merge gate (DECISION B)

Ask the operator for a **valid access token issued by `${ISSUER}`** belonging
to a `translation_manager` or `global_translator` account on that instance.

Verify ALL of the following; record each as pass/fail for the PR body:

1. **Issuer match** — decode the token (`kc_decode_token`) and confirm the
   `iss` claim equals `${ISSUER}`. A token from any other issuer fails the
   gate.
2. **Signature valid** — fetch the realm's signing material and verify the
   token signature:
   - `PUBKEY=$(curl -fsS "${ISSUER}" | jq -r .public_key)` gives the realm
     RSA public key (the Keycloak realm root endpoint returns
     `{ "realm": ..., "public_key": ... }`); or fetch the JWKS at `jwks_uri`
     and match the token's `kid`.
   - Validate the RS256 signature against that key (e.g. via
     `kc_validate_token`, or reconstruct the PEM
     `-----BEGIN PUBLIC KEY-----\n${PUBKEY}\n-----END PUBLIC KEY-----` and
     verify with `python3`/`openssl`). A token must NOT be accepted on its
     decoded claims alone — the **signature against the issuer's own key** is
     the whole point of the proof.
   - The token must be unexpired (`exp` in the future).
3. **Manager role** — `realm_access.roles` contains `translation_manager`
   **or** `global_translator`.
4. **Audience** — `aud` contains `account`.

- If **all four pass** → `PROOF=PASS` (eligible for auto-merge).
- If any fail → `PROOF=FAIL`. Continue to open the PR, but it will be left
  open for human review (step 7). Tell the operator exactly which check failed.

### 5. EDIT — append the issuer in an isolated worktree

Work in a throwaway worktree off the GitOps repo's `origin/master` so the
operator's checkout is untouched:

```bash
cd ~/PROJECTS/00-eRegistrations-Next/eregistrations
git fetch origin master --quiet
WT=$(mktemp -d)
git worktree add --quiet "$WT" -b "feature/gts-trust-${SLUG}" origin/master
cd "$WT"
```

- Ensure the file exists (create with a header comment if missing):
  `Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst`.
- Append `${ISSUER}` as a new line, then **sort + dedupe** the data lines
  (preserve any leading `#` comment header):

```bash
F="Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst"
mkdir -p "$(dirname "$F")"
[ -f "$F" ] || printf '# GTS additional trusted issuers (off-domain). One issuer URL per line.\n# Read by the GTS app via GTS_TRUSTED_ISSUERS_FILE.\n' > "$F"
printf '%s\n' "$ISSUER" >> "$F"
# sort/dedupe data lines, keep comment header on top
{ grep -E '^#' "$F"; grep -vE '^#|^$' "$F" | sort -u; } > "$F.tmp" && mv "$F.tmp" "$F"
```

- **Diff-guard** — before committing, verify the change is **addition-only and
  a single file**:

```bash
git diff --stat        # must show exactly 1 file changed
git diff -- "$F"       # every changed line must be an addition (leading '+')
```

  If the diff touches more than `${TRUST_FILE}`, or removes/modifies any
  existing line, **abort**, remove the worktree (step 8), and report — do not
  push.

### 6. COMMIT + PUSH + PR

```bash
git add "$F"
git commit -m "chore(gts): trust issuer ${HOST} (${REALM})"
git push -u origin "feature/gts-trust-${SLUG}"
```

- Commit message: `chore(gts): trust issuer <host> (<realm>)`. **No AI / Claude
  / Anthropic / "Generated with" mentions** anywhere in the subject, body, or
  PR description.
- Open the PR against `master` with the validation evidence in the body:

```bash
gh pr create --base master --head "feature/gts-trust-${SLUG}" \
  --title "chore(gts): trust off-domain issuer ${HOST} (${REALM})" \
  --body "$(cat <<EOF
Adds off-domain Keycloak issuer to the GTS trusted-issuers list.

- **Issuer:** \`${ISSUER}\`
- **Host / realm:** \`${HOST}\` / \`${REALM}\`
- **File:** \`${TRUST_FILE}\` (addition-only, sorted, deduped)

## Validation evidence
- OIDC discovery: 200, \`issuer\` matches, \`jwks_uri\` present
- Not covered by on-domain regex; not already in the file
- Proof-of-control: ${PROOF}
  - iss == issuer: <pass/fail>
  - signature valid against realm key: <pass/fail>
  - realm_access.roles has translation_manager/global_translator: <pass/fail>
  - aud contains account: <pass/fail>

Trust takes effect after the GitOps sync / GTS redeploy reads
\`GTS_TRUSTED_ISSUERS_FILE\`.
EOF
)"
```

- Capture the PR URL from the `gh pr create` output.

### 7. AUTO-MERGE — only when fully proven

- Auto-merge **only if** `PROOF=PASS` **AND** OIDC-valid (step 2 passed)
  **AND** the diff was addition-only single-file (step 5) **AND** the issuer
  was not a duplicate (step 3):

```bash
gh pr merge --squash --delete-branch "<PR_URL>"
```

- If **any** of those conditions is false → **do NOT merge**. Leave the PR
  open and tell the operator precisely why (e.g. *"proof-of-control failed:
  token signature did not verify against the realm key — left PR open for human
  review"*).
- **Always print the PR URL**, merged or not.
- Remind the operator: trust **takes effect only after** the GitOps sync /
  redeploy reloads the GTS with the updated `GTS_TRUSTED_ISSUERS_FILE` — the
  merge alone does not make tokens accepted instantly.

### 8. CLEANUP — remove the worktree

```bash
cd ~/PROJECTS/00-eRegistrations-Next/eregistrations
git worktree remove --force "$WT"
git worktree prune
```

## Usage

```
/translations-mcp:gts-trust-instance https://login.gateway.nipc.gov.ng/realms/NG
/translations-mcp:gts-trust-instance            # derives issuer from a rejected token
```

## Notes

- **On-domain issuers never need this** — they are trusted by regex; the
  command exits early in step 3.
- The trusted-issuers file is the on-disk source the GTS app reads via
  `GTS_TRUSTED_ISSUERS_FILE`; editing it is necessary but **not sufficient**
  until the GitOps pipeline syncs and the GTS service redeploys.
- This command never bumps plugin versions — version bumps go through the MCP
  release flow, not here.
- If the GitOps diff-guard trips (more than one file, or a non-addition),
  treat it as a signal that something is off and stop; never force the push.
