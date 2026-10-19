# AI project status

Last inspection: 2026-10-19 15:28 BRT (America/Sao_Paulo).

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

## Preparation and implementation

- Preparation committed as `0e4c23a`; SSH signature verified.
- Shared service source/configuration now lives in `ai/transcription/`.
- The service is deployed and healthy as `shared-transcription-transcription-1`,
  reachable privately as `http://transcription:8000` on `lara-backend`.
- No host ports are published. Caddy and host configuration were not modified.
- Runtime uses Faster Whisper 1.2.1, CTranslate2 4.8.3, PyAV 16.1.0,
  CUDA 12.8.1/cuDNN, and pinned Python dependencies in `requirements.lock`.
- PyAV 19.0.1 failed actual decoding because its `av.open` API removed the
  `metadata_errors` argument Faster Whisper uses. Pinning 16.1.0 fixed this;
  the test suite includes a real audio-decoding regression check.
- Large V3 revision `edaa852ec7e145841d8ffdb056a99866b5f0a478` was
  downloaded into `/srv/lara/ai/models/large-v3`; all model assets passed
  upstream size/hash verification. Source manifest is retained alongside them.
- One GPU worker uses `int8_float16`, beam size 5, VAD, and word timestamps.
  SQLite stores jobs/results, originals are retained, and concurrent ownership
  is prevented with a file lock.

## Verification evidence

- Ten automated tests passed: lifecycle, result persistence, input validation,
  upload limits (including chunked multipart), atomic queue capacity, interrupted
  job recovery, inference/model failures, exclusive worker ownership, queue
  saturation, and real audio-decoder compatibility.
- Actual API/GPU checks passed using a public OpenAI Whisper JFK fixture
  (11 seconds), synthetic Brazilian Portuguese speech (10.71 seconds), silence,
  and corrupt media. These are smoke tests, not a representative quality study.
- English inference took 1.89 seconds; Portuguese 1.51 seconds; silence 0.04
  seconds. Do not extrapolate these short results into a two-hour runtime claim.
- Both speech tests checked expected words, requested language, nonempty segments,
  CUDA/compute settings, and segment bounds within original recording duration.
- Silence produced no segments and an explicit warning; corrupt media persisted
  a failed job. The initial decoder failure is also retained as a diagnostic job.
- Actual container restart preserved all five stored job records/results
  byte-for-byte. A completed transcript remained retrievable through the API.
- One-second GPU sampling observed a peak of 2251 MiB, and a peak temperature of
  55 C across startup and short inference checks. Brief spikes may be missed.
- Container RAM after restart was about 1.47 GiB. GPU idle use was about 1913 MiB.
- Raw measurements, fixtures, and JSON summaries remain outside Git under
  `/srv/lara/ai/data/transcription-fixtures/` and `transcription-gpu.csv`.
- Development command/output log: `/srv/lara/ai/data/transcription-development.log`.

## Next action and remaining limits

Evaluate a representative sermon and a roughly two-hour recording for accuracy,
completeness, word-timestamp quality, peak memory, and throughput. The first
transcription deployment works, but the full milestone is not yet validated.

There is no review UI, diarization, preacher identification, sermon segmentation,
note generation, or automatic retention cleanup yet. The service intentionally
provides general transcription only. Final LLM/OCR selection remains open.

Uploads are limited to 512 MiB, multipart parsing is serialized, and four
outstanding jobs are allowed. Queued jobs survive restart; interrupted uploads
and running jobs are explicitly failed and may be resubmitted. Originals stay
available. Model initialization failures require an operator restart after the
underlying issue is resolved. No silent CPU fallback is configured.
