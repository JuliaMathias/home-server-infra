# AI project status

Last inspection: 2026-10-21 13:15 BRT (America/Sao_Paulo).

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

The first review identified note organization, quotation fidelity and ambiguity
handling as the next work. The full-document preparation below follows the
user's subsequent request to proceed with the complete sermon and supplied notes.
The candidate is not a final model selection.

## Full-sermon notes preparation (2026-10-19)

- The user supplied a searchable NAA PDF, handwritten sermon notes in PDF/.note,
  and a more complete conference notebook with related transcripts/expanded notes
  as a style reference. Eight explicitly selected source files were copied to
  private Lara storage and size/SHA-256 verified. Original files remain intact.
- Both handwritten sermon pages were read visually. Four substantive original
  notes were transcribed with source-page provenance. Grids are writing guides
  and must be absent from the cleaned export, per the user's clarification.
- Seventeen selected Bible ranges (54 verses) were extracted using this PDF's
  typography, including small-cap text. Every verse exactly matches normalized
  text on its source PDF page(s). All were imported into private SQLite with
  translation/book/chapter/verse keys, source hash and page mapping. Retrieval
  matches the checked extraction. This is a validated subset, not a complete
  Bible import or a generic PDF parser proven on other editions.
- Full-recording source preparation uses the second microphone in the overlap,
  the first microphone for its opening and later material, and the user's human
  corrections with explicit uncertainty. Offset mapping is approximate. The
  later appeal/prayer remains a separate relevant section with unconfirmed voice
  identity; it is not silently attributed to the sermon speaker or discarded.
- Eight section tasks assign 137 source blocks exactly once and preserve all four
  original-note integration assignments. Interval assignment does not establish
  semantic completeness. Raw recordings/transcripts/corrections remain unchanged.
- A single CPU batch was started at 21:58 BRT under
  `/srv/lara/ai/data/evaluations/full-sermon-notes-20261020T0052Z`. It uses an
  8192-token context, up to 2048 output tokens per section, one slot/four cores,
  the existing 16 GiB memory cap, structured output, source IDs and context
  preflight. These longer settings are a new measured workload, not a prior fit
  or quality claim. Outputs and thermal/resource evidence remain private.
- Domain prompts, handwriting and Bible text are private evaluation inputs;
  shared infrastructure adds only a domain-neutral sequential batch runner.
  Syntax, Compose and task-assignment checks passed. Full draft generation,
  source-fidelity/completeness review and PDF layout/link validation are pending.
- Native `.note` export is unproven. A linked PDF is the first deliverable;
  using PDF templates on Supernote is a documented possible device-side route,
  but preservation of all link/native-note behavior still needs device testing.

## Ownership and failed long batch (updated 2026-10-20)

The user moved Bible/application work to the separate Notey project/chat.
The eight-task batch failed after 80m09.90s: four sections completed, section_05
reached its 2048-token output allowance (finish_reason=length), and sections 06-08
were not attempted. This was not context overflow or OOM. Targeted review found
reversed influence/attribution and a negation contradiction despite recognized
source identifiers. None of these drafts is accepted as final application output.
The finite monitor was deleted; originals and partial results remain private.
Review and measurements are in `failure-review.json` and
`failure-measurements.json` inside the full-recording evaluation directory.

Sampled CPU package mean/peak was 79.67/87 C; package throttle delta 11 is one
package count, duplicated across logical threads, not seconds. Docker CLI peak
4.763 GiB excludes inactive file cache; host available minimum was 14.566 GiB.
GPU 47-62 C reflects background activity, not CPU generation acceleration.

## Compact comparison reviewed (2026-10-20 16:45 BRT)

User authorized a small source-fidelity/speed comparison before another long run.
Issue #7 tracks four requests on two short private fixtures: developed prose and
compact evidence extraction, using identical source text per pair. Existing
Qwen3-14B Q5_K_M and pinned CPU runtime remain unchanged; one slot/four cores,
16 GiB cap, 4096 context, 768 output tokens per request, fixed existing sampling.
A predeclared rubric checks required propositions, agency, negation and additions.
Task order reverses styles between pairs; prompt caching/order still confound
latency. This is one sample per condition, not a statistical benchmark.

Run: `/srv/lara/ai/data/evaluations/compact-comparison-20261020T1900Z`.
`cases.json`, `rubric.json`, and `fixture-manifest.json` retain private setup;
status, task outputs and telemetry retain evidence. All four requests completed
in 919.94s including 5.42s readiness. Complete JSON and allowed source lists passed;
paired source hashes match. All four outputs failed semantic acceptance after
assistant comparison with the supplied text and predeclared proposition rubric.
This is not a human audio review or a statistical accuracy estimate.

| Fixture | Prose wall time / output tokens | Compact wall time / output tokens |
| --- | --- | --- |
| Attribution | 277.13s / 623 | 135.42s / 277 |
| Negation/coverage | 353.30s / 730 | 148.52s / 235 |

Compact outputs omit required propositions and later source material. Prose
retains more but adds unsupported interpretation; both styles misread ambiguous
figurative language in one fixture. The negation fixture's critical judging
proposition was omitted by both styles. Removing a contradiction by omitting
the claim is not a coverage pass. The six-entry schema ceiling may encourage
selecting early facts; this confounds the test and must be revisited. Faster
output is not accepted as a fidelity or application-workflow improvement.

One sample per condition and different cached prompt counts limit timing claims.
The test excludes later composition cost; no full-sermon speed estimate is made.
Private `comparison-review.json` and `comparison-measurements.json` retain details.
151 telemetry samples: CPU package mean/peak 68.65/73 C, zero recorded package
throttle delta (duplicated counters not summed), Docker CLI peak 3.782 GiB
excluding inactive file cache, host available minimum 17.703 GiB. GPU 45-63 C is
background activity. Sampled peaks may miss spikes; no ambient comparison was made.
Container cleanup/Whisper health are checked separately from content acceptance.

The finite monitor was removed after a connectivity failure; access recovered
and all outputs have now been reviewed manually by the assistant. User authorized
reading the selected private text in tool history, excluding Git/shared display.
No new inference or model switch was launched during review.

Current authorized work: iterate toward good enhanced notes in around 30 minutes
after transcription for an hour-long sermon. PR #10 remains draft until actual
quality/time evidence supports finalization. See `ai-generation-iterations.md`.

Iterations 2-6 have failed reviewed fidelity/completeness/style gates. The explicit
Qwen3.5-4B candidate loads and runs faster than 14B on short samples, but is not
accepted as a workflow or production switch. Iteration5 was intentionally cancelled
after a known evidence failure. Iteration6 finished all four requests with bounded
reasoning256; object coverage did not fix role swaps or unsupported wording.

Iteration7 critic failed: it falsely accepted critical attribution/time/uncertainty
errors. Private review is saved; no automatic repair or acceptance follows.
Iteration8 larger-model critic also failed, accepting all nine paragraphs despite
critical role/time errors; 392.09s request time. Private review/measurements saved.
Iteration9 source-only events also failed: all events were marked negated,
with omissions and invented uncertainty. Private review is saved.
Iteration10 minimal-format notes improved readability but failed attribution,
future/possibility and unsupported-addition checks; 400.83s for both requests.
Private review and measurements are saved.
Iteration11 clean/noisy synthetic controls both failed. Clean preserved most
facts but added a reversed recipient; noisy had several further meaning errors.
Source noise alone does not explain all observed failures. Private review saved.
Iteration12 recommended-sampling profile was confirmed by actual slot settings.
Clean factual control passes; noisy control fails several core meanings. This is
one synthetic pair, not sermon acceptance or a causal sampling-quality claim.
Iteration13 normalization failed fidelity/traceability after three requests in
435.28s; dropped IDs/context boundaries and introduced a quotation typo. No
composition was run from those outputs. Private review saved; no inference active.
The user authorized the prepared 9B comparison by saying "please continue" after
the explicit download question. Original proposal and authorization are preserved.
The 9B download verified and loaded. First control failed semantic coverage and
negation despite a normal stop/valid JSON, after 225.75s request plus 11.09s load.
Private review and measurements are saved; no sermon regression was run.
Current single comparison:
`/srv/lara/ai/data/evaluations/qwen35-9b-off-control-20261021T1615Z`.
Same noisy control/settings with thinking disabled; inspect actual state before
further work. Quality and complete 30-minute workflow acceptance are unproven.
See `ai-generation-review.md` for the required private manual review procedure.
Default/deployed services and original weights remain unchanged.
All full-workflow acceptance gates remain unmet.

Generic tooling now supports explicit pinned candidate selection and optional
bounded reasoning controls. Defaults retain the original model and reasoning-off.
Thirteen deterministic offline tests, compile and Compose checks passed; actual
short model inference is separate evidence. No new application implementation,
Bible migration, production export, GPU or Whisper deployment change was made.
Existing private source/database fixtures remain unchanged except the explicitly
versioned evaluation correction with raw provenance noted in the experiment log.

A monthly model research heartbeat is active for the first day of each month at
09:00 America/Sao_Paulo. It compares credible improvements with actual baselines,
uses primary sources, and recommends tests without automatically downloading,
benchmarking or deploying models. The generation model remains a trial candidate.

A roughly two-hour transcription and repeated sustained jobs remain unvalidated.

There is no review UI, diarization, verified preacher identification, automatic
sermon segmentation, complete production notes application, or retention cleanup yet. The service intentionally
provides general transcription only. Final LLM/OCR selection remains open.

Uploads are limited to 512 MiB, multipart parsing is serialized, and four
outstanding jobs are allowed. Queued jobs survive restart; interrupted uploads
and running jobs are explicitly failed and may be resubmitted. Originals stay
available. Model initialization failures require an operator restart after the
underlying issue is resolved. No silent CPU fallback is configured.
