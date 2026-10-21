# Working instructions

## Communication and code

- Check the actual current time before every user-facing message and append the
  date and time in America/Sao_Paulo (BRT). Do not invent timestamps.
- Every Git commit must have a descriptive title and a complete body explaining
  what changed and why. Preserve existing commit signing; never disable it to
  work around an unavailable key or agent.
- When writing Elixir, add both `@spec` and `@doc` to every function. Structure
  helpers so this requirement is satisfied; do not silently omit documentation.
- Keep explanations clear and make routine authorized progress without asking
  the user to relay terminal output that can be inspected directly over SSH.

## Read first

- `docs/ai-project.md`: agreed requirements and architecture boundaries.
- `docs/ai-roadmap.md`: implementation order and acceptance criteria.
- `docs/ai-operations.md`: remote workflow and verification.
- `docs/ai-status.md`: last verified state and immediate next action.
- On Lara, also read the existing `README.md` and `docs/server-setup.md`.

## Working location

- The canonical infrastructure Git checkout is on Lara at
  `/srv/lara/infrastructure`, remote `JuliaMathias/home-server-infra`.
- Connect using the existing SSH host `lara` as `thejuliamathias`. Respect host
  key checks and existing authentication; do not copy private keys.
- The Mac directory `/Users/thejuliamathias/Projects/Personal/ai_server` stages
  the requested instructions and planning files. It is not another infrastructure
  checkout. Keep these files synchronized explicitly; do not clone the whole
  infrastructure repository here unless the user changes that preference.
- Develop shared AI services in the existing infrastructure repository under
  `ai/`. Keep models and runtime data under `/srv/lara/ai/models` and
  `/srv/lara/ai/data`, outside Git.
- Separate application repositories belong under `/srv/lara/apps` when deployed.
  Applications may be developed on the Mac independently.
- Use descriptive repository names; Lara is a host name, not a product name.

## Architecture and quality

- Shared services provide domain-neutral transcription, document extraction,
  model inference, and resource coordination.
- Applications own persistence for domain records, orchestration, prompts,
  review screens, preacher identification, sermon boundaries, Bible retrieval,
  note integration, and domain quality checks.
- Prioritize accuracy, completeness, and fidelity over processing speed.
- Start with reusable asynchronous transcription. Whisper Large V3 through
  Faster Whisper is the agreed first candidate, subject to measurement on Lara.
  Do not silently downgrade the model when it does not fit.
- Lara has 4 GB VRAM and 32 GB installed RAM. Bound concurrency and coordinate
  expensive workloads; do not assume large models can coexist in GPU memory.
- Preserve original recordings, PDFs, raw transcripts, and correction history.
  Keep proposed exclusions as metadata; never destructively trim originals.
- Distinguish confirmed requirements, candidate technologies, and measured
  results. Previous assistant estimates are not deployment evidence.

## Changes and verification

- Inspect remote instructions, Git status, existing configuration, and resource
  availability before changing anything. Preserve unrelated edits and services.
- Keep changes focused. Prefer Docker Compose and small repeatable scripts;
  avoid introducing orchestration systems without a demonstrated need.
- Keep inference APIs on private Docker networks by default. Do not publish
  ports or change Caddy, firewall, SSH, or host packages as incidental setup.
- Never commit secrets, certificates, recordings, transcripts, Bible text,
  personal notes, model weights, database contents, or backups.
- Validate relevant configuration and behavior, then report what actually
  passed. Mocked inference is not proof of transcription quality or GPU fit.
- Before copying planning files, check destination conflicts. Copy an explicit
  file list, preserve unrelated files, and verify byte equality afterward.
- Before commits, review the exact staged diff and run `git diff --cached
  --check`. Stage only intended files and retain signed commits.
- Keep status and roadmap evidence current as milestones are completed.

## AI-only ownership and review workflow

- This project/chat owns shared AI capabilities, runtimes, resource management
  and model evaluation. Notey at `/Users/thejuliamathias/Projects/Personal/notey`
  owns Bible imports/storage, domain prompts/workflows, note integration and
  PDF/Supernote exports. Provide interface/data pointers rather than implementing
  application features here. See `docs/ai-scope-and-model-review.md`.
- Existing Bible/sermon material under AI runtime storage is private evaluation
  data, not the application's production database. Preserve it for handoff;
  do not move/delete it or treat its location/schema as an approved app design.
- Use an issue and dedicated `codex/issue-N-description` branch for changes;
  never implement on the default branch. Stage explicit paths, retain signed
  commits with complete bodies, prepare a linked PR, and leave merging to the user.
- Monthly reviews recommend meaningful model comparisons within measured
  hardware limits. They do not authorize downloads, heavy benchmarks or switches.

## Pull request descriptions

Use `.github/PULL_REQUEST_TEMPLATE.md` in the canonical infrastructure repository and keep the Mac staging copy synchronized. It is adapted from the global baseline: include an explicit manual-testing decision and, when needed, runnable instructions with actual execution status. Distinguish configuration checks, live service integration and model-quality evidence. Keep unrun runtime/deployment gates visible and adapt the template if the project workflow changes.
