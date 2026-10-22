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
naming a backend; the router runs them, falls back along a fixed chain when a
cloud backend fails, records every attempt, and returns structured results.
Applications keep their prompts, multi-step recipes, privacy consent and
review UI.

```text
Notey / other apps ──HTTP──> router (job queue, SQLite, attempts, provenance)
                                ├── claude worker  → official `claude -p` CLI (user's subscription)
                                ├── codex worker   → official `codex exec` CLI (user's ChatGPT plan)
                                └── local worker   → llama.cpp (GPU lease with Whisper)

Fallback chains (user decision, 2026-10-21):
  claude → codex → local
  codex  → claude → local
  local  → (none)
```

## Backends

| Backend | Where content goes | Typical time per request | Cost | Notes |
| --- | --- | --- | --- | --- |
| `local` | Stays on Lara | ~1-2 min per note section (35B MoE, GPU auto) | Electricity, heat | Default. Measured in the notes runs. |
| `local-thorough` | Stays on Lara | Several times longer | Electricity, heat | Reasoning on and/or a larger dense model; candidate profiles still to be evaluated. |
| `claude` | Anthropic, under the user's consumer-plan data settings | 41 s for a whole sermon in one request (measured once, Sonnet 5.5 on Pro) | Counts against subscription usage limits | Unmodified `claude` binary, user's own login. |
| `codex` | OpenAI, under the user's ChatGPT data settings | Seconds to minutes (unmeasured here) | Counts against plan rate limits | Unmodified `codex` binary, user's own login. |

The Codex figure is a placeholder until measured.

**First comparison (2026-10-21, user-approved, one sample).** The same private
sermon input that took the local workflow 35-55 minutes went through the
Claude CLI as one request: 41 seconds (Claude Sonnet 5.5 on a Pro plan). Against
the user-confirmed checklist it got every story right that the local model
kept failing (including the two-people ending, which it also flagged as
uncertain), attributed the appeal correctly and matched the user's note style
closely, with no hard check flags. Its one defect was rewording the user's
handwritten notes, which the application recipe corrects in code by inserting
them verbatim. Details: `ai-generation-iterations.md`. One sample does not
establish reliability across sermons.

## Other CLI backends considered (free tiers only)

The user already pays for Claude and ChatGPT and wants additional CLIs only if
they have a free tier. Findings on 2026-10-21:

| CLI | Free tier | Headless use | Status |
| --- | --- | --- | --- |
| GitHub Copilot CLI | Yes: all plans include it, Copilot Free with a small AI-credit allowance and automatic model selection only | `-p` programmatic mode documented | Candidate. Before adding: confirm tools can be fully disabled, the actual free allowance, and how free-plan prompts are used. |
| Antigravity CLI (`agy`, Google) | A free "starter" quota exists but is not officially documented; users report it is small | Unclear | Watch. Replaced free Gemini CLI use. |
| Gemini CLI | No longer free: since 2026-06-18 it serves only paid API keys and enterprise plans | Yes | Excluded (no free tier). |
| Qwen Code | Free sign-in tier ended in April 2026; needs a paid key or a local model | Yes | Excluded. |
| DeepSeek | No official CLI; community tools (for example DeepSeek TUI) need DeepSeek's paid API | Varies | Excluded. |

Backends are adapters behind one contract, so a free-tier CLI can be added
later as an optional link in the cloud chains (before `local`) once verified,
with its own provider entry in `cloud_providers_allowed`. Free tiers commonly
have stricter data-use terms; each must be checked before private content is
sent.

## Job API (sketch)

Private on `lara-backend`, mirroring the transcription service's job model
(HTTP 202 then polling, explicit failure states, no silent fallbacks).

`POST /v1/jobs`

```json
{
  "app": "notey",
  "backend": "local | local-thorough | claude | codex",
  "fallback": "default | none",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "response_schema": {"type": "object"},
  "max_output_tokens": 2000,
  "reasoning": "off | low | high",
  "deadline": "2026-10-22T09:00:00-03:00",
  "privacy": {"cloud_providers_allowed": ["anthropic", "openai"]}
}
```

- Returns `202` with `job_id`, `status`, `status_url`.
- Status: `queued`, `waiting_for_resource` (GPU lease or subscription rate
  window), `running`, `completed`, `failed`, `cancelled`.
- A completed job returns `result` (schema-validated JSON or text) plus
  provenance: the backend that produced it, CLI or runtime version, model
  reported by the backend, timings, token usage when available, and the full
  `attempts` list described under "Fallbacks".
- Request errors: `422` invalid request or schema; `409` a cloud backend whose
  provider is not in `cloud_providers_allowed`; `429` queue full with
  `Retry-After`. A backend that is not configured or logged in is not a request
  error: it is a failed attempt that triggers the fallback chain.
- `DELETE /v1/jobs/{id}` cancels a queued or running job.

## Fallbacks

The user chose fixed chains: `claude → codex → local`, `codex → claude →
local`, and no fallback for `local`. A job may opt out with `"fallback":
"none"`. Fallback is never silent: the job result always states which backend
produced it and why the earlier ones did not.

Triggers (an attempt fails and the next backend in the chain runs):

| Error code | Meaning |
| --- | --- |
| `usage_limit` | Subscription or plan limit reached; includes the reset time when the CLI reports it |
| `auth_unavailable` | CLI not logged in, token expired, or account restricted |
| `provider_unavailable` | Provider outage, overload or network failure after the CLI's own retries |
| `timeout` | No result within the backend's time budget |
| `invalid_output` | Missing or schema-invalid structured output after one same-backend retry |
| `cli_error` | CLI crashed or returned a non-zero exit without a usable result |
| `refused` | The model declined the request |

Not triggers: invalid requests (rejected before any attempt), and cancellation.
A provider not listed in `cloud_providers_allowed` is skipped and recorded as
`skipped_not_allowed`, because falling back from Claude to Codex sends the same
content to a second company; the app must have the user's consent for every
provider it lists. `local` is always allowed and is the last resort for both
cloud backends, which means a fast job can become a slow one (35+ minutes for a
sermon): the job status reports `running` on `local` so the app can tell the
user.

Every result carries the attempts:

```json
{
  "status": "completed",
  "backend_requested": "claude",
  "backend_used": "local",
  "fallback_used": true,
  "attempts": [
    {"backend": "claude", "outcome": "failed", "error_code": "usage_limit",
     "error_detail": "limit reached, resets 2026-10-22T03:00:00-03:00",
     "started_at": "...", "ended_at": "..."},
    {"backend": "codex", "outcome": "failed", "error_code": "auth_unavailable",
     "error_detail": "codex login required", "started_at": "...", "ended_at": "..."},
    {"backend": "local", "outcome": "completed", "started_at": "...", "ended_at": "..."}
  ],
  "result": {}
}
```

A job that exhausts its chain ends `failed` with the same `attempts` list. A
router-wide health view (which backends are logged in, usage-limit reset times)
lets apps warn before submitting.

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
  per job; the job names every provider the user allowed, and the router never
  falls back to a provider outside that list.
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
- Cloud jobs send private content to a provider, and a fallback can send it to
  a second provider; consent covers each provider by name, and labels are
  mandatory.
- A cloud job that falls back to `local` can take tens of minutes instead of
  seconds; apps must show that state rather than appear stuck.
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
5. **Quality and time comparison.** Claude CLI done once (see above); Codex
   CLI and a second sermon still to measure. Each cloud send of private
   content needs the user's explicit OK.
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
- Gemini CLI transition announcement: https://github.com/google-gemini/gemini-cli/discussions/27274
- GitHub Copilot plans: https://docs.github.com/en/copilot/get-started/plans
- GitHub Copilot CLI: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli
- Qwen Code free-tier end and DeepSeek community CLIs: secondary reports only
  (for example https://inventivehq.com/blog/qwen-code-still-free-2026-shutdown,
  https://github.com/holasoymalva/deepseek-cli); recheck before relying on them.
