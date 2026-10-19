# Transcription findings and deferred work

Decision: 2026-10-19. The user accepted the current working baseline and asked
us to collect findings, defer optimization, and proceed to the next stage.
This is a scope decision, not evidence that every acceptance check passed.

## Established evidence

- Large V3 through Faster Whisper processed two real Portuguese recordings with
  the same settings: int8_float16, beam 5, VAD and word timestamps, previous-text
  conditioning disabled. Processing took 7m39s for 68m31s and 6m50s for 59m44s.
- GPU peak memory was 2379 MiB in both evaluations. Sampled CPU peaks were
  91/93 C and GPU peaks 69/68 C. CPU throttle counters increased and GPU software
  thermal flags were active; their cause and performance impact remain unresolved.
- Selected human-reviewed excerpts demonstrate particular improvements with the
  better microphone. Fluent output can still misrecognize names, numbers, and
  meaning-changing phrases. There is no representative whole-recording WER.
- Equivalent name spellings accepted by the reviewer should be normalized for
  alias-aware evaluation. Keep literal WER and normalized metrics distinct.
- Preserve original media, raw drafts, uncertain corrections and reviewer history
  privately outside Git. Personal examples and name aliases remain in that layer.

## Future experiments, not enabled settings

| Candidate | Purpose | Required comparison |
| --- | --- | --- |
| Reviewed vocabulary via hotwords/context | Help uncommon words and names | Same audio with/without hints; check false insertions and fresh excerpts |
| Previous-text conditioning | Improve continuity | Check consistency, error propagation, repetition and timestamp integrity |
| Decoding settings | Explore alternative recognition choices | Change one setting at a time; larger beams do not guarantee quality |
| Selective second pass with surrounding audio | Review difficult passages | Compare against checked audio; agreement is not proof |
| VAD/segmentation changes | Investigate missing quiet speech | Inspect boundaries and preserve original time coordinates |
| Alternative model/precision | Explore quality/resource tradeoffs | Same checked inputs, measured fit and resource use; no silent downgrade |
| Fine-tuning | Adapt to recurring vocabulary/accent | Only after enough checked paired data and a held-out evaluation exist |
| Thermal/resource coordination | Understand sustained limits | Controlled load, clocks, temperatures and nonduplicated throttle counters |

## Remaining validation

Representative Portuguese and English audio, a roughly two-hour recording,
repeated-job stability, and broader human reference coverage remain open.
Candidate experiments do not block beginning generation evaluation. Revisit
when a concrete quality failure or workload requirement justifies the work.

Faster Whisper options were checked against the deployed version's source:
https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py
