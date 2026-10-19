# Shared transcription

Private asynchronous speech-to-text using Faster Whisper and Whisper Large V3.
No sermon analysis, preacher identification, review UI, or note generation is
performed by this service. Model files are downloaded separately; inference
runs locally and does not upload recordings to external services.

## Deployment

First run the repository's `scripts/bootstrap.sh` as the regular deployment
user on a newly prepared host. It creates the shared model directory and the
transcription data directory before Docker mounts them. On Lara the deployment
user and this container use UID/GID 1000. Check ownership if restoring to a
different host; do not let Docker implicitly create a root-owned data directory.
Bootstrap prepares folders/networks; the following commands build software,
download the pinned weights, and start the service explicitly.

Run from `/srv/lara/infrastructure/ai/transcription` on Lara:

```sh
docker compose build
docker compose run --rm --no-deps --user 1000:1000 \
  -e HF_HUB_OFFLINE=0 -e HF_HOME=/models/.cache \
  -v /srv/lara/ai/models:/models:rw \
  -v "$PWD/download-model.py:/app/download-model.py:ro" \
  transcription python3 /app/download-model.py
docker compose up -d
docker compose ps
docker compose logs --tail=50 transcription
```

The downloader verifies every asset against the pinned upstream size/hash manifest.
The first download is several GB. The model revision is pinned in the downloader
and Compose file. Check those match when deliberately upgrading. The model is
loaded from local storage with network downloads disabled during normal startup.
Upstream requirements: https://github.com/SYSTRAN/faster-whisper#requirements

The container runs as UID/GID 1000, with GPU access, four CPU cores, a 12 GiB RAM
limit, read-only root/model mounts, and no published ports. The existing
`lara-backend` network must exist. The host data directory must be writable by
UID 1000. Do not run multiple replicas or Uvicorn workers against the same data
directory: an exclusive file lock prevents simultaneous ownership.

## API

From an application/container attached to `lara-backend`:

```sh
curl -F file=@recording.m4a -F language=pt \
  http://transcription:8000/v1/transcriptions
curl http://transcription:8000/v1/transcriptions/JOB_ID
```

Omit `language` for automatic detection. Supported Whisper language codes are
validated; `pt` and `en` are the primary intended languages. The task is always
transcription, preserving the spoken language, rather than translation.

Uploads return HTTP 202 with `job_id`, `status`, and `status_url`. Poll the status
URL for `uploading`, `queued`, `running`, `completed`, or `failed`. A completed job
contains `result` with text, segments, word timestamps, language/probability,
original recording duration, speech duration, model revision, device/compute
settings, processing seconds, and warnings. All timestamps refer to the original
recording. Speaker diarization is not included yet.

Empty/invalid requests return 422; oversized uploads 413; queue saturation 429
(with Retry-After); an unavailable model returns 503; unknown jobs return 404.
Undecodable media is accepted into the asynchronous job then marked failed with
`transcription_failed:<exception class>`. Operator logs contain diagnostic
tracebacks. Silence returns an empty result with `no_speech_detected` when VAD
finds no speech. Never infer a person's identity from the transcript service.

## Storage and limits

- Originals: `/srv/lara/ai/data/transcription/UUID.media` (never automatically trimmed).
- Technical metadata/results: `jobs.sqlite3` in that directory, SQLite WAL mode.
- Model assets: `/srv/lara/ai/models/large-v3`.
- Defaults: 512 MiB per file; four outstanding uploads/queued/running jobs;
  one inference worker; GPU `int8_float16`, beam size 5, VAD and word timestamps.
- Multipart request parsing has a file limit plus 64 KiB envelope allowance.
  Multipart parsing is serialized to keep temporary storage bounded.
  Temporary parsing files use the container's bounded 1 GiB temporary mount.
- There is no automatic retention cleanup yet. Monitor disk space and retain or
  delete originals and job records deliberately. Back up the data directory with
  the service stopped, or use SQLite's online backup API plus original files.

Normal shutdown waits for the current job. Docker allows 30 seconds before
termination. At restart, unfinished uploads/running jobs are explicitly failed;
queued jobs remain queued. Retained originals can be submitted again. Completed
results survive restart. There are no automatic inference retries or silent CPU
fallbacks; changing compute device is an explicit deployment choice.

`/health/live` checks the HTTP process. `/health/ready` returns 200 only after the
model loads and the worker is alive. Compose health can take several minutes
while the model loads; unhealthy status alone does not restart a container.

## Dependency compatibility

`requirements.in` records direct choices; `requirements.lock` pins the complete
runtime Python environment. The Docker base is pinned by digest. PyAV 16.1.0 is
intentional: 19.0.1 removed `av.open(metadata_errors=...)`, which Faster Whisper
1.2.1 still calls. Preserve the real-decoding regression test when upgrading.

## Tests

```sh
docker build --target test -t home-server-transcription:test .
docker run --rm --tmpfs /tmp:mode=1777 home-server-transcription:test
```

Unit/API tests use a substitute engine and do not establish recognition quality
or GPU capacity. Record real inference and resource measurements separately.
A representative two-hour recording and the user's real samples remain required
before claiming the transcription milestone is fully validated.

## Watch development commands

From the Mac, while work is active:

```sh
ssh lara 'tail -n 100 -F /srv/lara/ai/data/transcription-development.log'
```

This log is operational data outside Git. It records the development command
trace and output, not application recordings or transcript contents by design.

## Initial measured validation

On 2026-10-19, ten automated tests and all four live API checks passed.
An 11-second public English recording transcribed in 1.89 seconds; a synthetic
10.71-second Brazilian Portuguese sample in 1.51 seconds. Silence produced no
segments; corrupt media produced a failed job. Actual restart retained every
existing result unchanged. One-second GPU sampling observed a peak of 2251 MiB
and 55 C. These short smoke checks do not establish long-recording performance
or sermon accuracy; see `../../docs/ai-status.md`.

For the optional live check, provide `jfk.flac`, `portuguese.wav`, `silence.wav`,
and `corrupt.wav` in a fixture directory outside Git, then run the test image on
`lara-backend` with that directory mounted writable at `/fixtures`:

```sh
docker run --rm --entrypoint /opt/venv/bin/python --network lara-backend \
  -v /srv/lara/ai/data/transcription-fixtures:/fixtures \
  home-server-transcription:test tests/live_smoke.py
```

The script writes a JSON summary to the fixture directory. It uses the running
GPU service; the client container itself does not need GPU access.
