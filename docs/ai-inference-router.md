# Shared inference router (proposed)

Status: **proposed design, not implemented** (2026-10-21, issue #19).
Decision owner: the user. Nothing here authorizes installing CLIs, logging in
on Lara, deploying a service, or sending private content to a cloud backend.

## Context

Applications on Lara need text generation with different trade-offs per job.
The redesigned local notes workflow (Qwen3.6-35B-A3B with GPU offload, see
`ai-generation-iterations.md`, "Redesigned workflow runs") produces organized
notes in 35-55 minutes, but still makes multi-person story errors that a
frontier model avoids. The user wants to choose per job, from each
application's interface, between:

- a **private local** model (slow, possibly hours, optionally with reasoning);
- **Claude Code** or **Codex** through their command-line tools on the user's
  existing subscriptions, without paying for API credits, when speed or quality
  matters more.

This is meant for every application (Notey first), so it belongs in the shared
AI layer as a generic capability.

## Decision (proposed)

Add one private, domain-neutral **inference router** service under
`ai/router/` on `lara-backend`. Applications submit asynchronous generation jobs
naming a backend; the router runs them, records provenance, and returns
structured results. Applications keep their prompts, multi-step recipes,
privacy consent and review UI.

```text
Notey / other apps ──HTTP──> router (job queue, SQLite, provenance)
                                ├── local worker   → llama.cpp (GPU lease with Whisper)
                                ├── claude worker  → official `claude -p` CLI (user's subscription)
                                └── codex worker   → official `codex exec` CLI (user's ChatGPT plan)
```

## Backends

| Backend | Where content goes | Typical time per request | Cost | Notes |
| --- | --- | --- | --- | --- |
| `local` | Stays on Lara | ~1-2 min per note section (35B MoE, GPU auto) | Electricity, heat | Default. Measured in the notes runs. |
| `local-thorough` | Stays on Lara | Several times longer | Electricity, heat | Reasoning on and/or a larger dense model; candidate profiles still to be evaluated. |
| `claude` | Anthropic, under the user's consumer-plan data settings | Seconds to minutes (unmeasured here) | Counts against subscription usage limits | Unmodified `claude` binary, user's own login. |
| `codex` | OpenAI, under the user's ChatGPT data settings | Seconds to minutes (unmeasured here) | Counts against plan rate limits | Unmodified `codex` binary, user's own login. |

Time figures for cloud backends are placeholders until measured.

## Job API (sketch)

Private on `lara-backend`, mirroring the transcription service's job model
(HTTP 202 then polling, explicit failure states, no silent fallbacks).

`POST /v1/jobs`

```json
{
  "app": "notey",
  "backend": "local | local-thorough | claude | codex",
  "fallback": "none | local",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "response_schema": {"type": "object"},
  "max_output_tokens": 2000,
  "reasoning": "off | low | high",
  "deadline": "2026-10-22T09:00:00-03:00",
  "privacy": {"contains_private_content": true, "user_confirmed_cloud": true}
}
```

- Returns `202` with `job_id`, `status`, `status_url`.
- Status: `queued`, `waiting_for_resource` (GPU lease or subscription rate
  window), `running`, `completed`, `failed`, `cancelled`.
- A completed job returns `result` (schema-validated JSON or text) plus
  provenance: backend, CLI or runtime version, model reported by the backend,
  timings, token usage when available, and attempts.
- Errors: `422` invalid request or schema; `409` cloud backend requested
  without `user_confirmed_cloud`; `429` queue full with `Retry-After`; `503`
  backend not configured or not logged in. Rate-limit and auth failures inside
  a job are explicit job states, never a silent backend switch: a fallback runs
  only when the job asked for it, and the result says it happened.
- `DELETE /v1/jobs/{id}` cancels a queued or running job.

One request is one model call. Multi-step workflows (Notey's plan, write,
review and check stages) stay in the application, which checkpoints by
storing each completed job's result. A long local run then survives
interruptions, because only the unfinished step is resubmitted.

## Worker design

**Local worker.** Reuses `ai/generation/runtime_session.py`, changed from
"start, run batch, stop" to a held runtime with idle unload. It takes a
**GPU lease** before loading: while generation holds the lease, transcription
jobs wait (queued, not failed), and vice versa. This replaces today's manual
"stop Whisper, run, restart" sequence. Long local jobs get a thermal guard:
pause between requests while the CPU package stays above a configured
temperature (the notes runs reached 100 C during combined CPU+GPU load).

**Claude worker.** Runs the official CLI exactly as published, in an empty
temporary directory per job, with no tools and no saved session. Planned
flags, re-verified against the CLI reference at implementation time:

```sh
claude -p --output-format json --json-schema "$SCHEMA" \
  --system-prompt-file system.txt --tools "" --disallowedTools "mcp__*" \
  --setting-sources "" --strict-mcp-config --no-session-persistence \
  --permission-prompts none --model "$MODEL" --effort "$EFFORT" < user.txt
```

The structured result is read from `structured_output`; a missing field is a
failed job. `--bare` is not used because bare mode does not use subscription
login.

**Codex worker.** Same isolation:

```sh
codex exec --output-schema schema.json --sandbox read-only --ephemeral \
  --ignore-user-config --skip-git-repo-check -o result.json - < prompt.txt
```

**Credentials.** Each CLI is logged in once through its own official sign-in
flow (for Claude, `claude auth login` or `claude setup-token`) under a dedicated
Unix user on Lara. Credential files stay in that user's home, mode 600, outside
Git, logs and backups shared elsewhere. The router never reads, copies or
forwards tokens; it only runs the binaries. `claude auth status` and a Codex
equivalent feed a health check so a logged-out backend reports `503`.

**Network.** Cloud workers need outbound internet; the router API and local
inference stay private with no published ports.

## Permitted use (as documented on 2026-10-21)

- Anthropic: OAuth sign-in is for subscription purchasers' "ordinary use of
  Claude Code"; plan limits "assume ordinary, individual usage of Claude Code
  and the Agent SDK". Developers may not route requests through Free, Pro or
  Max credentials **on behalf of their users**, nor collect or intermediate
  session tokens. An end user may sign in to the unmodified binary with their
  own subscription. Our reading: one person's own apps calling the unmodified
  CLI under that person's login fit; serving anyone else, or extracting tokens,
  does not. Anthropic may enforce without notice, and the policy changed
  several times in 2026.
- OpenAI: `codex exec` reuses saved CLI authentication; ChatGPT-managed auth in
  automation is documented with warnings (treat `auth.json` like a password,
  not for public repositories), and API keys are called the simpler default.
- Consequences for the design: single user only, unmodified binaries, no token
  handling, usage limits respected (queue rather than retry storms), and each
  cloud backend configurable to an API key instead without changing apps. The
  monthly model review re-checks these terms and records changes here.

This is a reading of public documentation, not legal advice.

## Privacy

- `local` is the default for every app. Cloud backends are opt-in per app and
  per job; the API rejects a cloud job without explicit confirmation.
- Applications label the choice in their interface (for example "Local -
  private - about 40 min" versus "Claude - sent to Anthropic - about 2 min") and
  record the backend in the document's provenance.
- Consumer-plan data-use settings (for example, whether conversations may be
  used for training) are the user's account settings; the router cannot
  enforce them and the design does not assume their values.

## Alternatives considered

1. **Local only (status quo).** Private and free, but the measured quality gap
   on multi-person stories remains and long runs tie up the GPU and heat the
   laptop. Kept as the default backend.
2. **Paid APIs.** Simplest and policy-clean, but the user prefers not to pay
   for credits. Kept as a configuration option per cloud backend.
3. **Each app calls the CLIs itself.** Duplicates credentials, rate-limit
   handling and policy checks in every app. Rejected.
4. **Third-party gateways (for example LiteLLM, OpenRouter).** Require API keys
   and add another party with access to content. Rejected for this use.

## Consequences

- One place handles credentials, usage limits, GPU coordination and
  provenance; apps get one contract.
- Subscription use can be restricted by the providers at any time; apps must
  handle `503`/`failed` and the router must allow switching to an API key.
- Cloud jobs send private content to a provider; consent and labels are
  mandatory.
- The router adds a long-running service and a dedicated CLI user on Lara to
  maintain (CLI updates, re-login when tokens expire).

## Phased plan

1. **Router core + local backend.** Job API, SQLite job store, held llama.cpp
   runtime with idle unload, offline tests with fake backends.
2. **GPU lease with transcription.** Shared lease so neither service is
   stopped by hand; tests for waiting rather than failing.
3. **Claude CLI backend.** Dedicated user, official login, isolation flags,
   health check, usage-limit handling; integration check with synthetic text.
4. **Codex CLI backend.** Same pattern.
5. **Quality and time comparison.** The same notes workflow input on `local`,
   `claude` and `codex`, scored with the confirmed private checklist. Sending
   the sermon to a cloud backend requires the user's explicit OK first.
6. **Application integration.** In the Notey repository: backend picker,
   consent, per-backend recipes (a frontier model can take the whole transcript
   in one request), checkpointing.

Each phase gets its own issue, tests and PR.

## Open questions for the user

- Which applications besides Notey should be first consumers?
- Is any category of content never allowed on cloud backends, regardless of
  per-job choice?
- Should `local-thorough` start with reasoning on the current 35B model (no
  download) before evaluating a larger dense model (download needs approval)?

## Sources (checked 2026-10-21)

- Claude Code headless mode: https://code.claude.com/docs/en/headless
- Claude Code CLI reference: https://code.claude.com/docs/en/cli-reference
- Claude Code legal and compliance: https://code.claude.com/docs/en/legal-and-compliance
- Codex non-interactive mode: https://learn.chatgpt.com/docs/non-interactive-mode
