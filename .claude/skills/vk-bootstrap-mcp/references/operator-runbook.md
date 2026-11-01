# Operator runbook: public Cloudflare Access MCP

Use this only in the build phase. It turns the infrastructure decisions already
made in `task.md` into exact actions. Substitute the deployment manifest values
instead of asking again for values that are already known.

## Start with a deployment manifest

Before changing anything, read the task and infra record, then state the known
values in one compact block:

```text
Origin:       <host or CT>, loopback HTTP <port>
Public URL:   https://<hostname>/mcp
Connector:    <existing name> | new dashboard-managed tunnel
Access app:   new self-hosted app, policy copied from <sibling or none>
Identity:     <allow-list and login method>
Backup:       <off-box location>, restore check <date or pending>
```

Discover missing host addresses, CT IDs, public hostname conflicts, and
connector reachability with read-only checks. Do not guess from an old IP or
ask the user to rediscover facts the agent can inspect.

## Choose or create the tunnel

Reuse a tunnel only when its current connector can reach the new origin. A
connector inside Bazzite that routes to `127.0.0.1:3000` cannot route to a
Proxmox CT merely because both devices share a LAN. If the MCP must survive
that host sleeping, create a dedicated connector in the always-on CT.

For a dashboard-managed tunnel, give this exact handoff card if the agent has
no dashboard control:

1. Open **Cloudflare Zero Trust** → **Networks** → **Tunnels & Mesh**.
2. Click **Create a tunnel**, choose **Cloudflared**, name it `<name>` and
   create it.
3. On the connector-install page, copy the one displayed install command and
   run it **on the always-on origin/CT only**. Do not paste its token into chat,
   a task note, a git repository, or a shell command that will be logged.
4. Return to the tunnel page and wait until the connector is **Healthy**.
5. Open its **Public Hostname** tab → **Add a public hostname**. Enter
   subdomain `<name>`, domain `<base-domain>`, service type **HTTP**, URL
   `http://127.0.0.1:<port>`, then click **Save hostname**.

Creating a Public Hostname creates the proxied tunnel CNAME automatically.
Check that DNS resolves before adding a separate CNAME. Add a manual record
only if the tunnel page saved successfully and the expected record is absent.

For a token supplied through an approved secure mechanism, store it in a
root-only file and run a dedicated system service with restart enabled. Do not
put it in a unit `ExecStart`, environment dump, journal, source tree, or the
infra record. If a token was pasted into chat or emitted to logs, rotate it.

## Create the Access application

The Access app protects the **whole hostname**. Do not enter `/mcp` as its
path unless a deliberate path-scoped policy is required. The MCP client's URL
still includes `/mcp`.

1. In **Cloudflare Zero Trust**, open **Access controls** → **Applications** →
   **Create new application**.
2. Choose **Self-hosted and private**, select **Public DNS**, then click
   **Continue with Self-hosted and private**.
3. Set application name `<name>` and domain `<hostname>`; leave the path empty.
4. In policies, attach the existing sibling policy only when it has the intended
   email allow-list and login method. Otherwise create an **Allow** policy with
   precisely those identities and that login method. Save the app.
5. Reopen the app → **Additional settings** → **OAuth** → turn **Managed
   OAuth** on → **Save**.
6. In **Additional settings** → **AUD tag**, copy the new app's tag into the
   origin's `CF_ACCESS_AUD`. Never reuse a sibling application's AUD.

Tell the user exactly one result to return: either “Managed OAuth is on and
the displayed AUD tag is …” or a screenshot of the field that blocks them.
Do not ask them to “configure Access”.

## Origin details that repeatedly fail in production

- Bind the process to loopback, but configure the MCP transport with the public
  host as its explicit allowed host and allowed origin. A localhost-default
  transport otherwise rejects the tunnel's public Host header before the route
  executes.
- Keep `/healthz` path-exempt, not loopback-exempt. A tunnel also reaches the
  origin over loopback.
- If a structured target list is held in a systemd `EnvironmentFile`, do not
  put raw JSON quotes in it. Use a base64-encoded JSON variable and decode it
  at process startup, or use a dedicated config file with strict permissions.
- Create and restore-test an off-box backup before enabling the public service;
  refresh it after the last deployed code/configuration change.

## Failure map before asking the user anything

| Observation | Cause to test first | Exact next action |
| --- | --- | --- |
| Hostname does not resolve | Public Hostname was not saved or tunnel DNS is absent | Reopen the chosen tunnel → Public Hostname; verify `<hostname>` and service URL, then inspect the zone DNS record. |
| `/mcp` returns 302 | Managed OAuth is off | Access controls → Applications → `<name>` → Additional settings → OAuth → enable Managed OAuth → Save. |
| Discovery routes return 302 or HTML | Same: edge is using browser Access instead of OAuth | Enable Managed OAuth, then recheck both well-known endpoints for JSON. |
| Client says “does not implement OAuth” | Client was given bare `https://<hostname>` | Replace it with `https://<hostname>/mcp`; then check discovery endpoints. |
| Service is active but no port listens | Startup config parsing failed | Inspect the service journal; validate JSON/base64 configuration before changing Cloudflare. |
| Local health is 403 | Transport host allow-list rejected a loopback Host header | Retry with `Host: <hostname>`; configure explicit allowed hosts/origins, never weaken the origin auth. |
| A token appeared in chat/logs | Secret is exposed | Rotate the tunnel token in Cloudflare and replace the root-only token file. |

## Human handoff format

Use this format whenever a browser click, login, MFA, or token is the only
thing the agent cannot perform. Ask for no extra decision if the manifest has
the value.

```text
Do this now in Cloudflare:
1. <exact navigation>
2. Click <control>; enter <value>.
3. Click <save control>.
Expected: <single visual/result check>.
Reply only with: <one value, status, or screenshot needed next>.
```

Resume immediately from that result. Never send a generic “configure the
tunnel” instruction or a menu of unranked alternatives.
