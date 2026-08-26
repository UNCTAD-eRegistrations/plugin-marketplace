# Access — names only

**This file lives in a public GitHub repository.** Everything below is a
*name*: what a credential is called, and which VPN profile to select. No
addresses, no usernames, no values, and no statement about which host is safe.

Where the real things live:

| Class | Lives in | Never in |
| --- | --- | --- |
| Addresses — servers, SSH targets, VPN endpoints | `~/.ereg/fleet.local.json` (`hosts.<host>.address`) | this repository |
| Security posture — which hosts are sound | Monitor's `posture` field, or `hosts.<host>.posture` in the overlay | this repository |
| Credential values | your credential manager, referenced by name | this repository, any commit, any commit message, any issue |
| Credential and profile **names** | here | — |

`~/.ereg/fleet.local.json` is created by the operator and committed nowhere. See
`resolution.md` for its schema.

## VPN profiles

The router's lane probe needs to know **which profile to bring up**, not where
it connects. That name is recorded per host in the overlay:

```json
"hosts": { "<host-name>": { "vpn": "<vpn-profile-name>" } }
```

Use the profile name exactly as it appears in your VPN client's profile list.
A host with no `vpn` entry is one the router cannot bring a tunnel up for; it
will detect the `build` lane and hand off rather than half-run.

Instances behind the same tunnel share a profile name — record it once, on the
host entry, not on each instance.

## Credentials this work touches

Named by role. What each is called in your credential manager is your naming
choice; keep it stable, because that name is the only handle that may be written
down or spoken in a request.

| Role | Used for | Notes |
| --- | --- | --- |
| VPN profile credential | bringing up the tunnel to a host | one per profile |
| SSH key | reaching a host once the tunnel is up | prefer a key over anything typed |
| Git hosting credential | cloning and pushing the eRegulations repositories | |
| Container registry credential | pulling and pushing the `unctad/` images | |
| Database administrator credential | the SQL Server instance behind a deployment | per instance, never shared across instances |
| Mail-delivery API credential | outbound mail from a deployed instance | |
| Currency-rate API credential | the exchange-rate integration | |
| Monitor account | the live fleet path in `resolution.md` | `viewer` role is sufficient — read endpoints require authentication but no elevated role |

## Two rules that are not about tidiness

**Never retry a rejected Monitor login.** Monitor locks an account after five
failed attempts for fifteen minutes, and it has no service accounts today, so
a retry loop can lock a human out of the fleet dashboard mid-incident. One
rejection surfaces to the operator immediately, and the router stops. Ask; do
not iterate.

**A credential in a request is a credential to rotate.** If a value ever
appears in a prompt, a commit, a ticket or a chat, treat it as disclosed. Name
it and reference it; never paste it. A pushed commit cannot be un-published.

## Known, out of scope, worth doing

A separate operations document holds working credential values in plain text,
several tied to a personal rather than an institutional account, and some of
them open hosts whose posture is questionable. Rotating those and moving them
into a shared credential manager is real work with real value. It is deliberately
**not** folded into this plugin: mixing a security cleanup into a tooling change
makes both harder to review, and it is tracked separately.
