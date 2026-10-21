# Manual AI generation acceptance review

Manual review is required: valid JSON, known source IDs and a normal runtime stop
do not establish that notes preserve source meaning or cover the material.
This procedure reviews private evaluation evidence; it does not implement Notey.

## Prerequisites and exact test data

- Access Lara as the existing SSH user and read current `AGENTS.md`, status and
  iteration log in `/srv/lara/infrastructure`. Use the issue9 branch's latest
  documented revision. No credentials belong in this document or the evidence.
- Review privately, outside the shared tmux display. Source/output text stays
  outside Git. The user has authorized necessary selected text in tool history.
- First 9B control: `/srv/lara/ai/data/evaluations/qwen35-9b-control-20261021T1537Z`.
- Thinking-off comparison: `/srv/lara/ai/data/evaluations/qwen35-9b-off-control-20261021T1615Z`.
- Unconstrained comparison: `/srv/lara/ai/data/evaluations/qwen35-9b-no-grammar-20261021T1619Z`.
- English diagnostic: `/srv/lara/ai/data/evaluations/qwen35-9b-english-control-20261021T1623Z`.
- Conservative profile: `/srv/lara/ai/data/evaluations/qwen35-9b-conservative-control-20261021T1627Z`.
- Extended thinking: `/srv/lara/ai/data/evaluations/qwen35-9b-headroom-control-20261021T1633Z`.
- Each contains `cases.json`, `rubric.json`, `noisy_control.json`, `status.json`,
  `sampling.json`, runtime configuration, logs and telemetry. An active run may
  not yet have its response. Never restart it or create another job for review.
- Case ID `noisy_control` uses fictional blocks S1-S6. Expected facts remain in
  the private rubric and must never be inserted into model requests.

## Read-only procedure

1. Connect in a private terminal with `ssh lara`. Set `RUN` to one exact directory
   above. Run `cat "$RUN/status.json"`. If it is preparing/generating, leave it
   alone and await its existing monitor. Only review a saved completed/failed run.
2. Run `less "$RUN/cases.json"`, then `less "$RUN/rubric.json"`. Read every source
   block and its required facts before the output. Distinguish source ambiguity
   from a model's unsupported interpretation. Do not edit source or rubric.
3. Run `less "$RUN/noisy_control.json"`. Check the actual request/model/settings,
   `finish_reason`, token usage and visible notes. Confirm all source blocks and
   substantive propositions are represented. An output that ends mid-sentence,
   omits later blocks or reverses a qualifier fails even with `stop` and valid JSON.
4. Check each claim against its cited source: actor/recipient, chronology,
   possibility versus fact, negation, conditions, numbers and quotations. Record
   unsupported additions, omissions and false uncertainty. Identify exact output
   locations privately. Do not silently repair errors to call the output passed.
5. Compare `slots-1.json` (when captured) with `sampling.json` and the request.
   Read `runtime-config.yaml`, `server.log` and `telemetry.jsonl`; use a saved
   `measurements.json` when available. Record load and request times separately.
   GPU values are background during CPU-only trials. Docker CLI memory excludes
   inactive file cache. Count duplicated CPU package counters once, not their sum;
   increments are events, not throttled seconds. Sampling may miss spikes.
6. Save `review.json` privately with passed/failed gates, actual observations,
   evidence paths, reviewer/time and limitations. Update the nonprivate iteration
   log/status and draft PR without source/output text. Preserve raw results.

## Pass/fail, evidence and cleanup

All predeclared substantive facts must be covered without unsupported additions,
actor/time/negation mistakes, altered quotations or false certainty. A structural
failure also fails the gate. A synthetic pass permits the next bounded regression;
it does not accept sermon notes, a new holdout, or a complete 30-minute workflow.
The latter requires all inference stages timed and full-source/original-note and
citation coverage reviewed against private fixtures.

Record revision, model hash, actual run paths/settings, timings, every gate's
status, measurement limitations and reviewer/time. No screenshots or private text
in Git. No deletion is required for read-only review: exit `less` and SSH. Retain
all originals and failed outputs. The batch runner stops only its temporary
trial container; never stop Whisper or remove other data as review cleanup.

## Execution status

- First 9B control: assistant reviewed 2026-10-21, failed semantic coverage/negation;
  `review.json` and `measurements.json` retained in that run directory.
- Thinking-off comparison: assistant reviewed 2026-10-21, failed unsupported
  relationships and causes; private review.json retained.
- Unconstrained comparison: assistant reviewed 2026-10-21; failed format and
  semantic review. Raw code-fenced response and private review.json retained.
- English diagnostic: assistant reviewed 2026-10-21, failed roles, negation and
  unsupported additions. No production translation workflow follows.
- Conservative profile: assistant reviewed 2026-10-21, failed identity, dates
  and qualifiers. Private review saved; no sermon regression.
- Extended thinking: running at introduction; inspect actual state. More response
  allowance is not evidence of accuracy or a full-workflow time result.
- Sermon regressions, new holdout and complete-workflow acceptance: not passed.
  See the maintained iteration log for later evidence and current next action.
