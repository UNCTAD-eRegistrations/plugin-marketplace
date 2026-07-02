---
description: Open a reviewed GitOps PR to add an OFF-DOMAIN Keycloak issuer to the GTS trusted-issuers list (human approval required — never auto-merged)
argument-hint: [issuer-url]
effort: high
allowed-tools: Bash(curl *), Bash(git *), Bash(gh *), Bash(jq *), Bash(python3 *), Bash(mktemp *), Bash(sort *), Bash(grep *), Bash(awk *), Read, Write, mcp__Keycloak__kc_decode_token
---

# GTS Trust Off-Domain Issuer (human-reviewed)

Opens a GitOps PR to add an **off-domain** Keycloak issuer to the Global
Translation Service (GTS, default https://translations.eregistrations.org)
trust list so its manager tokens are accepted by the GTS write API.

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
that file at startup. This command only edits that file via a PR; it does not
restart or deploy anything.

Arguments: `$ARGUMENTS`

## Safety model — READ THIS

An off-domain issuer is a **new GLOBAL trust root**. Once trusted, GTS accepts
**any** `translation_manager` / `global_translator` token that issuer mints, to
write the **whole** global catalogue that feeds **every** country instance.

⚠️ **This command NEVER auto-merges.** A "proof-of-control" token (a valid
manager token from that issuer) only proves the requester controls *that*
realm — it does **not** prove the realm is a legitimate, sanctioned
eRegistrations deployment. An attacker who self-hosts a Keycloak passes every
automatable check (OIDC discovery, signature, role, audience) for their *own*
rogue issuer. Authenticity of a new global trust root **cannot be
self-attested**. So this command gathers evidence into the PR and **always
leaves it open** for a maintainer with infrastructure authority to verify,
**out of band**, that the issuer belongs to a real deployment — and to merge.

Constants:
- `GITOPS_REPO` = `~/PROJECTS/00-eRegistrations-Next/eregistrations`
  (origin `https://github.com/UNCTAD-eRegistrations/eregistrations`, default
  branch **`master`**).
- `TRUST_FILE` = `Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst`
  (relative to the GitOps repo root).
- `ONDOMAIN_RE` = `^https://[a-z0-9.-]+\.eregistrations\.org/(auth/)?realms/[A-Za-z0-9_-]+$`

> **Prerequisite (verify before relying on this):** the GTS deployment must
> actually read `TRUST_FILE` — i.e. `Conf-LIVE/compose/global/docker-stack.yml`
> must set `GTS_TRUSTED_ISSUERS_FILE` and mount the `.lst` into the
> translation-service container, on an image new enough to include the
> file-reader. Until that GitOps wiring exists, a merged entry here is a no-op.

## Instructions

### 1. Input — resolve the issuer URL

- Take the issuer from `$ARGUMENTS` (e.g.
  `https://login.gateway.nipc.gov.ng/realms/NG`).
- If none was given but the operator has a currently-rejected token, decode it
  with `kc_decode_token` and read its `iss` claim — that is the issuer.
- Normalise: strip any trailing slash. Derive:
  - `HOST` = the hostname (e.g. `login.gateway.nipc.gov.ng`)
  - `REALM` = the last path segment (e.g. `NG`)
  - `SLUG` = lowercased `<host-with-dots-as-dashes>-<realm>` for the branch name.
- Echo the parsed `ISSUER`, `HOST`, `REALM` back to the operator.

### 2. VALIDATE — confirm it is a real Keycloak realm

```bash
curl -fsS "${ISSUER}/.well-known/openid-configuration"
```

- Must return HTTP **200** with a JSON body whose `issuer` equals `${ISSUER}`
  exactly and which has a `jwks_uri`.
- On any failure (non-200, `issuer` mismatch, missing `jwks_uri`) → **abort
  clearly**, report what was returned, open no PR.

### 3. SKIP-IF-COVERED — don't trust what is already trusted

- If `${ISSUER}` matches `ONDOMAIN_RE` → report *"Already trusted by the
  on-domain regex — no entry needed."* and **exit (no PR)**.
- If `${ISSUER}` is already a line in `${TRUST_FILE}` (exact match after
  trimming) → report *"Already present."* and **exit (no PR)**.
- Otherwise continue.

### 4. EVIDENCE — gather proof-of-control (supporting, NOT a merge gate)

If the operator can provide a `translation_manager` / `global_translator`
access token **issued by `${ISSUER}`**, validate it and record the result for
the PR body. This is *evidence to help the human reviewer*, not authorization
to merge. If no token is offered, skip this and record `proof: not provided`.

Verify the token's **signature against the issuer's own realm key** (decoded
claims alone are worthless):

```bash
# best-effort; needs PyJWT in the runtime python. If unavailable, record
# "proof: not verified (tooling unavailable)" and let the reviewer verify.
PUBKEY=$(curl -fsS "${ISSUER}" | jq -r .public_key)   # realm root returns {public_key:...}
python3 - "$TOKEN" "$PUBKEY" "$ISSUER" <<'PY'
import sys, jwt
token, pubkey, iss = sys.argv[1:4]
pem = f"-----BEGIN PUBLIC KEY-----\n{pubkey}\n-----END PUBLIC KEY-----"
try:
    p = jwt.decode(token, pem, algorithms=["RS256", "RS512"],
                   audience=["account"], issuer=iss, leeway=30,
                   options={"verify_iat": False})
    roles = (p.get("realm_access") or {}).get("roles") or []
    has_role = bool({"translation_manager", "global_translator"} & set(roles))
    print("proof: PASS" if has_role else
          "proof: token valid but lacks translation_manager/global_translator")
except Exception as e:
    print(f"proof: FAIL ({e})")
PY
```

Record the one-line `proof:` result. It does **not** change the outcome —
the PR is opened either way and always left for human review.

### 5. EDIT — append the issuer in an isolated worktree (enforced diff-guard)

```bash
cd ~/PROJECTS/00-eRegistrations-Next/eregistrations
git fetch origin master --quiet
WT=$(mktemp -d)
git worktree add --quiet "$WT" -b "feature/gts-trust-${SLUG}" origin/master
cd "$WT"
F="Conf-LIVE/haproxy/elsalvador/translations-global-issuers.lst"
mkdir -p "$(dirname "$F")"
[ -f "$F" ] || printf '# GTS additional trusted issuers (off-domain). One issuer URL per line.\n# Read by the GTS app via GTS_TRUSTED_ISSUERS_FILE.\n' > "$F"
printf '%s\n' "$ISSUER" >> "$F"
{ grep -E '^#' "$F"; grep -vE '^#|^$' "$F" | sort -u; } > "$F.tmp" && mv "$F.tmp" "$F"

# HARD diff-guard — exit non-zero (do not push) if not an addition-only single-file change:
git add -A
[ "$(git diff --cached --name-only | wc -l | tr -d ' ')" = "1" ] || { echo "ABORT: diff touches more than one file"; git -C ~/PROJECTS/00-eRegistrations-Next/eregistrations worktree remove --force "$WT"; exit 1; }
if git diff --cached -U0 -- "$F" | grep -qE '^-[^-]'; then echo "ABORT: change is not addition-only"; git -C ~/PROJECTS/00-eRegistrations-Next/eregistrations worktree remove --force "$WT"; exit 1; fi
```

### 6. COMMIT + PUSH + OPEN PR (no merge)

```bash
git commit -m "chore(gts): trust issuer ${HOST} (${REALM})"
git push -u origin "feature/gts-trust-${SLUG}"
```

- Commit message: `chore(gts): trust issuer <host> (<realm>)`. **No AI / Claude
  / Anthropic / "Generated with" mentions** anywhere.
- Open the PR against `master` with the evidence in the body:

```bash
gh pr create --base master --head "feature/gts-trust-${SLUG}" \
  --title "chore(gts): trust off-domain issuer ${HOST} (${REALM})" \
  --body "$(cat <<EOF
Adds an **off-domain** Keycloak issuer to the GTS trusted-issuers list. This
is a NEW GLOBAL TRUST ROOT — a reviewer must confirm out-of-band that the
issuer belongs to a sanctioned eRegistrations deployment before merging.

- **Issuer:** \`${ISSUER}\`
- **Host / realm:** \`${HOST}\` / \`${REALM}\`
- **File:** \`${TRUST_FILE}\` (addition-only, sorted, deduped)

## Evidence
- OIDC discovery: 200, \`issuer\` matches, \`jwks_uri\` present
- Not covered by on-domain regex; not already in the file
- <the one-line proof: result from step 4>

## Reviewer checklist (REQUIRED before merge)
- [ ] Confirmed out-of-band that \`${HOST}\` is a legitimate eRegistrations
      instance (not an attacker-controlled Keycloak).
- [ ] \`GTS_TRUSTED_ISSUERS_FILE\` env + \`.lst\` mount exist in the global
      docker-stack on a file-reader image (else this entry is a no-op).

Trust takes effect after the GitOps sync / GTS redeploy.
EOF
)"
```

- Capture and **print the PR URL**.

### 7. HUMAN REVIEW — always; never auto-merge

- **Do NOT merge.** Tell the operator clearly:
  *"PR opened for human review. An off-domain issuer is a new global trust
  root; a maintainer with infrastructure authority must verify the issuer is a
  sanctioned deployment (and that GTS_TRUSTED_ISSUERS_FILE is wired) before
  merging. The merge alone does not make tokens accepted until the GTS
  redeploys."*
- Print the PR URL and the `proof:` result so the reviewer has the evidence.

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

- **On-domain issuers never need this** — trusted by regex; exits in step 3.
- Editing the file is necessary but **not sufficient** until the GitOps
  pipeline syncs and the GTS service redeploys with the new
  `GTS_TRUSTED_ISSUERS_FILE`.
- Never bumps plugin versions (that goes through the MCP release flow).
- If the diff-guard trips, treat it as a signal something is off and stop.
