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
holdout. Result: both completed in 228.91s including readiness; agency request
125.34s and kings request 98.16s. All events were incorrectly labeled negated.
Roles improved in places, but coverage, time, context exclusion and source
assignment failed. Explicit statements became invented unresolved questions.
Private review.json rejects this representation; no composition was launched.

## Iteration 10: minimal note schema with longer reasoning

Run: `/srv/lara/ai/data/evaluations/minimal-notes-iteration10-20261021T0111Z`.
Two identical regression sources, existing 4B model, reasoning allowance 1024,
2048 total response and 4096 context. One notes string allows normal Markdown
organization instead of many constrained evidence/event fields. No drafts, gold
answers or synthetic style examples are supplied. This changes representation
and reasoning budget together; it is not an isolated causal comparison.
Result: both completed in 400.83s including readiness (188.35s agency,
206.99s kings). More readable headings did not fix meaning: changed speaker
roles, future plans changed to past, possible location made certain and invented
model-following remained. Corrupt speech/quotation was copied into finished notes.
Private review.json records positive and failed points; measurements.json retains
resource evidence. No full-recording run is justified by this outcome.

## Iteration 11: controlled source-noise diagnostic

Run: `/srv/lara/ai/data/evaluations/source-noise-control-iteration11-20261021T0141Z`.
Two fictional accounts carry the same intended facts in clean and deliberately
noisy language. Both contain attribution, chronology, conjecture, future plans,
negation and voluntary choice. Expected facts are in private rubric.json only,
not the requests. Existing4B, reasoning1024, total2048, minimal notes schema.
Hypothesis: distinguish basic instruction/runtime limitations from sensitivity to
noisy source language before another model comparison. Clean goes first: cache,
order and single-sample limitations prevent a causal performance claim.
Result: both finished in 338.01s including readiness (clean160.61s,
noisy172.09s). Clean retained most facts but invented the narrator accepting a
proposal she herself explained; noisy introduced several actor, date, negation
and meaning errors. Private review.json records each failure. Neither passes.
Noise sensitivity is plausible but does not fully explain the errors; two samples
do not establish a causal or statistical model-quality result.

## Iteration 12: publisher-recommended sampling control

Run: `/srv/lara/ai/data/evaluations/sampling-control-iteration12-20261021T0212Z`.
Inspection found earlier runs explicitly used temperature0.7/top_p0.8; remaining
samplers inherited runtime defaults. The official model card recommends a
different general-thinking profile: temperature1.0, top_p0.95, top_k20, min_p0,
presence_penalty1.5 and repetition penalty1.0. Test that whole profile on the
identical two synthetic cases with unchanged seed, thinking/context/output bounds.
A private wrapper mutates and records actual request settings using the canonical
harness; it leaves tracked/deployed defaults unchanged. Offline wrapper checks
passed for payload updates, seed retention and unaffected preflight. Resolved slot
parameters are saved when the runtime exposes them, with failures recorded.
Result: both completed in 340.65s (clean174.55s, noisy160.78s). Saved slot
parameters confirm the entire requested profile was applied. Clean passes the
predeclared factual control rubric, with awkward/misplaced headings still noted;
noisy fails metaphor/actor, date, delay and refusal meanings. Private review.json
records both. This supports another source-handling diagnostic, not a claim that
sampling alone caused improvement or that sermon notes are accepted. Single
sample/order/cache limitations remain; no weights or deployed defaults changed.

Primary sources checked 2026-10-20:
- https://huggingface.co/Qwen/Qwen3.5-4B#best-practices
- https://github.com/ggml-org/llama.cpp/blob/31288c9c66e59377f7788d920678a565bb89dd37/tools/server/README.md

## Iteration 13: conservative transcript normalization

Run: `/srv/lara/ai/data/evaluations/normalization-iteration13-20261021T0241Z`.
Hypothesis: punctuation and conservative cleanup before note composition may
improve interpretation of noisy text. Three tasks: synthetic noisy control and
the same agency/kings regression sources. Existing4B with recommended sampling,
reasoning512, total2048, context4096. First-person narration, all substantive
content, numbers, modal qualifiers and source boundaries must be preserved.
Unclear spans remain verbatim with separate uncertainty flags; no external
knowledge or expected answers. Original sources remain unchanged outside Git.
Result: all three completed in 435.28s including readiness (101.37s synthetic,
146.34s agency, 182.18s kings). Reject automatic composition inputs: kings lost
all source IDs and introduced a typo in quoted wording; agency lost the explicit
context/target boundary; synthetic punctuation did not preserve the important
supervisor/refusal boundary clearly. Uncertainty flags missed hard ambiguities
and added speculation. Private review.json records details; no composition ran.

## Next model comparison: authorized preparation

Prepared metadata and plan:
`/srv/lara/ai/data/evaluations/qwen35-9b-proposal-20261021T0310Z`.
Qwen3.5-9B Q5_K_M, publisher Unsloth, 6,577,841,376 bytes; revision
`3885219b6810b007914f3a7950a8d1b469d598a5`, SHA-256
`dc2a39aef291f91a9116ad214058da0d86eb648743a124bd8c333787c4b9c91c`.
Candidate metadata passes the existing safe-path/pin validator. No weights were
downloaded at proposal time. The user subsequently said "please continue" after
the explicit download/evaluation question on 2026-10-21, authorizing this candidate.
The original proposal is preserved; authorization evidence is recorded privately.

Rationale: repeated role/time failures survived representation, thinking, critic,
sampling and conservative-cleanup experiments. A distinct model comparison is
more informative than replaying those failed configurations. First gate: only
the identical noisy synthetic control, then semantic review before two sermon
regressions. New holdout and full-workflow quality/time still follow only if valid.
Use a separate model directory, existing CPU/private runtime and 16GiB/four-thread
limits; no default/deployed switch. About 240 GB disk was free at inspection.
The 6.58 GB weights are smaller than the existing 10.51 GB 14B; memory fit is plausible,
not measured. Quality/speed/30-minute suitability remain unknown.

Primary sources checked 2026-10-21:
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/tree/3885219b6810b007914f3a7950a8d1b469d598a5

## Iteration 14: authorized 9B noisy-source control

Preparation: `/srv/lara/ai/data/evaluations/qwen35-9b-preparation-20261021T1537Z`.
Single control: `/srv/lara/ai/data/evaluations/qwen35-9b-control-20261021T1537Z`.
One coordinator downloads the exact pinned candidate, verifies full size/hash,
and then starts only the noisy synthetic control. It does not queue sermon
regressions. Existing runtime/container locks still prevent duplicate inference.
The noisy control, seed 42, context 4096, total 2048, reasoning 1024 and recommended
sampling match iteration12; model selection is the intended difference. Actual
slot settings and raw responses remain private. Download size/hash verified and
actual 9B loading succeeded. Readiness 11.09s, request 225.75s, decode 5.72tokens/s.
The response failed: valid JSON/stop but ends mid-sentence in S2, omits S3-S6 and
reverses an explicit negation. 1234 completion tokens of 2048, runtime truncated=0;
this is semantic early completion, not an output-limit failure. Private review.json
and measurements.json preserve evidence. Package mean/peak 75.2/81 C, throttle
delta 0 counted once, Docker CLI peak 6.191 GiB excludes inactive cache, host available minimum 18.49 GiB;
GPU 47-60 C is background. A short CPU load is not sustained full-workflow acceptance.
The pinned recipe is tracked as `ai/generation/candidate-qwen35-9b.json`;
weights stay outside Git. Default model, service deployment and network unchanged.

## Iteration 15: identical 9B control without thinking

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-off-control-20261021T1615Z`.
Only reasoning changes from on1024 to off/effective0; case/messages/schema,
sampling profile, seed42, context4096 and response2048 remain identical. This
checks whether the bounded thinking mode contributed to early semantic completion.
One sample/mode, token-allocation and cache effects limit conclusions. No download
or model/default switch. Result: 108.31s request, all six blocks represented,
but invents employment/relationships, extends refusal to supervisors and turns
the wrong-fuel analogy into a reason for refusal. Private review.json rejects it;
no sermon regressions follow. Faster completion does not meet the quality gate.
Manual review is required; see `ai-generation-review.md` for exact fixtures,
read-only actions, gates, evidence and cleanup. Full-workflow gates remain unmet.

## Iteration 16: remove only the runtime JSON constraint

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-no-grammar-20261021T1619Z`.
Same 9B/off/case/messages/sampling/context/output and seed; remove only
`response_format` from the actual request. The prompt still asks JSON. A private
wrapper records the actual unconstrained request and raw response; it does not
wrap/repair model output. Invalid JSON remains a failed record for separate
semantic inspection. Offline assertions verify removed grammar, unchanged seed
and untouched preflight. This tests a runtime interaction hypothesis, not an
assertion that the runtime has a bug. Result: 87.26s; raw response uses code fences
and a notes array, failing JSON parsing. Source review ALSO fails person identity,
previous familiarity negation and conjecture. Raw response preserved; no wrapping
or silent repair. Removing grammar did not eliminate critical errors. One sample
and cache effects limit conclusions; no upstream-bug claim follows.

## Iteration 17: English source sensitivity control

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-english-control-20261021T1623Z`.
Same existing 9B/off/profile/seed/context/output/schema as15; instructions/source
rendered in English with the same intended fictional facts and informal style.
Expected-fact rubric remains private and excluded from requests. This investigates
language sensitivity before another Portuguese prompt variant. Human-authored
translation changes wording/prepositions too: not a token-level minimal pair or
a definitive language-causality test. Result: 94.11s, failed narrator/visitor
roles, invented sequence, explicit not-yet contact changed to uncertainty and
unsupported supervisor refusal. Private review.json saved. English did not
eliminate the failures; no production translation workflow follows.

## Iteration 18: conservative sampling on the identical PT source

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-conservative-control-20261021T1627Z`.
Same 9B/off/case/messages/schema/context/output/seed as15; temperature1->0.2 and
presence penalty1.5->0, other sampling unchanged. Hypothesis: reduce variation
and avoid discouraging reuse of factual names/words. This profile changes two
parameters together, not an isolated causal test. Repetition/copying and the
original factual gates remain checked; lower randomness does not guarantee
accuracy.
Result: 113.10s, failed identity, hiring chronology, not-said versus not-known
and unsupported supervisor refusal. Private review.json saved. Reduced variation
did not pass the original gate; no new weights/default/deployment.

## Iteration 19: larger bounded thinking and response allowance

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-headroom-control-20261021T1633Z`.
Same case/messages/schema/seed/sampling as14; thinking1024->2048, totalresponse
2048->4096 and context4096->8192. This tests whether more reasoning/answer room
helps; direct reasoning-budget exhaustion was not established. Three bounds
change together and one sample/cache effects limit conclusions. CPU4threads,
16GiB and private/noGPU limits remain unchanged. Result: 487.30s request, 2601
completion tokens of 4096, normal stop. It still invents a different person, changes
unknown organization into unknown routine, changes prior routine familiarity
into knowing a person and extends refusal to supervisors. Private review.json
rejects it; larger bounds did not pass the unchanged gate. Whole-trial sampling
CPU package mean/peak was 78.99/83 C, with zero package-counter increment counted
once. Docker CLI peak 0.631 GiB excludes inactive file cache and is not full
resident model memory. Host available RAM minimum 18.32 GiB; background GPU 50-60 C.
The 82 samples include startup and may miss spikes. Measurements
and raw outputs remain private; no full-workflow speed estimate follows.

Generic harness now validates finite integer response bounds 128-4096 before any
model work, retains per-case default 2048 and sets the temporary runtime ceiling
to the maximum validated case allowance. Existing 128/768/1536/2048 bounds and
new 4096 acceptance plus invalid/unbounded/noninteger rejection are covered by
three added tests. All 16 offline tests, compile, default/extended Compose and
whitespace checks passed. This is tooling evidence, not a model-quality pass.
Full-workflow fidelity, unseen passage and actual all-stage time remain unmet.

## Iteration 20: clean-source 9B factual sanity

Run: `/srv/lara/ai/data/evaluations/qwen35-9b-clean-sanity-20261021T1647Z`.
Use the previously prepared clean_control source version with the same intended
facts, instead of noisy_control. Instructions, schema, model and sampling match
iteration19, with seed42, thinking2048, response4096 and context8192. This establishes a clean-source capability
baseline rather than further tuning one noisy case. Human wording changes
ambiguity too, not a token-level minimal pair. Private expected rubric is not
supplied to the model. State: running, one control only. A clean pass would not
erase failed noisy robustness or accept PT sermon/full-workflow quality; use it
to select a distinct source-handling or representative-input diagnostic.
No new model/download/default/deployment; all acceptance gates remain unmet.
Result: 394.01s request (430 prompt tokens at 38.6 tokens/s, 2120 completion
tokens at 5.5 tokens/s), valid JSON, normal stop. Visible notes cover only S1;
S2-S6 are absent, so eight of nine rubric facts are missing. Even a clean,
already note-like source fails coverage with bounded thinking on. Private
review.json saved.

## Pivot: workflow redesign (2026-10-21)

The user reviewed iterations 1-20 with a second assistant (Claude) and stopped
single-sample prompt, sampling and thinking micro-tuning. Twenty iterations varied
those settings but never changed the three factors that dominate the outcome:

1. Model capability: 4-14B dense models produce actor, tense and negation errors
   when paraphrasing noisy Portuguese, and fail to catch them as critics.
2. Request shape: large source blocks in, one polished answer out, with no
   per-paragraph link back to the exact source sentences it relies on.
3. Hardware use: `compose.yaml` runs the CPU-only image with zero GPU layers.
   Prompt reading at roughly 16-39 tokens/s makes a ~15k-token sermon cost about
   ten minutes per full pass before any writing.

Confirmed requirements (user, 2026-10-21): real enhanced notes in the user's own
style, integrating handwritten notes when present and fully generated from the
transcript otherwise; not headings only and not reformatted transcript; local
generation on Lara only; Notey's review/edit step is the safety net, so the goal
is few errors that are clearly flagged.

Workflow under evaluation (prototype here; Notey owns the production version):

1. Plan: label non-sermon spans (kept as proposed exclusions, never deleted, edge
   cases flagged), split the sermon into real sections with sentence IDs, and
   build a short sermon map of section titles and main points.
2. Write: enhanced prose one section at a time, in order, with the sermon map,
   the notes already written for earlier sections (verbatim while they fit,
   else previous section plus a digest), that section's corrected source
   sentences, the matching handwritten notes, a short excerpt of the user's own
   enhanced notes as style reference, and Bible passages from the fixture
   database. Every paragraph returns its source sentence IDs.
3. Whole-sermon review: one long-context pass over the draft, the map and the
   full sermon transcript proposes missing points, cross-section connections and
   merges, each with source IDs, inserted as visibly marked additions.
4. Deterministic checks of each paragraph against its cited sentences
   (negations, names/numbers/dates, Bible references, verbatim quotations,
   future/past markers); one targeted rewrite, then flag for review.

Runtime/model changes evaluated first: GPU-offloaded llama.cpp with Whisper
stopped during generation, then a mixture-of-experts candidate (download needs
separate user approval). Evaluation uses one fixed case set with private
checklists and changes one factor at a time. See `ai-status.md` for state.

## Redesigned workflow runs (2026-10-21)

Private prototype, reference checklist (confirmed by the user) and run outputs:
`/srv/lara/ai/data/evaluations/notes-workflow-20261021`. Reader copies are in
the user's private Drive folder. All runs: Qwen3.6-35B-A3B UD-IQ4_XS, GPU auto
(llama.cpp `--fit`, about 2.7 GiB VRAM), 22 GiB RAM cap, 32k context, reasoning
off, temperature 0.4, seed 42, Whisper stopped and restarted healthy.

GPU speed baseline (identical old section request, one sample each): 14B CPU
1042 s, 14B GPU 821 s, 9B GPU 340 s. Partial offload speeds prompt reading
4-7x but not decoding. The 35B mixture-of-experts model decodes about 8-12
tokens/s and reads about 83 tokens/s in this setup.

A first 9B workflow attempt failed in planning: it labelled the whole opening
testimony as non-sermon, split sections at almost every block and added Bible
passages that were never mentioned. Boundaries now ask only for the start block
and the closing structure; sections are capped per window; code drops references
whose book is not spoken nearby.

Run 1 (66 min: plan 9, write 45, review 11). Boundaries matched the confirmed
reference exactly; all four handwritten notes kept the user's wording; the
agency, negation and judgement errors that defeated iterations 1-20 were
correct. Failed: two people in one late story merged into one (holdout section),
roles inverted in an illustration, a figurative phrase read literally, one
teaching point omitted, two outside-knowledge expansions. The free-form review
pass added commentary in the wrong sections. Every section was rewritten because
most check flags were false positives. CPU package mean 80.4 C but peak 100 C
(TjMax) and a package throttle-counter increase of about 55,800 (counted once),
far above CPU-only runs; the laptop's shared cooling is the likely cause.

Run 2 (35 min: plan 7.5, write 23, review 4). Changes: sections capped at 12
blocks; explicit multi-person story rule; checks recalibrated (hard flags only
for non-literal quotes, invalid sources, and names/numbers absent from the whole
sermon; negation heuristic reported only); review pass may only name gaps with
block IDs, code rejects gaps whose blocks are already cited and writes accepted
ones with the normal rules; prompt order made cache-friendly; each NAA passage
inserted once. Result: outside-knowledge names gone, omitted point restored,
4 of 17 sections rewritten. Still failing: the merged-people story (its key
relationship is garbled in the ASR text itself), an illustration's roles, the
appeal attributed to the preacher, two handwritten notes paraphrased instead of
kept. All six review-pass items were rejected as already cited.

Run 3 (39 min: plan 7.5, write 27, review 4.3). Changes: user-confirmed
boundaries and speaker labels as input (Notey's review step precedes generation
in the product flow); confirmed spans as their own sections; a per-section cast
list (who did what) emitted before the prose; handwritten notes inserted
verbatim when the wording was not kept; NAA passages only for references
confirmed as spoken. 15 offline tests cover the deterministic parts. Result: the
appeal is correctly attributed to the other speaker and the closing prayer is
brief; one note was inserted verbatim by the guarantee; no hard flags remained.
Regressed: a figurative "another [preacher's name]" (a changed person) became a
separate person, and the cast list reinforced it. Still failing in all three
runs: the merged-people ending of the holdout story. That passage comes from the
better-microphone recording and its key relationship is garbled by speech
recognition, so the error originates in the transcript. Other moderate errors
remain (who invited whom in an illustration, a figurative phrase read
literally, one tense). All six review-pass items were again rejected as already
cited, so the long-context review currently adds time (about 4 minutes) without
changing the notes.

Run 4 (55 min: plan 7.4, write 41, review 6.3), after user style feedback:
the notes read as a retelling ("the preacher said"), carried transcript IDs and
times, and did not use the preacher's name. Changes: style example replaced by
the user's own before/after notebook pages (handwritten session notes, her
enhanced version of the same session, and a second enhanced session); rules to
state teachings directly, name the speaker only for testimony, and never write
IDs or tool vocabulary; the user's handwritten notes always kept verbatim as
the section's first bullets (her pattern in the first session; the second
session reworded her bullets, deliberately not followed for fidelity); preacher
name/title/date from confirmed metadata; a clean reader rendering ("@ speaker -
title", "→" topics, bullets, NAA blocks) separate from the review rendering.
Result: the tone moved clearly toward the user's style. The model wrote block
IDs inside the text in Bible-marker syntax, which the checks read as invalid
references, forcing rewrites in 14 of 17 sections; those rewrites added
duplicates and a new merged-people error in the longest section. A mechanical
cleanup (IDs moved to sources, embedded bullets split, header-only lines dropped)
now runs before the checks, with a test; run 4 was re-rendered with it offline.
Persisting errors: the same multi-person stories, a figurative "another
[name]", a transcription filler word ("so-and-so") treated as a name, and one
Bible quotation written from memory.

Run 5, cloud comparison (2026-10-21, user explicitly approved sending this
sermon's transcript and notes to Anthropic once; issue #19). Recipe for a
frontier model: one request with the whole sermon (130 blocks after confirmed
exclusions, speaker labels, the four handwritten notes, the same before/after
style example and rules, schema-constrained JSON). Run with the unmodified
Claude Code CLI on the user's Pro plan, safe mode, all tools disabled, no saved
session, from an empty folder; the prompt streamed from Lara and the result
streamed back, so no private file was stored on the Mac. Result: 41 s wall time
(Claude Sonnet 5.5, CLI cost estimate USD 0.18, which a subscription counts
against usage limits rather than billing). Against the confirmed checklist:
the two-people ending, the illustration roles, the appeal attribution and every
agency/negation point were correct; it flagged the garbled two-people passage
and the confusing opening as uncertain instead of guessing; style matched the
user's notebook closely; zero hard check flags; 124 of 130 blocks cited. Defects:
three handwritten notes were reworded or extended (corrected in code by
inserting them verbatim, as the local recipe already does); four references the
preacher alluded to without naming the book were kept as citations without
inserted text. Private outputs: `run5-claude-cli-pro/` in the run directory.
One sample, one sermon: not yet evidence of reliability across recordings.

Assessment after three runs: the workflow reliably gets boundaries, Bible
passages, the user's notes and most agency/negation points right in 35-39
minutes, a large improvement over iterations 1-20. It does not yet meet the
"no unflagged critical error" gate: errors cluster in multi-person stories,
especially where the transcript itself is garbled, and run-to-run variation can
flip a previously correct reading. Next decisions are the user's (see status).

## Delivery plan

Adjustments (2026-10-21 pivot): micro-tuning stopped; all 9B controls rejected,
including the clean-source sanity check. Next, in order: GPU runtime and speed
measurement on existing weights; mixture-of-experts candidate proposal (user
approval before download); fixed evaluation set with user-skimmed checklists;
four-stage workflow prototype; full-sermon end-to-end run timed against the
around-30-minute target and read by the user. Full-recording quality/time still
gates PR finalization. Do not lower quality or silently shorten output to claim
speed. Keep the issue as the tracked task; this file records evidence, not a
competing app backlog.
