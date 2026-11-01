# Verification commands

Phase 5, run inside the verify subagent. Paste the raw output **into the phase
note**, not into the main thread — that thread gets the pass/fail count and the
failures only.

Substitute `$HOST` (public hostname), `$PATH_` (MCP path, e.g. `/mcp`),
`$ORIGIN` (host:port the server binds to).

## 1. Unauthenticated request is challenged

```bash
curl -si -X POST "https://$HOST$PATH_" \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | head -20
```

Expect `HTTP/2 401` and a `www-authenticate: Bearer` challenge. A `302` means
Managed OAuth is off or the request is hitting a browser-only Access flow;
MCP clients cannot use it. Do not investigate the origin until this is fixed.

## 2. Discovery metadata serves

```bash
curl -s "https://$HOST/.well-known/oauth-authorization-server" | jq
curl -s "https://$HOST/.well-known/oauth-protected-resource$PATH_" | jq
```

Both must return JSON. The first must carry a `registration_endpoint` (dynamic
client registration) and list `S256` in `code_challenge_methods_supported`.
Missing DCR means the user has to hand-paste a client id and secret.

## 3. The origin rejects what skips the proxy

From the host itself, bypassing the tunnel. Pass the public Host header if the
MCP transport has an allowed-hosts list; otherwise its own DNS-rebinding guard
will reject the request before the origin middleware is reached:

```bash
curl -si -X POST "http://$ORIGIN$PATH_" \
  -H "Host: $HOST" -d '{}' | head -5                           # expect 403
```

Then a forged token:

```bash
curl -si -X POST "http://$ORIGIN$PATH_" \
  -H "Host: $HOST" \
  -H "Cf-Access-Jwt-Assertion: $(printf 'a.b.c')" -d '{}' | head -5   # expect 403
```

Both `403`. A `200` here means the tunnel is the only boundary, and the origin
is reachable by anything else that lands on that network.

## 4. Health endpoint is exempt and boring

```bash
curl -s -H "Host: $HOST" "http://$ORIGIN/healthz" | jq
```

Returns counters. If it returns config, secrets, or content, cut it back.

## 5. TLS validates from outside

From a network that is not the host's:

```bash
curl -sI "https://$HOST$PATH_" >/dev/null && echo "tls ok"
```

## 6. The real client connects

Not optional. Add the connector in the app using **exactly**
`https://$HOST$PATH_`, complete the consent flow, and confirm the tool list
renders. The bare host is not an MCP endpoint and commonly produces “does not
implement OAuth”. Everything above can pass while this fails.

## 7. A write lands in the audit log

Call one write-family tool from the client, then:

```bash
# adjust to the actual log sink
journalctl --user -u <unit> -n 50 | grep audit
```

The line must carry the tool name, the target, the outcome, and **the caller's
identity from the JWT**. Without the caller it is a debug log, not an audit log.

## 8. Restore drill

On a scratch machine:

```bash
git clone <backup-origin> restore-test && cd restore-test && <build command>
```

Confirm it reproduces the server before relying on the backup. Do this once,
before exposure — not after the first incident.
