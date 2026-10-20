# Private application ingress

Lara hosts shared infrastructure, private AI services and independent applications.
Do not replace the host-wide root response when adding an application. Ingress is
owned here; application releases/data remain in their own repository/deployment.

## Registry

| Private HTTPS entry | Owner/upstream | State |
| --- | --- | --- |
| `https://lara.taila21247.ts.net/` (443) | Existing Caddy host response | Preserve unchanged |
| `https://lara.taila21247.ts.net:8443` | Notey / `notey-web:4000` on `lara-proxy` | Prepared; rollout and device evidence pending |

Publish both ports only on the verified Tailscale IPv4 `100.89.181.91`. Do not
publish Notey's web/database ports separately. Future applications receive their
own documented port/route without assuming that Notey owns the host. Per-app DNS
or path-prefix routing would require another reviewed decision.

The existing hostname certificate is used for both ports. Caddy's reverse proxy
handles WebSocket upgrades and forwarded scheme headers, required by LiveView.
Shared AI endpoints remain private on their existing networks, with no host port
or new ingress. Remote AI access is a separate authenticated integration design.

Official configuration references checked on 2026-10-20:
[Caddy addresses](https://caddyserver.com/docs/caddyfile/concepts#addresses) and
[reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

## Manual rollout after user merge

This is the infrastructure companion to JuliaMathias/notey#1, tracked here in
issue #11. No service is changed just by merging this file. Never switch or reset
an unrelated active infrastructure worktree to deploy it.

1. Verify the merged ingress SHA, current Tailscale address/hostname, certificates,
   available port 8443 and existing route response. Record running shared-service
   health and published ports. Record the prior Caddyfile/Compose revision.
2. Deploy the tested Notey image using its repository's `deploy/apply.sh`; expect
   healthy `notey-web` and dedicated PostgreSQL. The application must join the
   existing `lara-proxy` network. No AI workload or host package change is needed.
3. From the reviewed infrastructure deployment directory, validate before reload:

   ```sh
   docker compose -f caddy/compose.yaml config --quiet
   docker compose -f caddy/compose.yaml run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   docker compose -f caddy/compose.yaml up -d caddy
   ```

   Keep the existing certificate directory and named Caddy volumes. If applying
   from a clean release directory, configure the existing certificate bind mount
   explicitly; never copy certificates into Git or create empty replacement certs.
   The port mapping change needs container recreation, not only `caddy reload`.
   This briefly reconnects existing Caddy connections; do it only for this reviewed
   ingress update and record the outcome.
4. Verify the original 443 response is byte-for-byte unchanged. Verify Notey's
   `/health`, root, static assets and a real LiveView save/reload through 8443.
   In the laptop's browser inspect a successful `/live/websocket` 101 upgrade.
   On the phone disable home Wi-Fi, keep Tailscale on, repeat over cellular.
5. Inspect Docker host mappings: only Tailscale-address 443/8443 ingress; Notey
   database/web and existing AI have no newly published ports. Confirm existing
   transcription service remains healthy. Record source/image identities,
   URL/device/browser/connectivity and passed/failed/pending evidence.
6. For a routing failure, restore the prior recorded Caddyfile and Compose config,
   validate and recreate only Caddy. Preserve app/database state, certificates,
   networks and existing AI. Do not remove volumes or change firewall rules.

## Validation limits and plan

Configuration validation can establish that Caddy accepts this configuration; it
cannot establish a browser WebSocket, phone reachability or application readiness.
No live routing switch has been performed in this PR. N01 stays open until its
actual deployment/restart/device checks pass. N20 later verifies the access boundary
for real private source/result/export routes; N22 owns automatic updates/backups.
No further shared infrastructure change is required for the empty foundation.
