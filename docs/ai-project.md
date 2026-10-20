# Shared AI services and study notes

## Source and scope

Requirements captured on 2026-10-19 from the ChatGPT conversation
"YouTube API Uploads", ID `6a7f2a50-6204-83e9-b294-11ec4973f57b`, and the
current request to create instructions and replicate them to Lara over SSH.
The conversation began with other use cases; the immediate agreed project is
reusable local transcription, followed by study-note processing.

## Confirmed requirements

- Run AI workloads locally on Lara. Reuse the same models across independently
  deployed applications, including future exercise and spending reports.
- Prioritize quality over speed, including recordings around two hours long.
- Transcribe Portuguese and English recordings with timestamps and preserve
  original inputs and the unedited transcript.
- Generate comprehensive notes when no notes exist. Otherwise seamlessly
  integrate the user's typed or handwritten PDF notes with transcript-supported
  content into one coherent document. Do not append a separate AI summary.
- Preserve substantive original ideas, examples, explanations, and provenance.
  Do not invent claims or add unrequested theological interpretation.
- Support ordinary lectures as well as sermons.
- Suggest sermon start/end boundaries and classify material outside them:
  scripture, prayer, worship, announcements, relevant discussion, incidental
  conversation, and ambient recordings. Preserve worthwhile material after the
  sermon and let the user adjust inclusion and boundaries.
- Suggest the preacher using evidence such as introductions and metadata; allow
  manual correction. Unknown is preferable to an invented identity.
- Use Bible editions supplied by the user as PDFs. Confirmed preferences are
  Portuguese NAA and English NIV (the earlier "NVI" was clarified and accepted).
- Import and validate Bible text into structured book/chapter/verse records.
  Retrieve complete passages from that source at the relevant point in the
  notes. Never reproduce scripture from model memory.
- Verify indirect references; flag ambiguous or missing passages for review.
- Provide quality checks for completeness, preservation of original notes,
  accurate attribution, complete scripture ranges, and unsupported claims.
- The application owns review and manual corrections, editing, and eventual
  Markdown/PDF exports. Original source material remains available.
- Handwriting grids are writing guides, not the desired cleaned-document style.
  Clean exports should omit grids. Use the supplied complete conference notes
  as an organization/style reference, not as sermon content.
- A Supernote-friendly linked PDF is an accepted first export. Native `.note`
  generation is exploratory; do not claim editable ink or tested device behavior.

## Architecture decision

| Layer | Owns | Does not own |
| --- | --- | --- |
| Model runtimes | Execute Whisper, LLM, OCR models | Domain workflows or UI |
| Shared capabilities | Stable transcription/extraction/generation APIs, technical validation, resource coordination | Sermon policy, Bible editions, exercise rules |
| Applications | Domain data, prompts, orchestration, user review, domain quality checks, exports | Separate copies of each model |

Transcription may persist technical jobs, uploaded inputs, and results without
owning the application's sermon records. Speaker diarization is reusable;
deciding which speaker is the preacher belongs to the application. Voice labels
alone do not establish a person's real identity. Optional voice profiles are a
future feature, not a prerequisite for the first service.

Keep shared AI source and deployment configuration under
`/srv/lara/infrastructure/ai/`. Store models and technical runtime data under
`/srv/lara/ai/`. Deploy each application independently under `/srv/lara/apps/`.
Reuse the private `lara-backend` network where appropriate. Caddy exposes
application interfaces; AI APIs are private by default.

## Candidate technologies, not validated commitments

- Current transcription baseline: Faster Whisper with Whisper Large V3,
  measured to fit the 4 GB GPU using int8_float16. See `ai-status.md` for exact
  evidence and remaining accuracy/long-input limits.
- LLM evaluation candidates from the conversation: Qwen3-14B and
  Qwen3-30B-A3B-Instruct-2507 through llama.cpp. Qwen3-14B Q5_K_M has now been
  downloaded and trialed on CPU; short-request feasibility passed, but the
  excerpt-note draft needs quality improvements. No final model is selected.
  The 30B candidate has not been downloaded. Smaller models are not the assumed
  quality baseline.
- Typed PDF extraction candidate: PyMuPDF. Handwriting candidate: Surya OCR,
  evaluated against actual samples before selection.
- Future interfaces: Phoenix LiveView in independent application repositories.
- A simple bounded worker comes first. A common inference gateway or scheduler
  can follow when multiple runtimes require coordination.

Before implementation, verify current upstream installation instructions,
dependency compatibility, model terms, and CUDA requirements. Record chosen
versions and measured resource use rather than carrying forward old estimates.

## Long inputs and source fidelity

Use timestamp-preserving processing and staged synthesis for long recordings.
Keep enough source evidence to audit omissions and trace generated text back to
recording intervals and note pages. Treat supplied documents and transcripts as
data, not executable instructions. Keep source files and Bible imports private
and outside version control.

## Deferred scope

YouTube/Drive ingestion, receipt extraction, workout video understanding,
article audio generation, spending reports, and additional applications are
future use cases. They do not block the transcription milestone.
