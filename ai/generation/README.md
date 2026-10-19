# Shared generation evaluation preparation

This is an evaluation harness, not a deployed inference service or a selected
production model. The first candidate is Qwen3-14B Q5_K_M through llama.cpp.
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
No candidate quality, generation speed, or sustained thermal result is claimed.
