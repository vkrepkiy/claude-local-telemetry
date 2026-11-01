# The shared infrastructure record

Lives at `~/.claude/work/.mcp-infra.md`. One per machine/account, **not** one
per server, and **not** per repo — it describes the Cloudflare account, and the
servers it covers live in different repos. A repo-local
`.claude/work/.mcp-infra.md` overrides it, for the case of a second account.

It is what makes the second server cheap.

Written by the first server's build phase. Read by every phase of every server
after that, before anything is decided.

## Why it exists

Cloudflare already supports the shape you want: **one tunnel carries many
hostnames** through ingress rules, and **each hostname gets its own Access
application with its own AUD tag**. Same tunnel, same zone, same JWKS, same
team domain — new auth per server. The AUD tag *is* the per-server knob.

Without a record, every run re-derives the team domain, the tunnel id, the
ingress file path and the supervision style from scratch, and gets one of them
subtly wrong.

## Format

Plain markdown, key-value. Keep it short enough to paste into a subagent prompt.

```markdown
# MCP infrastructure

base_domain:   example.com
zone_id:       <cloudflare zone id>
team_domain:   <team>.cloudflareaccess.com
jwks_url:      https://<team>.cloudflareaccess.com/cdn-cgi/access/certs
tunnel_name:   <name>
tunnel_id:     <uuid>
ingress_config: /path/to/config.yml       # or "dashboard-managed"
supervision:   quadlet | systemd --user | compose
tunnel_unit:   <unit or container name>
identities:    someone@example.com        # the allow-list, verbatim
login_method:  <the one IdP the policy permits>
alert_channel: <where tunnel failure notifies>
backup:        <off-box location, and the date it was last restored>

## Served

| hostname | path | AUD tag | mode | since |
| --- | --- | --- | --- | --- |
| vault.example.com | /mcp | a1b2… | read-only | 2026-09-01 |
```

`identities` and `login_method` are recorded because a second server's policy
should match the first unless the user says otherwise — a drifting allow-list
across apps is how one server ends up quietly wider than the rest.

No secrets in here. The zone id and tunnel id are not secrets; a tunnel token
is. If a value would be dangerous in a work dir, record where it lives instead
of the value.

## First server: write it

At the end of the build phase, after the tunnel is up and the first Access app
exists. Every field above, filled. An unfilled field costs the next server a
rediscovery.

## Second server onward: read it, then append

The build phase collapses to:

1. Hostname is `<name>.<base_domain>`. Confirm it is free.
2. **Ingress rule** for that hostname on `tunnel_id`, pointing at the new
   origin's `host:port`. Same tunnel, same daemon — no new tunnel, no new
   supervision. Reload, do not recreate.
3. **DNS** — `CNAME <name> → <tunnel_id>.cfargotunnel.com`, proxied.
4. **New Access application** on the hostname. Managed OAuth on. Policy copied
   from `identities` + `login_method`. Redirect URIs to the vendor's domains.
   Same TTLs as the existing apps.
5. **Copy the new AUD tag** into the new origin's config, alongside
   `team_domain` and `jwks_url` taken from this record. The middleware code is
   the same; only the AUD differs.
6. MFA after the connector flow proves out, as always.

Then append one row to **Served** and update `backup` if the new server's state
needs its own coverage — it usually does, and that is the field most likely to
be forgotten.

## What does not belong here

Per-server decisions — the read-only/read-write call, the tool inventory, the
verification output. Those stay in the server's own `task.md` and notes. This
file answers "what is already deployed", nothing else.
