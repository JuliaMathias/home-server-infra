# Reusable application delivery and recovery

Status: approved direction for Notey N02; shared implementation and runtime
acceptance remain in [issue #17](https://github.com/JuliaMathias/home-server-infra/issues/17).
Application companion: [Notey #22](https://github.com/JuliaMathias/notey/issues/22).
This guide defines the adoption contract. It is not evidence of installed timers,
working credentials, published images or successful live recovery.

## Ownership and working location

Develop application code and application release recipes in each application's
Mac repository. Develop this shared infrastructure repository on Lara in an
isolated issue worktree through a named tmux session. Current work:
`/srv/lara/worktrees/infra-app-delivery`, branch
`codex/issue-17-app-delivery`, session `notey-n02`.

Julia can inspect it using:

```sh
ssh -t lara 'tmux attach -t notey-n02'
```

Keep infrastructure and application PRs separate. Preserve the canonical
checkout's unrelated branch and other active worktrees. Do not activate unmerged
infrastructure from a working branch.

## Architecture decision: one small versioned mechanism, per-app configuration

Julia approved pull delivery and requested a repeatable workflow on 2026-10-21.
An application's CI builds and publishes its tested image. A Lara-side checker
retrieves an eligible release; no application compilation or dependency download
takes place on Lara. A short checking interval trades a small rollout delay for
avoiding CI deployment access into the tailnet. The proposed interval is five
minutes, configurable per app.

Shared ownership: release eligibility/integrity checks, per-app locking,
orchestration order, backup encryption/transfer/verification, retention evaluation,
scheduling and durable status. App ownership: its image build, Compose recipe,
database adapter, migration command, file/job consistency, health/readiness
semantics and migration-specific recovery instructions.

Implement only the current Docker Compose / PostgreSQL foundation use case.
Do not turn this into a general deployment platform or assume that a future
SQLite/database-free app works without another reviewed adapter. Keep the
contract versioned so an infrastructure update cannot silently change every app.

## Configuration contract

The following is the configuration surface to implement and verify, not a claim
that these example keys are already accepted by an installed executable.

| Setting | Owner and meaning |
| --- | --- |
| Contract version | App pins the supported shared mechanism version. |
| App ID / Compose project | Unique per app; used for locks, receipts and service scope. |
| GitHub repository / branch / CI workflow | Exact allowlist for release source and checks. |
| Release transport | Private GitHub release assets containing the prebuilt image and deployment recipe; verify source/image/checksums. |
| State and release directories | Dedicated app paths under /srv/lara/apps; no source development checkout. |
| Runtime secrets file | Private per-app host file, outside Git/images/logs. |
| GitHub credential file | Per-repository read access to required release/CI/merge information. |
| Database adapter / service | Dedicated database; never infer a shared PostgreSQL instance. |
| Migration command | App-owned command shipped in its image, with an explicit recovery policy. |
| Health URL and service checks | App-specific readiness plus HTTPS checks where appropriate. |
| Backup destination / credential file | Dedicated private Drive location and restricted authorization. |
| Encryption recipient | Public key on Lara; private recovery key outside Lara. |
| Schedule | Backup before deployment, optional daily schedule, configurable polling. |
| Retention minimum count / age | Explicit per-app approvals; never inherit Notey's numbers silently. |
| Reporting | Current/previous revision, backup receipt, timestamps and failed stage; never secrets. |

Notey's approved settings: repository JuliaMathias/notey, main branch, app ID
notey, existing dedicated PostgreSQL 17 and existing private HTTPS route. Backups
run before each deployment plus daily. Keep all completed verified backups from
the last five days AND at least the newest 30 regardless of age. Expiry is
eligible only outside the newest 30 AND older than five days. Failed/incomplete
backups cannot displace valid recovery points. These settings do not become
defaults for other apps.

Credentials, encryption-recipient setup, active timers, the exact installed
mechanism revision and live restore evidence must be recorded at activation.
No credentials or keys have been provisioned by this documentation.

Verified setup prerequisite: Notey release immutability is currently disabled.
The publisher/checker must fail closed until it is enabled and verified. Enabling
that repository setting locks subsequently published releases and their tags;
record the change explicitly rather than weakening release identity checks.

## Version 1 retention policy

`delivery/v1/retention.py` computes an expiry candidate list using explicit
app identity, minimum successful count, minimum age and an injected clock.
It preserves incident-pinned backups and rejects mixed-app or invalid/future
receipts. It performs no storage operations or deletion. Run:

```sh
python3 -m unittest discover -s delivery/v1/tests -p test_retention.py -v
```

Eight deterministic tests cover rapid deployments, sparse old backups, exact
five-day boundaries, failed uploads, incident pins and different per-app policies.
They passed on Lara without contacting live services; CI repeats them separately.

## Required release transaction

1. Confirm a release belongs to the configured repository/branch, a user-merged
   PR and successful CI on that exact merged revision. Reject direct/unverified
   revisions, draft releases, failed/pending/cancelled checks and unmerged PRs.
2. Verify immutable release metadata, downloaded payload checksums, amd64
   architecture and image identity. Use the already-built image; do not rebuild.
3. Acquire the app's deployment/backup lock and recheck its current state.
   Concurrent invocations must not interleave migration or backup operations.
4. Preserve the current release, secrets and database. Establish any app-specific
   write pause required for a consistent recovery point.
5. Complete and verify the encrypted off-host backup before migration. Backup
   failure stops the update. Do not mistake local staging for off-host recovery.
6. Run the image's migration command once under the lock. A failure stops rollout.
7. Activate only that app's services and verify readiness/HTTPS. Record the exact
   successful revision/image and backup receipt.
8. On failure preserve the prior image and all data, record the failed stage and
   block unsafe subsequent rollout. Never automatically reverse migrations.
   Restart the previous image only when schema compatibility is established;
   otherwise keep the app stopped for its documented recovery procedure.

Any release requiring a manual rollout exception must state it in its PR and
provide the exact procedure. The mechanism never merges PRs. Runtime activation
of this initial mechanism is itself a documented manual exception after user
merge; subsequent ordinary eligible app releases are automatic.

## Encryption, authorization and retention

Use a dedicated backup encryption identity. Lara needs the public key only;
Julia approved storing the private recovery key in her password manager and a
protected offline copy. Confirm the external copy actually decrypts a synthetic
backup before relying on it. Routine backups remain unattended; full decryption
and disaster recovery require access to that external key.

Drive authorization and encryption solve different problems. Drive permission
allows storage operations; public-key encryption protects archived contents.
Use the narrowest practical authorization, verify the actual OAuth scope and
folder isolation, and do not call a folder path an access-control boundary.
Google's drive.file scope is per-file/app access, not an upload-only guarantee.
Retention deletion requires permissions to remove the relevant backup objects;
an upload-only credential cannot perform it.

Encrypt before upload, verify downloaded encrypted bytes and periodically
perform an external-key decryption/isolated database restore. Encryption does
not prevent a compromised writer credential from deleting accessible backups;
Drive is not an immutable backup vault. It also cannot protect live data from
a compromised application host. Do not claim ransomware-proof recovery.

Evaluate retention using successful complete receipts, UTC timestamps and
explicit app identity. Preserve backup sets referenced by unresolved recovery
incidents. Clock inconsistencies, failed listing, failed upload/verification or
invalid receipts must prevent destructive expiry. Never run a Drive-wide cleanup
or apply another application's retention policy.

## Onboarding another app

1. In the new app's repository, confirm Lara hosting and needed shared AI services.
   Read this guide and the installed mechanism's versioned contract.
2. Give the app a unique Compose project, database/storage, app directory,
   backup destination and credentials. Agree its schedule and retention.
3. Implement the app's pinned CI image build, migration/health commands and
   backup adapter. Define file/job consistency if it has non-database state.
4. Obtain its explicitly reviewed ingress entry in a separate infrastructure PR.
   Existing ingress and AI state must remain unchanged.
5. Pin the reviewed mechanism version and supply app-specific configuration.
   Keep secrets outside Git. Do not copy Notey's secrets or runtime state.
6. Run deterministic fake-adapter tests and isolated actual image/database
   checks: successful update, failed backup, failed readiness and an incompatible
   migration that needs restored data.
7. Authorize the private Drive connection and external key custody. Upload,
   download, decrypt and restore synthetic data into an isolated empty target.
8. After user merge, activate only that app's timers/configuration through the
   documented manual bootstrap. Record revision/image, backup destination,
   mechanism version and recovery evidence without secrets.
9. Verify real HTTPS/WebSocket/device behavior as relevant and confirm existing
   apps/services were preserved. Only then mark runtime acceptance complete.

## Manual verification and recovery gates

Prerequisites: user-merged app/infrastructure revisions, approved per-app
credentials/keys, isolated test target and an explicitly reviewed bootstrap plan.
Notey's synthetic DB/file contract and exact fixtures are documented in its
[backup guide](https://github.com/JuliaMathias/notey/blob/b09ba03/docs/backup-format.md)
at the companion PR's immutable commit link; this survives branch deletion.

Use only synthetic fixtures. Record exact revisions, image IDs/checksums,
commands, actual outcomes and service-state comparisons. Instructions are not
execution evidence. Cleanup removes only named test containers/databases/files;
never remove runtime volumes, revoke unrelated credentials or prune other apps.

Current execution: the Notey local archive and PostgreSQL recovery checks passed
on the Mac. Shared runner/timer installation, release eligibility/integrity/
serialization exercises, encrypted Drive recovery and automatic Lara rollout
remain not run. Do not close either delivery issue from documentation alone.

## Sources

- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub release asset permissions](https://docs.github.com/en/rest/releases/assets)
- [Google Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [PostgreSQL dump](https://www.postgresql.org/docs/17/app-pgdump.html)
- [PostgreSQL restore](https://www.postgresql.org/docs/17/app-pgrestore.html)
