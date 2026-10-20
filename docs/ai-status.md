# AI project status

Last inspection: 2026-10-19 21:17 BRT (America/Sao_Paulo).

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

## Real recording evaluation (2026-10-19)

- A complete 68m30.51s Portuguese recording processed successfully in 7m39.17s
  with the existing warm Large V3 GPU configuration (about 8.95x real time).
- Upload-to-result client time was 7m40.53s. Full baseline/run/cooldown took
  8m25.92s. No second transcription was launched during the scheduled check.
- Output: 1,469 segments, about 9,151 whitespace-delimited words, and 9,171
  word-timestamp entries. All timestamp bounds passed; segment ordering checks
  found no backwards overlap beyond the 0.1-second tolerance.
- This establishes successful full-recording processing, not verified recognition
  accuracy. Draft passages and names need audio review; no reference WER exists.
  Portuguese was specified explicitly, so language probability is not an accuracy
  score or evidence of automatic language detection.
- Two-second host telemetry: GPU peak 2379 MiB (2.32 GiB), GPU mean/peak
  temperatures 65.4/69 C, CPU package mean/peak 79.3/91 C. Baseline CPU/GPU means
  were 49.9/46.9 C. CPU package throttle count increased by 8665; duplicated
  logical-thread counters were not summed. Counts are not throttled seconds.
- GPU software thermal flag was active in 220/227 transcription-phase samples;
  no hardware thermal flag was active. The cause of software capping at these
  temperatures is unresolved. Do not label the deployment thermally unconstrained.
- Host available RAM never fell below about 15.4 GiB; this is not a measurement
  of peak per-service RAM. GPU utilization averaged 92.4%; power averaged 26.2 W.
- All 250 telemetry samples were collected without reported monitoring errors.
  Brief thermal spikes, fan speed, ambient conditions, clocks, and attribution
  of other host activity were not measured.
- Original recording and Lara copy have matching SHA-256. Private originals,
  transcripts, results, telemetry, and a detailed educational report remain
  outside Git under `/srv/lara/ai/data/evaluations/`.
- Reading copies were exported to the user's private mirrored project-files
  folder. The scheduled completion check is being stopped after reporting.

## Same-sermon recording comparison (2026-10-19)

- A second, better-microphone recording completed with the same model revision
  and inference settings. Duration 59m44.05s; processing 6m49.84s (8.74x real time).
- Peak GPU memory was 2379 MiB; sampled CPU/GPU peaks were 93/68 C.
  Telemetry remained enabled; no optimization or power-setting changes were made.
- Normalized transcript alignment found 197 matching runs of at least 12 words.
  Median original-minus-second-recording offset was 199.17 seconds. Quarter
  medians were 199.17, 199.14, 199.12, and 199.20 seconds: no clear cumulative
  drift in these text anchors. This is not sample-accurate audio synchronization.
- Comparison covers the common interval only. Different file durations and word
  counts must not be treated as an omission/accuracy measurement.
- Several previously suspicious phrases have more plausible alternatives in the
  new draft, but both drafts still contain wording requiring listening review.
  Neither is an independently checked reference; no WER/accuracy claim is made.
- New segment bounds/ordering checks passed. Private full side-by-side text,
  a focused disagreement report, and new transcript exports are outside Git,
  with verified reading copies in the user's mirrored project-files folder.
- Paired listening suggestions total 4m30s across both recordings. Source files
  and earlier exports were preserved. The scheduled checker was deleted at the
  user's request after the immediate completion review.

## Targeted human review (2026-10-19)

- The user supplied 72 timestamped corrections/annotations from selected parts
  of the original recording. These form a private partial reference, not a
  reviewed transcript of the full sermon.
- Four explicitly uncertain annotations remain flagged. One zero-duration
  timestamp is retained as a point annotation; human timing is approximate.
- Listening corrections confirm specific improvements in the second recording's
  draft and also identify remaining wording errors. The user subsequently
  accepted equivalent biblical-name spellings in the second transcript; the
  private review findings now reflect that clarification.
  No overall WER or recognition-accuracy percentage has been assigned.
- Raw transcripts and earlier comparison artifacts were preserved. Corrections,
  structured provenance/uncertainty, and review findings are outside Git, with
  verified reading copies in the private mirrored project-files folder.
- Future note generation must prioritize reviewed wording where available,
  retain uncertain speech explicitly, and keep edits separate from raw ASR.
  No model settings, prompts, or automatic global replacements were changed.

## Next action and remaining limits

On 2026-10-19 the user chose to retain the current transcription baseline,
collect findings and defer optimization, and proceed to shared generation.
See `ai-transcription-follow-ups.md`; remaining checks are not marked passed.

The first Qwen3-14B Q5_K_M CPU trial completed on 2026-10-19 at 20:56 BRT.
Weights passed size/SHA-256 verification and the pinned llama.cpp b11723 runtime
loaded successfully. Raw evidence is private under
`/srv/lara/ai/data/evaluations/generation-20261019T2340Z`.

- One slot, four CPU cores, 16 GiB memory cap, 4096 context tokens; no GPU access
  or published host ports. The temporary container stopped with exit code 0,
  OOMKilled=false. Whisper remains healthy. No duplicate inference was started.
- Model load/readiness took 15.61 seconds. Requests took 43.98 seconds for the
  synthetic Portuguese case, 77.93 seconds for the exercise report, and 220.75
  seconds for a private 55-second reviewed sermon excerpt. Decoding was about
  3.20–3.51 tokens/second. TTFT and whole-sermon throughput remain unmeasured.
- CPU package sampled mean/peak: 79.53/84 C. Recorded package throttle counters
  had zero delta in every logical-thread copy; duplicates were not summed.
- GPU sampled temperature range 48–60 C, memory 1995 MiB, utilization zero.
  These are background/Whisper readings, not GPU generation measurements.
- Docker CLI reported peak 3.084 GiB, excluding Linux file cache; this is not
  total resident model memory or full cgroup peak. Host MemAvailable minimum
  was 17.82 GiB, which includes reclaimable memory. Sixty samples included one
  pre-creation Docker-stats error and a final stopped-container zero reading.
- Source-fidelity review: synthetic Portuguese facts/uncertainty survived, but
  the output mostly restated source lines. The exercise total was correct;
  explicit per-activity subtotals from its rubric were omitted.
- The private sermon draft is not accepted as ready-to-use notes. It is overly
  mechanical, introduces an unsupported interpretation and alters wording inside
  a quotation. Source IDs alone do not establish factual fidelity. This is an
  assistant comparison against supplied text, not another audio review or a
  representative quality score. No user-edition Bible text was loaded/verified.
- Raw requests, responses and source annotations remain intact. A labeled draft,
  reviewed-source reading copy and detailed report were exported to the user's
  private Drive mirror and byte-verified. Personal examples are outside Git.

Next: improve note organization, quotation fidelity and ambiguity handling on
this short reference before processing the entire sermon. No further run or
optimization sweep has been started. Full-sermon staged processing, completeness
checks, PDF-note integration and Bible retrieval remain application work. The
first candidate is feasible for short local requests but is not a final selection.
A roughly two-hour transcription and repeated sustained jobs remain unvalidated.

There is no review UI, diarization, preacher identification, sermon segmentation,
note generation, or automatic retention cleanup yet. The service intentionally
provides general transcription only. Final LLM/OCR selection remains open.

Uploads are limited to 512 MiB, multipart parsing is serialized, and four
outstanding jobs are allowed. Queued jobs survive restart; interrupted uploads
and running jobs are explicitly failed and may be resubmitted. Originals stay
available. Model initialization failures require an operator restart after the
underlying issue is resolved. No silent CPU fallback is configured.
