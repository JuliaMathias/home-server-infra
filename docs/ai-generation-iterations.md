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

Result: all three requests completed in 944.80s, but all failed semantic
acceptance. The two regressions still introduce unsupported attribution or meaning;
the holdout invents a strategy to gain time/conditions, upgrades conjecture and
drops the main renunciation connection. Private review.json retains details.
Full-recording quality, original-note preservation and target time remain pending.

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

## Iteration 4: explicit smaller-model comparison

Run: `/srv/lara/ai/data/evaluations/grounded-notes-qwen35-4b-20261020T2019Z`.
Same cases as iteration3, explicit Qwen3.5-4B Q5_K_M CPU candidate. Downloaded
3,143,656,608 bytes passed pinned SHA-256; actual loading/inference succeeded.
All three requests completed in 234.24s, including 5.28s load/readiness. The
first request decoded about 9.24 tokens/s. All three still failed semantic
acceptance: actor swaps, omitted major points, future changed to past, and a
First Kings/Luke reference conflation. The style example contaminated wording.
Speed is promising but no accepted workflow/model switch follows. Remove that
example and evaluate a different task decomposition. Private review.json saved.

## Iteration 5: per-block evidence then organization

Extraction run: `/srv/lara/ai/data/evaluations/evidence-workflow-iteration5-20261020T2027Z`.
Require an entry for each block, nearby source context and literal supporting
quotes. Organization may only group immutable notes, not rewrite their facts.
Four private fixtures include a new car analogy. One supplied human correction
restores a later-time qualifier in T094; raw text and provenance are preserved.
This is a test fixture edit, not a reusable application correction importer.

Result: rejected and intentionally cancelled after a known fidelity/evidence
failure (2 requests had completed). Quotes crossed block boundaries,
and notes still invented attribution. The interrupted HTTP request is operator
cancellation, not OOM or a spontaneous crash. Grouping followup did not run.
The private review and cancellation metadata remain intact.

## Iteration 6: bounded thinking on identical evidence tasks

Run: `/srv/lara/ai/data/evaluations/evidence-workflow-iteration6-20261020T2035Z`.
Same sources/schema and 1536 total-response ceiling; Qwen3.5-4B with reasoning
on and a 256-token thinking allowance. Reasoning was present in responses;
completion-token usage includes reasoning, not just visible notes.
All four requests completed in 574.91s, including readiness, but failed
fidelity/evidence/style checks: actor swaps, invented meaning from corrupted
speech, cross-block/modified quotes, and verbatim copying. Required object keys
were present, which did not establish substantive coverage or support.
Private review.json lists every case. Prepared followup6 was NOT launched because
literal and semantic gates failed. Do not restart it automatically.

## Iteration 7: separate source critic

Run: `/srv/lara/ai/data/evaluations/critic-iteration7-20261021T0010Z`.
Hypothesis: separating source verification from drafting may expose unsupported
claims without the pressure to generate polished prose. Two known-bad drafts,
all paragraphs checked against contextual sources; 512-token bounded thinking,
1536 total-response ceiling. The private expected-error checklist is excluded
from the request. The critic must flag errors, not receive their answers.
Result: both finished in 239.37s including readiness. The critic caught one
unsupported term and flagged a reference problem, but falsely accepted critical
actor swaps, conjecture as fact and future contacts as completed events. Its
reference explanation was itself imprecise. Private review.json records misses;
do not use these verdicts as an automatic acceptance gate.

## Iteration 8: existing larger-model critic

Run: `/srv/lara/ai/data/evaluations/critic-iteration8-14b-20261021T0017Z`.
One identical agency critic case from iteration7, existing Qwen3-14B weights,
512-token reasoning allowance and 1536 total-response ceiling. This isolates
model selection on that case; no answers supplied or new weights downloaded.
Result: request completed in 392.09s, plus 10.31s readiness. It accepted all
nine paragraphs, including reversed actors, invented method and future contacts
changed to past facts. Private review.json and measurements.json retain evidence.
Do not use either tested critic as an automatic gate or run more of this critic
configuration merely to accumulate failures. Sampled CPU package peak 84 C;
package throttle increment 6 counted once, not summed across logical threads.
Docker CLI peak 2.101 GiB excludes inactive cache; GPU readings are background.

## Iteration 9: source-first event representation

Run: `/srv/lara/ai/data/evaluations/events-iteration9-20261021T0040Z`.
Hypothesis: explicit subject/action/object/time/modality fields may retain agency
and certainty before prose generation. Two source-only regression tasks use
existing Qwen3.5-4B, reasoning off, 4096 context and 1536 response ceiling.
Bad drafts and answer rubrics are excluded. Unresolved references must remain
uncertain. This is intermediate extraction, not final enhanced notes or an unseen
holdout. State: running; review actual roles, uncertainty, coverage and unsupported
additions before any composition stage. Full-workflow quality/time remain unmet.

## Delivery plan

Adjustments: full-recording quality/time now gates PR finalization; record each
iteration here, with failures preserved. Smaller-model or resource experiments
remain options only if current workflow cannot meet both gates. Do not lower
quality or silently shorten the requested output to claim speed. Keep the issue
as the tracked task; this file records evidence, not a competing app backlog.
