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
