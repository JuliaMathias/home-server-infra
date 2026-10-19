# Home Server Setup

This document describes the host configuration for the personal
home server.

The infrastructure repository is maintained directly on the server
and synchronized with a private GitHub repository.

## Hardware

- CPU: Intel Core i7-11370H
- GPU: NVIDIA GeForce RTX 3050 Mobile (4 GB VRAM)
- RAM: 32 GB
- Storage: NVMe SSD

## Operating System

- Ubuntu 26.04.1 LTS (Resolute Raccoon)
- Linux kernel 7.0.0-38-generic at initial setup

## Remote Access

Tailscale provides private networking between the server and
authorized devices.

SSH is accessible through Tailscale.

SSH security configuration:

- Public-key authentication enabled
- Password authentication disabled
- Root SSH login disabled

Firewall:

- UFW enabled
- Default incoming policy: deny
- Default outgoing policy: allow
- SSH port 22 allowed on tailscale0

Docker-published ports require separate security review because
Docker manages its own networking and firewall rules.

## Container Infrastructure

Docker Engine and Docker Compose are installed from Docker's
official Ubuntu repository.

Versions at initial setup:

- Docker Engine: 29.9.1
- Docker Compose: 5.6.0
- NVIDIA Container Toolkit: 1.20.1

The NVIDIA runtime is registered with Docker.

GPU access was verified using:

    sudo docker run --rm --gpus all ubuntu:24.04 nvidia-smi

## Directory Structure

The server uses /srv/lara as its deployment root.

- infrastructure/: Shared infrastructure configuration
- ai/: Shared AI services, models, and data
- apps/: Independently deployed applications
- backups/: Local backup staging

The infrastructure directory is a Git working tree.

Runtime data, secrets, certificates, and database backups must
not be committed to Git.

## Docker Networks

Two shared bridge networks currently exist:

- lara-proxy
- lara-backend

The proxy network connects Caddy to applications.

The backend network is available for shared internal services.
Sensitive services should use dedicated networks where practical.

## HTTPS

Caddy runs as a Docker Compose service.

Tailscale provides private network connectivity.

Caddy terminates HTTPS using a certificate issued for the
server's Tailscale hostname.

The HTTPS listener is published only on the server's Tailscale
IPv4 address.

Certificate renewal is handled by:

- /usr/local/sbin/lara-renew-cert
- lara-cert-renew.service
- lara-cert-renew.timer

The renewal service runs daily through a systemd timer.

Private keys and certificates are stored outside Git.

## Headless Operation

The systemd-logind configuration ignores laptop lid events.

Configuration file:

    /etc/systemd/logind.conf.d/99-lara-server.conf

The server should remain connected to power.

Thermal performance should be monitored during sustained
GPU-intensive workloads.

## Backups and Recovery

GitHub stores the version-controlled infrastructure configuration.

Database contents and application data require separate backups.

Existing PostgreSQL backups were created during the Ubuntu
upgrade and verified on an external SSD.

A complete automated backup and recovery workflow is still
planned.

## Outstanding Work

- Implement infrastructure deployment scripts
- Review package management and obsolete APT sources
- Implement scheduled application/database backups
- Deploy shared PostgreSQL infrastructure
- Deploy shared AI inference services
- Add application-specific deployment configurations
