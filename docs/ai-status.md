# AI project status

Last inspection: 2026-10-19 15:10 BRT (America/Sao_Paulo).

## Verified baseline

- SSH host `lara` connects as `thejuliamathias`.
- Canonical checkout: `/srv/lara/infrastructure`.
- Remote: `https://github.com/JuliaMathias/home-server-infra.git`.
- Baseline commit: `d29b297` (Add systemd service deployment script).
- Branch `main` was clean and tracking `origin/main` before these files.
- No `AGENTS.md` was found under `/srv/lara` or in its inspected ancestor paths.
- Existing tracked files cover Caddy, certificate renewal, bootstrap/systemd
  scripts, `.gitignore`, README, and host setup documentation.
- OS reports Ubuntu 26.04.1 LTS; Compose reports v5.6.0.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB VRAM;
  NVIDIA driver 580.178.04.
- Memory inspection: 31 GiB usable RAM, about 20 GiB available;
  2 GiB swap, unused at inspection. These values will change with workload.
- Filesystem containing `/srv/lara`: 247 GiB available at inspection.
- Docker is accessible as the regular SSH user. The running-container list
  contained `lara-caddy-caddy-1`; shared networks `lara-proxy` and `lara-backend`
  exist. Other Docker networks also exist and must be preserved.
- `/srv/lara/ai/models` and `/srv/lara/ai/data` exist. No shared AI service is
  implemented in the infrastructure checkout at this baseline.
- Passwordless sudo was unavailable. No privileged host changes were made.

## This preparation step

Working rules and supporting project, roadmap, operations, and status documents
have been created locally and replicated over SSH to the canonical checkout.
SHA-256 comparison verified byte equality for all five files. The resulting
repository changes contain only the five intended new Markdown files.
No model weights have been downloaded, no AI container has been launched, and
no commits or pushes have been made by this preparation step.

## Next action

Implement milestone 1 from `ai-roadmap.md`: the private reusable asynchronous transcription service,
starting with upstream dependency checks and a measured Large V3 deployment.

## Still to establish during implementation

- Exact dependency/image versions and supported CUDA/compute configuration.
- Whether Large V3 fits the GPU with acceptable quality; no fit or throughput
  result has been measured yet.
- Final upload limits, durable job storage, restart handling, and retention.
- Representative recordings and PDF samples for quality evaluation.
- Final LLM and handwriting model selection; candidate names are not decisions.
