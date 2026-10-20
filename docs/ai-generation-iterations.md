# Generation workflow evaluation log

## Acceptance and scope

Confirmed 2026-10-20: iterate until source-grounded, organized enhanced notes
are credible in around 30 minutes after transcription for an hour-long sermon.
PR #10 remains draft until evidence supports quality and elapsed time. It is not
ready merely because a model runs or source-ID/JSON checks pass.

This is AI-layer evaluation on private fixtures. Notey owns production prompts,
correction/retrieval policy, workflows, user review and document exports. No new
model download, deployment switch or full-recording retry occurs incidentally.
Private prompts, sources, outputs and detailed rubric stay outside Git.

## Gates

1. Regression fixtures: all required propositions, correct agency/negation,
   ambiguity and no unsupported additions. Keep answer rubric out of prompts.
2. Unseen representative source: preserve argument, examples, verified references
   and correction/uncertainty distinctions, including later source blocks.
3. Full workflow: measure every inference stage, not extraction alone. Review
   full-recording coverage and representative factual support and note preservation;
   include private checked reference fixtures without model-memory quotations.
4. Actual elapsed time around 30 minutes, recorded resources/temperatures and
   limits. Do not extrapolate from tiny tests or imply exhaustive human accuracy.

## Iteration 1: prose versus compact extraction

Run: `/srv/lara/ai/data/evaluations/compact-comparison-20261020T1900Z`.
Four requests, 4096 context, 768 output ceiling, same pinned Qwen3-14B CPU runtime.
All requests completed; all four failed semantic acceptance. Compact output was
faster but omitted required facts; prose added unsupported interpretation. The
six-entry maximum may bias selection toward early facts. This is a test-design
confound, not proof that compact extraction intrinsically loses information.
See private comparison-review.json, comparison-measurements.json and rubric.json.

## Iteration 2: direct grounded notes with coverage instructions

Run: `/srv/lara/ai/data/evaluations/grounded-notes-iteration2-20261020T1951Z`.
Hypothesis: removing the six-entry ceiling and explicitly requiring all-block
coverage, correct attribution and uncertainty can fix the observed weaknesses
without adding another inference stage. Same two source fixtures; two requests,
4096 context, 1024 output ceiling; existing model, sampling and CPU limits.
Private cases.json contains the exact prompts; the answer rubric is not provided
to the model. Generic metaphor guidance is informed by the observed failure, so
this is a regression experiment; it must pass a new holdout before generalization.

Result: failed after 237.45s for the first request (622 output tokens). The
response copied source blocks nearly verbatim, with first-person narration and
ASR disfluency. IDs included timestamp suffixes, failing exact source validation;
the second task was not attempted. More explicit completeness instructions alone
did not yield usable enhanced notes. Private review.json records the failure.

## Iteration 3: constrained IDs and demonstrated paraphrase

Run: `/srv/lara/ai/data/evaluations/grounded-notes-iteration3-20261020T2007Z`.
Schema source-ID enum now prevents timestamp suffixes. A synthetic independent
example demonstrates third-person paraphrase while preserving agency; generic
fidelity instructions retain ambiguity, conditions and all substantive points.
Two regression fixtures and the prepared unseen narrative holdout are included.
Same model/sampling/CPU settings; 4096 context and 768 output ceiling per request.
The holdout answer rubric remains outside the request. No inference answers or
failed outputs were silently repaired. This changes multiple prompt/schema factors
and is an acceptance experiment, not an isolated causal benchmark.

State: running. Review actual outputs before another workflow claim. Full-recording
quality, supplied-note preservation and around-30-minute elapsed time remain pending.

## Alternative candidate preparation

Initial comparison runtime timings show about 16 input tokens/s and 2.5-2.7 output
tokens/s; iteration3's first request measured 23.27 and 3.06 respectively. This
motivates measuring both prompt and decoding cost, not assuming shorter output
alone meets the around-30-minute target. None is a whole-recording estimate.

Prepare Qwen3.5-4B Q5_K_M as a separate CPU comparison, preserving current 14B
weights/default. Official base card and third-party quant publisher metadata
are linked in the generation README. Quant file is 3.14 GB, pinned revision/hash;
actual load, resource fit and fidelity are pending. Existing image source supports
its architecture; this does not prove deployment fit. No GPU/Whisper changes.
The download is separate from inference; only one generation run is allowed.

Generic candidate selection is explicit in downloader and batch runner, with
nine offline behavioral tests (including manifest collision protection and
verified recovery after an interrupted manifest write). No production model
switch occurred. Compare identical private fixtures after iteration3 stops; do not discard negative results.

## Delivery plan

Adjustments: full-recording quality/time now gates PR finalization; record each
iteration here, with failures preserved. Smaller-model or resource experiments
remain options only if current workflow cannot meet both gates. Do not lower
quality or silently shorten the requested output to claim speed. Keep the issue
as the tracked task; this file records evidence, not a competing app backlog.
