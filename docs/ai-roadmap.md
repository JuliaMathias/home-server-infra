# AI implementation roadmap

Status: initial transcription service deployed with short GPU/API checks passing.
A 68.5-minute real recording passed processing and timestamp-integrity checks.
The user accepted this as a working baseline on 2026-10-19 and deferred further
transcription optimization. Broader accuracy and two-hour checks remain unverified,
but do not block beginning shared generation evaluation. Update `ai-status.md`
with evidence.

## 0. Establish project context

- [x] Read the referenced conversation and distinguish requirements from advice.
- [x] Inspect Lara's existing checkout and inherited instructions.
- [x] Create working rules, architecture, operations guidance, and this roadmap.
- [x] Replicate the explicit file set to the infrastructure checkout via SSH.
- [x] Verify the local and remote copies match and review the resulting diff.

## 1. Reusable transcription

1. Check current Faster Whisper/CTranslate2 documentation and compatible
   container dependencies. Record exact chosen versions.
2. Implement a domain-neutral asynchronous upload/job/result contract. The
   proposed routes below require no public port or sermon-specific fields.
3. Store technical jobs/results durably, with one inference worker initially.
   Bound upload size, queue length, and processing concurrency. Validate media,
   use generated storage identifiers, and reject arbitrary server paths/URLs.
4. Deploy a reproducible Compose service with model/data paths outside Git,
   readiness checks, useful errors, and restart behavior documented.
5. Benchmark Whisper Large V3 on Lara with explicit compute settings. Measure
   peak VRAM/RAM, elapsed time, and transcription quality. If GPU memory is
   insufficient, report it and evaluate CPU/other settings explicitly.

Proposed API, to finalize during implementation:

| Request | Behavior |
| --- | --- |
| `POST /v1/transcriptions` | Multipart media upload, optional language; return `202` with job ID |
| `GET /v1/transcriptions/{job_id}` | Return queued/running/completed/failed state and result or useful error |

Results should include detected/requested language, original duration,
timestamped segments, model identifier, compute settings, and warnings. Keep
timestamps relative to the original recording even when VAD/chunking is used.
Speaker labels may be absent until optional diarization exists.

Acceptance evidence:

- An actual Portuguese and English sample produce timestamped transcripts.
- A roughly two-hour recording completes within measured resource limits.
- Silence, corrupt media, unsupported language/input, queue saturation, and
  worker interruption return documented behavior rather than silent loss.
- Technical job state survives service restart; interrupted jobs recover or
  explicitly fail. Concurrent requests cannot start competing GPU workloads.
- Original files remain intact and results do not contain sermon assumptions.
- Tests cover the job lifecycle and error paths. Real inference evidence is
  recorded separately from tests using fake models.

Two recordings of the same sermon have been processed and targeted excerpts
reviewed. Broader recognition accuracy remains unmeasured.

Initial deployment evidence (2026-10-19):

- [x] Private asynchronous upload/status/result API with durable SQLite jobs.
- [x] Bounded uploads/queue, exclusive single worker, and restart recovery.
- [x] Pinned container/model/dependencies and external model/runtime storage.
- [x] Ten tests, including actual audio-decoder compatibility.
- [x] Real GPU/API smoke tests: English, synthetic Portuguese, silence, corrupt media.
- [x] Actual restart preserved existing results; no host ports are published.
- [x] Complete 68.5-minute Portuguese recording processed; timestamp bounds checked.
- [x] Same-model comparison with a second microphone recording; alignment and review exports.
- [x] Targeted Portuguese excerpts reviewed by the user; uncertainty and provenance retained.
- [ ] Representative real Portuguese/English recordings reviewed against audio for accuracy.
- [ ] Investigate CPU throttling and GPU software thermal capping with controlled tests.
- [ ] Roughly two-hour recording validated for completeness and resource use.

See `ai-status.md` for measurements and `../ai/transcription/README.md` for use.

See `ai-transcription-follow-ups.md` for findings and deferred experiments.

## 2. Shared generation and extraction

Current next step: prepare a repeatable Qwen3-14B/llama.cpp evaluation using
source-grounded Portuguese notes and a separate exercise-report task. See
`../ai/generation/README.md`. Preparation is not a model-quality result.

- Benchmark larger LLM candidates using representative transcript sections and
  a distinct exercise-report task to check reuse and quality.
- Measure model load/unload and CPU/GPU contention before concurrent deployment.
- Extract embedded PDF text first; benchmark handwriting with actual samples.
- Preserve page/layout evidence and expose uncertain extraction for correction.
- Add resource coordination when a second expensive runtime is introduced.

## 3. Independent study-notes application

- Create the application in its own repository, with sermon and lecture modes.
- Analyze boundaries, relevant post-sermon material, and preacher evidence.
- Add review and overrides for identity, ranges, OCR, and translation settings.
- Import user-supplied NAA/NIV PDFs with verse-range validation and provenance.
- Generate unified comprehensive notes with deterministic passage insertion.
- Add source-aware quality checks, revision, and Markdown/PDF export.

Acceptance: original note content remains represented; important transcript
content is covered; each reference has its complete verified passage or a
visible unresolved issue; manual corrections survive regeneration.
