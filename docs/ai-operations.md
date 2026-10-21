# AI project operations

## Locations

| Purpose | Location |
| --- | --- |
| Canonical infrastructure checkout | `lara:/srv/lara/infrastructure` |
| Shared AI source/configuration | `lara:/srv/lara/infrastructure/ai` (planned) |
| Models | `lara:/srv/lara/ai/models` |
| Runtime inputs, jobs, outputs | `lara:/srv/lara/ai/data` |
| Independent deployed applications | `lara:/srv/lara/apps` |
| Local planning-file staging | `/Users/thejuliamathias/Projects/Personal/ai_server` |

The infrastructure checkout already has a private GitHub remote. Do not create
another repository for the same infrastructure or copy runtime data to the Mac.
The current request explicitly authorizes staging and replicating these project
files. Local staging does not change Lara's role as the canonical checkout.

## Inspect before editing

```sh
ssh -o BatchMode=yes -o ConnectTimeout=10 lara \
  'cd /srv/lara/infrastructure && git status -sb && git diff --stat'
```

Read applicable remote `AGENTS.md` files before changes. A sandbox DNS failure
does not prove Lara is offline; use the approved SSH execution path when
available. Keep host verification enabled and never print private keys or
credentials while diagnosing a connection.

## Replicate the planning files

Explicit synchronization set:

```text
AGENTS.md
.github/PULL_REQUEST_TEMPLATE.md
docs/ai-project.md
docs/ai-roadmap.md
docs/ai-operations.md
docs/ai-status.md
docs/ai-transcription-follow-ups.md
docs/ai-scope-and-model-review.md
```

Before first copy, confirm each destination is absent; on subsequent copies,
read changes on both sides and reconcile them. Transfer only this explicit list
using SSH/SCP or an equivalent SSH stream. When archiving on macOS, disable
Apple metadata (for example, `COPYFILE_DISABLE=1 tar --no-xattrs`) so `._` files
are not created on Linux. Do not synchronize entire directories
with deletion enabled. Preserve existing `README.md`, deployment configuration,
certificates, Git metadata, and unrelated documentation.

After copying, compare SHA-256 hashes for every file on both hosts. Review
remote `git status --short`, inspect all new files, and check whitespace. Mark
milestone 0 complete only after equality and repository checks pass.

## Implementation and deployment

Make shared AI changes in Lara's existing checkout over SSH. Pin dependencies
after checking upstream requirements. Validate Compose configuration before
starting a service; starting a service and downloading model weights are
separate from copying documentation.

Docker access works for the regular SSH user at the last inspection. Do not
assume passwordless sudo: `sudo -n` required authentication during that check.
Use noninteractive commands where possible and never request or embed passwords.

Before committing, inspect staged paths and the complete staged diff, then run
`git diff --cached --check`. Every commit needs a title and descriptive body.
Retain the configured signing mechanism and verify new signatures when commits
are made. Do not disable signing or rewrite existing history to bypass errors.

## Recovery and data

Keep source configuration in Git and model/input/output data outside it. An
image rebuild must not erase uploads or job records. Document interrupted-job
recovery and data retention when persistence is implemented. Existing backups
and unrelated containers must not be pruned as part of AI setup.

## What belongs in Git

| Version-controlled recipe | Runtime material outside Git |
| --- | --- |
| Dockerfile and dependency lock | Built image, Docker cache and container state |
| Compose mounts and model path | Actual model weights under `/srv/lara/ai/models` |
| Pinned model revision and verified downloader | Downloaded assets and their runtime manifest |
| Service source and synthetic test fixtures | Uploaded audio, PDFs, transcripts and correction history |
| Evaluation runner and nonprivate findings | Job databases, private evaluation outputs and telemetry |

The canonical checkout is `/srv/lara/infrastructure`. The Mac staging folder
contains planning documents only; it is not expected to contain the service
Dockerfiles. GitHub shows only pushed commits, so committing on Lara does not
make a file appear on GitHub until those commits are pushed.

The transcription Dockerfile builds the software environment. Compose connects
that environment to model files using this host-to-container mapping:

```text
/srv/lara/ai/models/large-v3  ->  /models/large-v3  (read-only)
/srv/lara/ai/data/transcription  ->  /data          (writable)
```

`MODEL_PATH=/models/large-v3` tells the service where to load the model within
its container. Normal startup is offline; it does not fetch missing weights.
The service README documents the explicit pinned download/verification step.

Bootstrap creates directories and shared networks. Model download and service
startup remain explicit service deployment steps. A fresh machine also needs
the Docker/NVIDIA prerequisites documented in `server-setup.md`; bootstrap does
not install them. Rebuilding from Git recovers software/configuration, while
runtime data needs a separate backup and restoration procedure.
