# Home Server Infrastructure

Infrastructure configuration for a personal home server running
Ubuntu Linux, Docker, and GPU-accelerated AI services.

## Architecture

- **Ubuntu:** Host operating system
- **Docker Compose:** Container orchestration
- **Tailscale:** Private networking and remote access
- **Caddy:** HTTPS termination and reverse proxy
- **NVIDIA Container Toolkit:** GPU access for containers
- **systemd:** Host services and scheduled maintenance

## Repository structure

- `caddy/` - Reverse proxy configuration
- `postgres/` - Shared database infrastructure
- `ai/` - Shared AI infrastructure
- `scripts/` - Maintenance and deployment scripts
- `systemd/` - System services and timers
- `docs/` - Architecture and recovery documentation

Some directories will be added as services are configured.

## Deployment

Infrastructure configuration is maintained directly on the server.

Changes are committed locally and pushed to a private GitHub repository.

Docker Compose services are deployed independently.

## Security

This repository must never contain:

- Private keys or TLS certificates
- Database credentials
- Environment files containing secrets
- Database volumes or backups
- AI model weights or runtime data

Runtime data and secrets remain outside version control.

## AI services: configuration versus runtime files

The repository stores the recipes needed to rebuild services: source code,
Dockerfiles, Compose configuration, pinned dependencies/model revisions, download
and verification scripts, and synthetic evaluation fixtures. Start with
[`ai/transcription/README.md`](ai/transcription/README.md) for the deployed service.
[`ai/generation/README.md`](ai/generation/README.md) documents an evaluated
CPU-only trial runtime. Its temporary container stops after evaluation; a
complete note-generation application is not deployed yet.

Large model weights are downloaded separately into `/srv/lara/ai/models`.
Original recordings, transcripts, job databases, corrections and measurements
live in `/srv/lara/ai/data`. These folders are outside this checkout and must
not be committed. They survive a container replacement, but still need their
own backup/recovery policy. Git alone is not a backup of personal AI data.

For transcription, `compose.yaml` mounts `/srv/lara/ai/models` on the host as
`/models` inside the container, read-only, and sets `MODEL_PATH=/models/large-v3`.
The Dockerfile installs the software; it intentionally does not embed weights.
The pinned downloader fetches and verifies those weights before service startup.

`scripts/bootstrap.sh` prepares host folders and shared networks. Run the
service-specific deployment instructions separately to build the image, fetch
weights and start transcription. Bootstrap does not automatically download models
or start expensive workloads. The current transcription container expects UID/GID
1000; Lara's directory ownership must match that deployment configuration.

## AI ownership and model reviews

Shared AI work is limited to inference, generic extraction, technical job state,
resource management and evaluation. Applications own their domain data and flows.
Notey's application project is `/Users/thejuliamathias/Projects/Personal/notey`.
See [scope, evaluation handoff and model-review policy](docs/ai-scope-and-model-review.md)
for the current boundary, monthly review and private test-data pointers.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`.
It runs checks that need no GPU, model files, secrets or access to Lara:

- Transcription service tests: builds the Dockerfile `test` stage and runs
  `pytest` inside it, the same commands as in
  [`ai/transcription/README.md`](ai/transcription/README.md#tests).
- Generation helper tests: `unittest` discovery of `ai/generation/test_*.py`.
  The job does nothing on revisions without those files.
- Compose and script checks: `docker compose config` on every `compose.yaml`
  (plus any `compose.*.yaml` overlay on top of it) and `shellcheck` on `scripts/`.

CI does not establish transcription or generation quality, GPU fit, deployment
health or the live API behaviour. Those checks stay manual on Lara (for example
`ai/transcription/tests/live_smoke.py`). A green CI run means the code and
configuration are sound, not that a change is deployed or accepted. The checks
are not yet required by branch protection.

## Application routing

See [private application ingress](docs/application-ingress.md) for independent
application routes, the Notey companion change, manual rollout and acceptance gates.
Existing host routing and private AI endpoints must be preserved.
