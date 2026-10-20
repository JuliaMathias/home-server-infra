# AI ownership and model lifecycle

## Decision and rationale

Confirmed by the user on 2026-10-19: this project/chat owns only the shared AI
layer. Notey owns the study-notes application at
`/Users/thejuliamathias/Projects/Personal/notey` (chat `01a156d6-5e5a-7433-9427-bd26eb13ed7e`).
This clarifies the existing architecture and supersedes the earlier plan for
this chat to complete a production sermon document or a Bible importer. Existing
requirements/evidence remain preserved; no private assets are deleted or moved.

A model service returns capabilities and evidence. An application decides how to
use them. This keeps one inference runtime reusable across unrelated products.

| Shared AI layer | Consuming application / Notey |
| --- | --- |
| Speech-to-text, generic extraction and text inference | Sermon/book/verse records, translation choices and imports |
| Technical jobs, errors, timestamps, model provenance | Domain prompts, source precedence and user corrections |
| Resource limits, load/unload, hardware/runtime compatibility | Workflow orchestration, semantic boundaries and speaker identity |
| Model fidelity/format/resource evaluations on private fixtures | Bible retrieval, completeness policy and review UI |
| Documented private capability interfaces | Note integration, PDF/.note exports and application acceptance |

Do not promote test-data storage or a prototype schema into the application's
production architecture. Notey chooses its own database and migration strategy.
Generic OCR/PDF extraction may be a shared capability, while interpreting extracted
text as Bible books/chapters/verses remains application logic.

## Existing evaluation handoff pointers

All paths below are on Lara and outside Git. They are test artifacts, not deployed
application services. No ownership transfer or automatic data migration occurred.

- Full-recording batch: `/srv/lara/ai/data/evaluations/full-sermon-notes-20261020T0052Z`.
  `status.json` reports technical state; `section_XX.json` retains requests/results;
  `cases.json`, `source-plan.json` and `source-blocks.json` retain fixture mapping.
  Structured validity and source IDs do not establish factual entailment or semantic
  completeness. Offsets between microphones are approximate.
- Original short model trial: `/srv/lara/ai/data/evaluations/generation-20261019T2340Z`.
  `review.json` / `evaluation-report.md` distinguish runtime success from quality.
- Selected private source fixtures: `/srv/lara/ai/data/study-notes/sermon-20261017/sources`.
  Integrity metadata is in `source-manifest.json`; original notes and test inputs
  remain unchanged. `handwritten-notes.json` is an assistant visual transcription,
  not a separately user-verified OCR dataset. `passages.json` retains PDF provenance.
- Prototype verse fixture: `/srv/lara/ai/data/study-notes/bible-passages.sqlite3`.
  Contains 54 checked verses across 17 selected ranges, explicitly a partial import.
  `editions` records source hash/scope; `verses` keys translation/book/chapter/verse
  and stores PDF-page provenance; `passage_ranges` records ranges/reference status.
  This is not a validated complete Bible, reusable importer or required Notey schema.

Notey must implement repeatable import validation, translation/book identity,
correction precedence, source-grounded composition, explicit ambiguity handling,
complete verse retrieval, content review and device/export verification. These
are integration pointers, not a second tracked application backlog here.

The transcription service is private on `lara-backend` at `http://transcription:8000`;
see its README for upload/status/result contracts and limits. The generation
container is currently a CPU evaluation runtime that stops after each run, not a
stable deployed production API or an application-ready asynchronous contract.

## Monthly model review

Scheduled in this chat: **first day of each month, 09:00 America/Sao_Paulo**.
Automation ID: `review-local-ai-model-candidates-monthly`.

1. Read current inventory, baselines, requirements and measured hardware before
   comparing models. Last verified hardware: i7-11370H, 32 GB RAM, 4 GB RTX 3050
   Laptop VRAM. Whisper Large V3 is the transcription baseline; Qwen3-14B Q5_K_M
   is a generation trial candidate, not a final production choice.
2. Research official model cards/releases/runtime documentation. Record exact
   model/revision/date, license, supported quantization and runtime compatibility.
3. Consider quality and efficiency together: Portuguese/English recognition,
   factual fidelity, structured output, context needs and extraction capability.
   Budget full weights, KV/context/runtime overhead and concurrent workloads.
   MoE active parameters are not the total model-memory requirement.
4. Distinguish vendor claims, estimates and measurements on Lara. Recommend a
   controlled comparison only for a credible material improvement. Use identical
   inputs and assess quality, elapsed time, memory and thermal behavior.
5. Do not automatically download, install, run heavy benchmarks, incur costs or
   switch deployments. Retain current baselines until separately authorized tests
   support a change. Save dated research outside Git under AI runtime data.

Notify for a credible improvement worth evaluating or an actionable failure.
Routine no-change reviews stay quiet; the monthly schedule remains active.

## Delivery sequencing and acceptance

The active finite generation monitor now reports AI evaluation evidence only and
stops after reporting. Application delivery is handled in Notey. Monthly review
is research, not an automatic upgrade pipeline. Repository changes follow an issue,
dedicated task branch and a PR left for the user to merge.

Adjusted dependencies: application document delivery no longer blocks an AI
model-evaluation report; application imports and production acceptance remain
visible in the consuming project. Outstanding AI limits include full-source
fidelity, longer-input stability, resource coordination and a production generation
contract. A schedule being active is not evidence that a future review ran.
