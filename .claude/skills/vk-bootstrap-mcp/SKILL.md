---
name: vk-bootstrap-mcp
description: Put an MCP server on the public internet behind Cloudflare Access — authenticated, tunnelled, and proven with a real client. Reuses the tunnel and zone already deployed, so a second server is a hostname and an Access app, not a rebuild. Use when the user says "expose my MCP server", "remote MCP connector", "MCP over HTTPS", "add auth to my MCP server", "tunnel my MCP server", or names a server to put online.
argument-hint: '[name] (becomes <name>.<base-domain>) to start or resume'
disable-model-invocation: true
---

Get an MCP server that works on localhost to the point where a vendor app connects to it over the public internet, authenticated, with every destructive tool behind that auth.

The user must never be left with an instruction such as “configure the tunnel”
or “set up Access”. When a human action is genuinely required, give one
**handoff card**: the exact console page, controls, values, save action, and
the one observable result to report. Read
[`references/operator-runbook.md`](references/operator-runbook.md) during the
build phase and use its failure map before asking any follow-up question.

This is an ordered gate sequence. **Nothing becomes publicly reachable before the `built` gate passes.** Each invocation advances exactly one phase and stops. Re-invoke to continue.

## 0. The workspace and the phase

Input for this run: $ARGUMENTS

Everything this skill knows between invocations lives in plain files, so a
run can stop after any phase and resume in another session:

- **Work dir:** `.claude/work/mcp-<name>/` in the MCP server's repository
  (outside any repository: `~/.claude/work/mcp-<name>/`). It holds `task.md`
  and `notes/`.
- **Infra record:** `~/.claude/work/.mcp-infra.md`, overridden by a
  repo-local `.claude/work/.mcp-infra.md` — see
  [`references/infra-record.md`](references/infra-record.md). Resolve it to
  an absolute path now; absent means this is the first server.
- **References:** the `references/` directory next to this file. Give
  subagents its absolute path — a subagent has no inherited working directory.

If the work dir exists, read its `task.md` and continue. Otherwise create it
with this `task.md`:

```
# Expose <name> MCP

status: discussing

## Context
name:      <name>
hostname:  <name>.<base-domain from the infra record, or ask>
server:    <path to the MCP server repo>
```

The `status:` line is the gate. Do the phase it names, then stop:

| status | phase | section |
| --- | --- | --- |
| `discussing` (fresh) | inventory | 1 |
| `inventoried` | exposure model | 2 |
| `modeled` | write story | 3 |
| `decided` | build | 4 |
| `built` | verify | 5 |
| `verified` | debt + doc | 6 |

Never run two phases in one invocation, and never skip forward because a phase "looks obvious". Tell the user which gate they are at and what it will cost to pass it. Do not re-ask a decision already present in the request, `task.md`, a prior note, or the infra record: copy it into Context and proceed to the next gate.

## Delegation — the rule for every phase

Each phase runs in **one subagent**, not in this thread. This thread holds the status line and the verdicts, nothing else — the inventory of forty tools, the build transcript, and the raw verification output all live in the work dir.

The phase's note is `<work_dir>/notes/NN-<phase>.md`, where `NN` is one more than the highest number already in `notes/` (two digits, starting at `01`). Spawn the phase as the **`vk-phase`** agent, overriding its model to `opus` for the exposure-model and verification phases — those decide what becomes reachable from the public internet. Then spawn with exactly this context, and no more:

> You are running the **<phase>** phase of an MCP public-exposure bootstrap.
>
> Read, in order: `<work_dir>/task.md` for the name, hostname and server path; `<infra_record>` for the infrastructure already deployed (absent = you are the first server); every note in `<work_dir>/notes/`; and `<references_dir>/<the file this phase names>`.
>
> Do the phase as specified below. Ground every claim in a file you opened or a command you ran — do not assert from what the server is said to do.
>
> Write your note to `<note_path>`, at most 40 lines, in this format:
>
> ```markdown
> **Verdict:** <the one thing this thread needs to know, one line>
>
> **Findings**
> - <max 6, one line each>
>
> **Blocks the next gate**
> - <anything unresolved, or "nothing">
> ```
>
> Return the Verdict line and nothing else.

Then set the `status:` line in `task.md` to the next status and report the verdict plus how to continue (`/vk-bootstrap-mcp <name>`). Do not paste the note back into this thread.

## 1. Inventory → `inventoried`

Reference: none. Reads the server's code.

- **Transport** — stdio or streamable HTTP. stdio cannot be exposed; it needs an HTTP transport first, and that is a code change, not a deploy step.
- **Bind address and port**, and whether anything but loopback reaches it today.
- **Every registered tool**, split read-family / write-family. Name the write tools explicitly (`write_*`, `delete_*`, `move_*`, anything that mutates). This list is the blast radius of getting auth wrong.
- **Whether a read-only mode already exists** as a config flag. If it does, it is a free fallback; if not, do not build one on spec.
- **Where state lives** and whether there is an off-box copy. Public write access with no restorable backup is not a risk to accept on the user's behalf — flag it.
- **How it is supervised** — systemd unit, container, Quadlet, bare process. The tunnel gets supervised the same way.

## 2. Exposure model → `modeled`

Reference: `references/cloudflare-access.md`.

The common wrong turn is reaching for a VPN mesh (Tailscale, WireGuard) because it feels safer. **Remote MCP connectors are called from the vendor's cloud, not from the phone** — the request never leaves the handset, so putting the phone on a private network does nothing. If the goal is "use it from the app", public HTTPS is the only path.

Confirm the goal with the user:

- **From the vendor app** → public HTTPS, continue.
- **From your own machines only, off-LAN** → a tailnet is correct and this skill is the wrong tool. Say so and stop.

Never propose Tailscale Funnel or `ngrok`-style tunnels as the endpoint: public exposure, none of the controls below.

Auth shape is settled, not re-derived: Cloudflare Access Managed OAuth is the authorization server; **the origin's whole auth job is verifying one JWT**. The reference names what was rejected and why — do not rebuild any of it. If the client UI is in doubt, spike it (a throwaway public endpoint with a hand-rolled `initialize`/`tools/list` handshake, added in the real client, deleted after) rather than trusting docs.

## 3. Write story → `decided`

Reference: none. Needs the inventory's write-family list.

Two honest options. Make the user pick; do not pick silently. Record the choice and its date in `task.md` — it gets re-litigated later.

- **Read-only public surface.** Flip the read-only flag, register no write tools. Removes the destructive risk, and removes "add things from anywhere" from the goal.
- **Full read/write.** Defensible only with all of these, as conditions:
  - Access policy scoped to specific identities, MFA on.
  - The origin independently validates the JWT. **The tunnel is not the boundary** — anything reaching the origin directly is rejected.
  - An audit log for write-family tools carrying caller identity, before exposure.
  - A durable off-box backup, so every destructive op has an undo.

## 4. Build → `built`

Reference: `references/cloudflare-access.md`, `references/operator-runbook.md`, plus `references/infra-record.md` for what to reuse and what to write back.

**Read the infra record first.** If it exists, steps 5 and 6 shrink to an ingress rule and a new Access app — the tunnel, zone, DNS and supervision are already there. If it does not, you are the first server: do all of it, then write the record.

Per-server, always:

1. **Pin the endpoint path.** Serve MCP at an explicit path (`/mcp`). Keep the old path registered if LAN clients depend on it. Check it does not collide with the `/.well-known/*` discovery routes served at the edge.
2. **DNS-rebinding protection.** Pass the public hostname to the transport's allowed-hosts option. An HTTP MCP transport with no host allow-list is attackable from any page the user visits.
3. **JWT middleware, ahead of the MCP route.** Fetch JWKS by the token's `kid` — never pin a single cert; Access rotates every ~6 weeks and the old key lives 7 more days. Verify `iss`, `aud` (**this application's AUD tag — the per-server knob**), expiry, and the identity claim against an allow-list. Reject with `403`.
   - Config **fails at startup** if the public surface is on without auth config or without an allowed-hosts list.
   - An empty identity allow-list is a startup error, not allow-all. Highest-value line in the build.
   - Test the failure paths: forged signature, wrong `aud`, wrong issuer, expired, identity not on the list.
4. **An auth-exempt health endpoint,** registered *before* the middleware, counters only — no server content, no config. Local monitoring has no JWT and will otherwise alert forever. Do **not** exempt loopback generally: the tunnel daemon also reaches the origin over loopback, so a loopback exemption waves through every tunneled request. Exempt the one path.

Infrastructure, **first server only** — afterwards read it from the record:

5. **The tunnel.** Decide reachability before reusing it: an existing connector may serve an origin only when it can reach that origin from its own network namespace. A connector on a sleeping PC pointed at `127.0.0.1` cannot serve a new Proxmox CT. In that case make a separate, dashboard-managed tunnel on the always-on target. Follow the exact UI and token-handling procedure in `operator-runbook.md`; never ask the user to paste a tunnel token into chat or a command transcript.

Per-server again:

6. **The Access application.** Self-hosted app on the hostname; a route in the selected tunnel plus the DNS record; policy = the identity allow-list AND a specific login method; Managed OAuth on; redirect URIs restricted to the vendor's domains; short access-token lifetime, bounded session grant. Copy a policy from a sibling app if its identities and login method are intended to match, but always create a distinct app and AUD tag. The dashboard sequence, including the fact that the Access app is host-wide while the client endpoint is `/mcp`, is in `operator-runbook.md`.
7. **MFA last.** Leave step-up MFA off until the connector flow is proven end to end, then turn it on. Debugging a token-refresh loop and a new MFA prompt at once is strictly worse than doing them in sequence.

Before finishing: update `.mcp-infra.md` per `references/infra-record.md` — at minimum append this server's hostname and AUD to the served list.

## 5. Verify → `verified`

Reference: `references/verification.md`. The subagent runs the commands and pastes the output **into its note**; this thread gets the pass/fail count and the failures only.

- Unauthenticated `POST` to the public URL returns `401` with a `WWW-Authenticate: Bearer` challenge.
- Both `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource/<path>` serve, advertising a registration endpoint and PKCE `S256`.
- A request that bypasses the proxy but reaches the origin directly gets `403`.
- A forged JWT gets `403`.
- TLS validates from a network outside the host.
- The real client completes the connector flow and lists tools.
- A write-family call appears in the audit log with the caller's identity.
- The backup has been restored once, on a scratch machine, and reproduces the server.

Anything unchecked is not done. Name the unchecked ones rather than declaring success.

## 6. Debt and doc → `documented`

Reference: `references/infra-record.md`.

List whichever remain open, each with the failure it prevents:

- **Alerting proven by a fire drill.** Alerting that has never fired is not alerting. Break something deliberately and confirm the message arrives without reading logs. If a failure has ever gone unnoticed for weeks, this outranks everything else here.
- **Rate limiting** at the edge.
- **Audit log durability** — container logs rotate; a JSONL file needs its own mount. And plumb the caller identity from the JWT down into the tool layer; an audit log without a caller is a debug log.
- **Key-rotation survival** — prove the origin survives an issuer key rotation without a restart. It will, if JWKS is fetched per `kid`.
- **Restore drill**, if not done in phase 5.

Then finish the record. Per-server decisions and their dates stay in `task.md`; anything the *next* server needs goes in `.mcp-infra.md`. The rejected-options section is what stops someone rebuilding an OAuth server in six months — it belongs in the reference, not in a note that ages out.
