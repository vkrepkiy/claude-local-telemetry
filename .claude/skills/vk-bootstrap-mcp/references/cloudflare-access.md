# Cloudflare Access as the MCP authorization server

Reference for Phase 2. Read before writing auth code. Another identity-aware
proxy with the same properties substitutes cleanly — the shape is what matters,
not the vendor.

## Why an IdP proxy and not your own OAuth server

An MCP client connecting to a remote server expects an OAuth 2.1 authorization
server sitting in front of it. Writing one means implementing discovery,
dynamic client registration, PKCE, authorize, token, refresh, and revocation,
then keeping them correct. Access already implements all of it:

- Returns `401` + `WWW-Authenticate` to non-browser clients instead of a `302`
  redirect. This is the property that makes it work at all — a browser-shaped
  redirect breaks every MCP client.
- Serves `/.well-known/oauth-authorization-server` (RFC 8414) and
  `/.well-known/oauth-protected-resource/<path>` (RFC 9728) at the edge.
- Supports **dynamic client registration**, so the client registers itself and
  there is no client secret to paste anywhere.
- Runs authorize / token / refresh, re-evaluating the Access policy on every
  refresh. Revoking a user takes effect within one token lifetime.
- Issues an **opaque** token to the client, resolves it at the edge, and
  forwards a **signed JWT** to the origin as `Cf-Access-Jwt-Assertion`.

Net effect: the origin is a plain resource server. Its entire auth job is
verifying one JWT.

## What the origin must verify

```
JWKS:  https://<team>.cloudflareaccess.com/cdn-cgi/access/certs
```

- Select the key by the token's **`kid`** against `public_certs`. Never cache
  `public_cert` as a fixed value — Access rotates every ~6 weeks and the old
  key stays valid only 7 more days. A pinned cert is a scheduled outage.
- `iss` — the team domain.
- `aud` — the application's AUD tag. Wrong-`aud` tokens are otherwise valid
  tokens from a *different* app on the same account. This is also the
  **per-server knob**: many servers share one tunnel, one zone and one JWKS,
  and are separated only by having their own Access app and therefore their own
  AUD. See `infra-record.md`.
- Expiry.
- The identity claim (`email`) against an allow-list held in config.

Reject with `403`, not `401` — a `401` from the origin invites the client to
retry the OAuth dance against a boundary that has already passed.

## Deliberately not used

Naming these prevents someone rebuilding them in six months.

- **`mcpAuthRouter`, `ProxyOAuthServerProvider`, `DemoInMemoryAuthProvider`,
  `requireBearerAuth`** (MCP SDK) — all for servers that *are* the
  authorization server. You are a resource server only.
- **Service tokens.** Machine identity: no user, no MFA. Wrong shape for a
  personal server holding personal data.
- **MCP server portals.** They do not protect the origin — a blocked user can
  still connect via the direct URL. They add a second OAuth hop, and they drop
  Independent MFA, purpose justification, and temporary authorization for
  portal-authorized servers. Their admin credential can expire silently with no
  notification, which is precisely the failure class the alerting phase exists
  to kill. Multiple servers do not need portals — one app per hostname on the
  shared tunnel is the supported path, and it is what `infra-record.md`
  describes.
- **AI Gateway.** Proxies LLM inference calls, not MCP. Unrelated.

## Application settings that matter

| Setting | Value | Why |
| --- | --- | --- |
| App type | Self-hosted | Managed OAuth requires it |
| Policy | Single email (or a small allow-list) AND one login method | The allow-list is the boundary |
| Managed OAuth | On | This is what makes it an AS |
| `allowed_uris` | The vendor's domains only (e.g. `https://claude.ai/*`, `https://claude.com/*`) | Stops a redirect to anywhere else |
| Access token TTL | ~15 minutes | Policy re-evaluated on refresh |
| Session grant | Weeks, not months | Bounds a stolen refresh token |
| Independent MFA | On — but *after* the first successful connection | See Phase 4.7 |

Every row is **per application**, so each MCP server gets its own. The tunnel,
the zone, the team domain and the JWKS endpoint are shared across all of them —
that split is what `infra-record.md` records.

Zero Trust's free tier covers 50 users; Managed OAuth has no documented plan
gate. A zone already on the account costs nothing extra to use, and additional
hostnames on an existing tunnel cost nothing either.

## Client-side reality check

Vendor docs have listed OAuth, static request headers (beta), and no-auth as
options, while the shipped connector dialog offered only Name, Remote MCP
server URL, and optional OAuth Client ID/Secret — **no field for a static
header of any kind**. Bearer-token plans die here. Re-run the Phase 2a spike
rather than trusting either the docs or this file; the UI changes.
