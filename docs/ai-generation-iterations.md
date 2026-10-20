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

State: running. Do not promote partial outcomes to acceptance. Later gates pending.

## Delivery plan

Adjustments: full-recording quality/time now gates PR finalization; record each
iteration here, with failures preserved. Smaller-model or resource experiments
remain options only if current workflow cannot meet both gates. Do not lower
quality or silently shorten the requested output to claim speed. Keep the issue
as the tracked task; this file records evidence, not a competing app backlog.
