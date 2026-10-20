# Shared generation evaluation preparation

This directory contains evaluation tooling and a private CPU-only trial runtime,
not a selected production model or a complete note-generation application.
The first candidate is Qwen3-14B Q5_K_M through llama.cpp.
Its official immutable revision, file size and SHA-256 are in `candidate.json`.
Model weights and all run outputs belong under `/srv/lara/ai/`, outside Git.

## First actual run

1. Pin a llama.cpp runtime image/revision and verify the official GGUF hash.
2. Begin with one bounded CPU feasibility run. Transcription currently occupies
   about 2 GiB GPU memory; do not assume the two models can coexist. Before GPU
   evaluation, implement explicit resource coordination and safe job draining.
3. Use one request at a time, an initial 4096-token context and at most 768
   output tokens. Reject oversized inputs explicitly rather than truncating them.
   Validate the installed runtime flags/template first. Qwen3 non-thinking mode
   should be configured explicitly and recorded; do not assume runtime defaults.
4. Run the supplied two synthetic cases with fixed sampling settings. Repeat
   on a private, reviewed transcript excerpt without uncertain words presented
   as fact. Domain prompts and correction precedence belong to the application.
5. Record load time, time to first token when streaming is measured, complete
   request time, prompt/output token counts, peak RAM/VRAM and sampled CPU/GPU
   temperatures. Distinguish cold load from warm inference. Reuse the existing
   thermal collection approach; never sum duplicated CPU package counters.
6. Human-review against each case's requirements. Fluency and valid JSON are
   not evidence of factual fidelity. Record omissions, unsupported additions,
   negation/number mistakes and uncertainty handling separately from speed.

## Harness

`evaluate.py --endpoint http://PRIVATE_HOST:PORT --model MODEL_ALIAS
--output /srv/lara/ai/data/evaluations/generation-RUN_ID` sends the cases
sequentially to a compatible `/v1/chat/completions` endpoint. There is no default
public endpoint. The output directory must be new and outside the Git checkout.
Requests, responses, errors, timestamps and wall-clock timings are preserved.
This non-streaming runner does not measure time to first token or hardware
telemetry; collect those separately. Failures produce a nonzero exit code.
`--validate-only` checks fixtures without loading a model or sending requests.

After both synthetic cases pass source-fidelity review, evaluate private sermon
material with traceable segment references and the user's correction layer.
Do not generate Bible quotations from model memory. User PDF integration and
Bible imports remain separate application/extraction work.

## Sources and unresolved decisions

- https://huggingface.co/Qwen/Qwen3-14B-GGUF
- https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md

Qwen3-30B-A3B-Instruct-2507 remains a comparison candidate; its exact available
GGUF source, quantization and memory budget still need verification. A metadata
lookup of a presumed official GGUF repository returned HTTP 401, which does not
establish that the model itself is unavailable. Do not substitute silently.
See the first-trial evidence below. Long inputs and repeated sustained workloads
remain unvalidated.

## CPU-only trial workflow

`compose.yaml` uses the official prebuilt llama.cpp server image; no custom
Dockerfile is required because we are not modifying that runtime image. Its
immutable reference is in `runtime-image.txt` (build b11723, source commit
`31288c9c66e59377f7788d920678a565bb89dd37`). Before manual Compose commands, set
`GENERATION_IMAGE` to the contents of that file. The model directory is
mounted read-only, no host ports or GPUs are exposed, concurrency is one, and
memory/CPU limits are explicit. The trial is stopped after evaluation.

Run `python3 download-model.py` to fetch the pinned 10.51 GB candidate with
size/SHA-256 verification. An exclusive download lock prevents duplicate work;
an existing mismatched model is preserved and reported rather than overwritten.
Download failures retain the partial file for diagnosis; retry currently restarts
the transfer rather than resuming it.

`python3 run-trial.py --run-dir /srv/lara/ai/data/evaluations/NEW_RUN_ID
--private-cases /srv/lara/ai/data/PRIVATE_CASES.json` waits for that download to
finish, loads the CPU model, runs the two public cases sequentially, and optionally
produces a preliminary private excerpt draft. It does not wait for quality
acceptance of the synthetic outputs before creating that draft. All outputs
require review. Run directories cannot be reused and a file lock blocks duplicate
trial processes for the same directory. There are no automatic retries.

The workflow captures non-streaming request wall time, runtime logs and sampled
host temperatures/available memory, GPU memory/temperature/utilization and
container RAM. The GPU readings reflect Whisper/background activity because the
trial has no GPU access. CPU package throttle counters are recorded by path and
must not be summed across duplicated logical threads. Sampling may miss spikes.
Model load/warmup is timed separately. Time to first token is not measured.

A reviewed excerpt trial does not generate notes for the entire sermon. Full
notes still require staged processing, correction precedence, source tracing,
completeness checks and integration of the user's existing notes and Bible PDFs.

## First measured CPU trial (2026-10-19)

Verified weights loaded in 15.61 seconds. Three non-streaming requests completed
in 43.98, 77.93 and 220.75 seconds, with about 3.20–3.51 output tokens/second.
The third covered only a 55-second reviewed private excerpt. CPU package mean/
peak was 79.53/84 C with zero observed throttle-counter increments. Docker CLI
reported peak 3.084 GiB (Linux file cache excluded, not full resident model RAM).
Sixty telemetry samples include one initial Docker-stats error before creation.
The container stopped successfully and Whisper remained healthy.

The short synthetic tasks preserved most facts; the private excerpt draft had
weak synthesis, unsupported interpretation and altered quotation wording. It is
not accepted as ready-to-use study notes. Private source/output comparisons and
measurements remain outside Git, with a reading report in the user's Drive mirror.
No overall accuracy percentage or full-sermon quality claim is made. The next
step is source-grounded prompt/workflow improvement on the same excerpt.

The pinned runtime warns that `enable_thinking` via template kwargs is deprecated
in favor of `--reasoning off`. The run still completed; record and validate that
explicit flag when deliberately updating trial configuration.

## Longer structured batches

`run-batch.py --run-dir PRIVATE_RUN --cases PRIVATE_TASKS.json --context 8192`
runs one to 32 private tasks sequentially, retaining requests, responses and
telemetry. Each task supplies messages, an output schema and a 128–2048 output
limit. Source-ID validation is supported when source metadata is supplied.
These checks validate structure/traceability, not factual entailment or coverage.
A global batch lock and an existing-container check prevent replacing an active
model run. Run directories cannot be reused automatically. The private model
container is stopped after completion/failure. There are no automatic retries.

Compose accepts `GENERATION_CONTEXT_SIZE` and `GENERATION_OUTPUT_LIMIT`; defaults
remain 4096 and 768. Batches explicitly set the larger bounds and use `--reasoning
off` with the pinned runtime. Template application and tokenization check input
plus output against context before inference; oversized inputs fail explicitly.
Domain-specific prompts, source text and document rendering remain outside the
shared runtime. The first complete-recording batch failed on output truncation
after four of eight tasks; targeted source-fidelity review also failed. No full
document completion is claimed.

## Bounded workflow comparison (issue #7)

Compare developed prose and compact evidence extraction on identical short
private sources before another long run. Use the existing runner/model with
4096 context, 768 output tokens per task and unchanged sampling/resource limits.
Two fixtures and two styles produce four requests; private cases, provenance and
a predeclared proposition rubric stay outside Git.

Review complete JSON and allowed source IDs separately from semantic coverage,
agency, negation and unsupported additions. Compare time and token count only
alongside quality. Reverse style order across fixtures but acknowledge prompt
cache/warm-state effects and one sample per condition. This experiment changes
prompt/output style together and excludes later composition cost; it establishes
neither an isolated causal speedup nor whole-sermon performance. Keep full
application orchestration and production prompts in the consuming project.


### Reviewed comparison result (2026-10-20, issue #9)

All four requests completed without truncation, but all failed semantic
acceptance. Compact output took 135/149 seconds versus prose 277/353 seconds
on the paired fixtures, with fewer output tokens. It omitted required facts;
prose retained more but introduced unsupported interpretation. Complete JSON and
recognized source IDs did not establish supporting evidence or coverage.

The schema's maximum of six entries may bias selection toward early facts.
Before another test, consider required proposition slots, full-source coverage
and ambiguity checks. Do not automatically rerun, accept either prompt or
extrapolate to full-sermon speed. One sample per condition, prompt cache/order
and missing second-stage composition cost limit the comparison. Private
comparison-review.json and comparison-measurements.json retain the audit.


## Explicit alternative candidates

`download-model.py --candidate candidate-qwen35-4b.json` downloads a separately
pinned Qwen3.5-4B Q5_K_M evaluation candidate into its own model directory. The
base model is official Qwen; this GGUF is published by Unsloth. The 3,143,656,608
bytes and SHA-256 are pinned from publisher metadata. Preserve the original
14B candidate and weights. Nothing changes the default runtime/model selection.

`run-batch.py --candidate candidate-qwen35-4b.json --run-dir PRIVATE_NEW_RUN
--cases PRIVATE_CASES --context 4096` explicitly selects that candidate. It checks
identity against the private verified manifest, records candidate.json in the
run, and supplies the distinct container path/alias to Compose. Existing global
locking, active-container refusal, resource limits and cleanup still apply.
Do not start a comparison until the previous generation container has stopped.
Text-only CPU evaluation uses the existing image and no vision projector/GPU.

`python3 -m unittest -v test_candidates` runs nine offline tests with synthetic
bytes: original/alternative path isolation, pinned metadata/path validation,
atomic valid/corrupt downloads, existing mismatch preservation and no duplicate
network work for valid weights, foreign-manifest preservation and recovery of
a missing manifest only after checking complete existing bytes. These establish
tooling behavior, not model fit or fidelity. Compile checks and both default/alternative Compose config checks
are separate from actual inference.

Sources checked 2026-10-20:
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/tree/e87f176479d0855a907a41277aca2f8ee7a09523
- https://github.com/ggml-org/llama.cpp/blob/31288c9c66e59377f7788d920678a565bb89dd37/src/llama-arch.cpp
- https://github.com/ggml-org/llama.cpp/blob/31288c9c66e59377f7788d920678a565bb89dd37/tools/server/README.md

The pinned runtime recognizes qwen35 and supports explicit reasoning off. These
are compatibility prerequisites, not proof that the quantization loads or that
it meets this task. Newer/smaller is not automatically better; use the same
private regression/holdout sources and review full workflow time and quality.
