# Reusable application delivery and recovery

Status: version 1 implemented for review; live setup and runtime
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

The version 1 executable accepts the configuration demonstrated by Notey
`deploy/delivery.example.json`. Installing or activating it is a separate step.

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

Verified 2026-10-22: Julia authorized Notey immutable releases; the repository
setting is enabled and `NOTEY_IMMUTABLE_RELEASES_CONFIRMED=true` is set. Future
published tags/assets are locked. Corrections require a new release. Other apps
must explicitly enable and verify their own setting.

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

## Version 1 release eligibility

`delivery/v1/release.py` evaluates supplied metadata for an immutable
`release-<full SHA>` tag resolving to the same revision as successful completed
main-branch push CI and a human-merged PR in the configured repository/workflow.
It rejects missing, failed, pending, cancelled, unrelated and unmerged evidence.
The adapter must independently fetch authenticated metadata, resolve the tag and
hash assets; this pure policy does not perform those operations.

```sh
python3 -m unittest discover -s delivery/v1/tests -p test_release.py -v
```

Five deterministic tests cover eligibility and rejection paths. They do not
establish live publication, image integrity, rollout serialization or recovery.

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

Current execution: 40 deterministic shared tests passed on Lara (41 discovered,
one opt-in crypto test skipped in the ordinary suite). The opt-in test separately
passed real GnuPG encryption, public-only Lara keyring and external-key decryption
of exact synthetic bytes; storage was fake. Notey archive, adapter and real local
PostgreSQL destructive-schema recovery checks passed separately. These establish
no live Google authorization, timers, automatic rollout or browser acceptance.
Keep both issues open until those gates run.

## Sources

- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub release asset permissions](https://docs.github.com/en/rest/releases/assets)
- [Google Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [PostgreSQL dump](https://www.postgresql.org/docs/17/app-pgdump.html)
- [PostgreSQL restore](https://www.postgresql.org/docs/17/app-pgrestore.html)

## Implemented command and adapter contract

Requires Python 3.11+ and the existing GnuPG/Docker/Compose tools; no new Python
packages. On Lara use `/usr/bin/python3`, not the older Conda `python3`.
`control.py check|backup|status CONFIG` reads an owner-only JSON configuration.
`check` retrieves the latest immutable release, validates exact completed main
CI and human merge metadata, hashes every asset, rejects older/diverged commits,
and passes the candidate to the app adapter. A release published while CI is
still finishing waits until a later poll. Multiple newer releases may coalesce
to the latest eligible one. A newer failed release fails closed; it does not
silently select an older candidate. Cached packages are reverified before reuse.

A per-app process lock rejects overlap between backups and deployments; a busy
invocation exits unsuccessfully and the next timer invocation retries. There is
no queue and no global deployment lock across apps. `state/transaction.json`
records stages durably before side effects. `current.json`, `previous.json` and
`last-backup.json` preserve exact identities and receipts. `status` reads local
state; systemd exit status/journals report failures without credentials. No chat,
email or external notification integration is installed.

The configured adapter is an explicit argv list, invoked without a shell, with
one phase argument: verify, pause, backup, migrate, activate, health, stop or
resume. Environment variables LARA_DELIVERY_CONFIG, LARA_DELIVERY_CURRENT and
LARA_DELIVERY_CANDIDATE convey the config path and public release metadata.
Only backup prints JSON: verified=true, app, revision and off-host id are required.
Other child output is captured to prevent accidentally logging secrets.
The app must validate the candidate recipe/image and define snapshot consistency.
Notey pauses only its web service for deployment; daily PostgreSQL pg_dump is
transactionally consistent without pausing it. Actual file/job consistency is a
later app extension, not implied by this database-only adapter.

Before migration, a failed backup resumes the current image. From the first
migration attempt onward, any error/timeout stops the candidate and records
recovery_required. Interrupted running markers also block further operations.
A subprocess timeout does not prove its Docker migration container stopped:
inspect app-scoped migration containers before recovery. No automatic image
rollback, down migration, database replacement or volume deletion occurs.
Recovery also blocks daily expiry. Add incident backup IDs to
protected_backup_ids before resolving the incident.

## Backup and credential behavior

`backup.py` encrypts an app-produced snapshot in private scratch space, uploads
only ciphertext and removes temporary plaintext on normal completion/failure.
A host crash may leave private scratch remnants: inspect and remove only this
app's abandoned scratch after ensuring no backup runs. Never use a global tmp
cleanup. `drive.py` downloads the uploaded ciphertext and checks SHA-256 before
marking its metadata verified. Failed/incomplete objects never displace valid
recovery points. Their investigation/cleanup is manual.

Julia approved moving expired backups to Drive Trash on 2026-10-22. Expiry never
permanently deletes objects or empties Trash. Google controls Trash lifetime;
trashed objects can continue consuming quota. Expiry defaults off and requires
an external restore date, matching recipient fingerprint and verified backup ID.
Deployment also requires that restore receipt; a manual `backup` can run first
to establish it. Configuration records operator evidence, not a cryptographic
proof that a human performed a restore. Repeat the actual restore after changing
the key or backup integration, before updating its receipt. A key change fails
closed. Policy is explicit per app; no other app inherits Notey's 30/five rule.

## Dedicated Google OAuth setup (operator procedure)

No account authorization has been performed. On the Mac, using Julia's account:

1. In Google Cloud Console select/create a dedicated backup-integration project,
   enable Google Drive API, and configure Google Auth Platform branding/audience.
   Do not enable billing or a paid plan. Use a dedicated Desktop app OAuth client,
   not a web client or a shared service credential. Choose the account/audience
   appropriate to Julia's Google account; do not request broader Drive scopes.
2. Configure only `https://www.googleapis.com/auth/drive.file` for this client.
   For an External app in Testing, refresh tokens normally expire after seven
   days for this scope. Before unattended operation, complete the appropriate
   production/personal-use setup shown by Google. Publishing the OAuth consent
   configuration does not publish backup files. Stop for review if Google asks
   for broader permissions, organizational approval or costs.
3. Download the Desktop client JSON into a private Mac directory outside Git and
   Drive-synced folders; chmod the directory 700 and client JSON 600. Never paste
   it, token output, browser callback URLs or screenshots of secrets into chat.
4. Copy the reviewed merged `delivery/v1` helper files from Lara into a NEW private
   temporary directory on the Mac. This is an installed setup tool, not a Mac
   infrastructure development checkout. Run with a Python 3.11+ interpreter:
   `python3 /PRIVATE/TOOL/authorize_drive.py /PRIVATE/client.json /PRIVATE/drive.json 'Notey encrypted backups'`.
   It opens Google's browser consent with PKCE and a localhost callback, requests
   offline drive.file access, creates the named private folder, and writes a new
   owner-only drive.json. It refuses overwrite and never prints credentials.
5. Confirm the correct account and requested per-file scope in the browser.
   Keep the folder unshared. The runtime verifies it is private. Transfer the
   credential file privately to the app delivery directory on Lara; chmod 600.
   Store a recovery copy securely outside Lara. Do not reuse it for another app.
6. Run a manual backup and external-key restore below. Test revoked/expired
   authorization in an isolated profile: it must fail without migration/expiry.
   Record only scope, private-folder status and outcomes, not credential values.

`drive.file` limits access to integration-created or explicitly selected files;
it is not upload-only, and a folder name is not an authorization boundary.
The credential can alter/trash accessible backups. Encryption protects content
confidentiality; it does not make Drive an immutable vault. Revoke the dedicated
client's grant through the Google account if compromised, then reauthorize and
retest recovery. Token expiry/revocation must cause backup and deployment failure,
not silent operation without backups.

## Installing a reviewed version and opting in

After Julia merges both companion PRs, verify the actual merged SHAs and fetch
origin/main in the Lara issue worktree without switching the canonical checkout.
Run `bash delivery/v1/install-mechanism.sh FULL_MERGED_INFRA_SHA` there. It requires
the exact origin repository and a revision reachable from fetched origin/main,
exports the reviewed files to a NEW `/srv/lara/app-delivery/SHA`, and starts nothing.
Pin each app's config mechanism_dir and its `delivery/mechanism` symlink to that
installed `delivery/v1` directory. Keep the adapter pinned to a reviewed app SHA.
The Notey repository's `docs/release-operations.md` supplies its bootstrap and
restore procedures, exact paths, synthetic fixture and acceptance gates.

The four systemd template units are inert until explicitly installed/activated.
After reviewing rendered paths, copy only lara-app-check@.service/.timer and
lara-app-backup@.service/.timer from the pinned export into /etc/systemd/system,
run `systemd-analyze verify` and `systemctl daemon-reload`, then enable/start only
`lara-app-check@APP.timer` and `lara-app-backup@APP.timer` for the authorized app.
Check timers use five minutes; daily backup is 04:00 America/Sao_Paulo with up to
10 minutes jitter. Adjust either using an app-specific drop-in and verify
`systemctl list-timers`; for OnCalendar overrides reset the inherited value
with an empty `OnCalendar=` first. Do not edit the common template for one app.

Services run as the existing Docker-capable owner, with umask 077, read-only
filesystem except that app's delivery directory, bounded CPU/memory, and private
/tmp. Docker access remains powerful; these settings are not container-daemon
security isolation. Each app's separate paths/credentials and adapter review are
required. No Caddy/firewall/AI service change is part of installation.

To pause automatic work: `systemctl stop lara-app-check@APP.timer
lara-app-backup@APP.timer`. This stops future triggers; inspect any active service
before interrupting a migration. Keep runtime databases, images, state and backup
receipts. Do not disable other apps' timers or perform Docker pruning.

## Repeatable verification

```
/usr/bin/python3 -m unittest discover -s delivery/v1/tests -v
LARA_CRYPTO_INTEGRATION=1 /usr/bin/python3 -m unittest discover -s delivery/v1/tests -p test_crypto_integration.py -v
systemd-analyze verify systemd/lara-app-{check,backup}@.{service,timer}
```

Ordinary tests use fake GitHub/Drive/adapter metadata and an actual competing
lock process. The optional crypto test uses disposable generated keys, a public
keyring, fake off-host storage and actual GnuPG decryption; no account or service
is contacted. Live Drive and Lara acceptance remain separate. Another app's
onboarding must repeat those gates with its own reviewed policy and adapter.

OAuth sources verified 2026-10-22:
[Desktop OAuth/PKCE](https://developers.google.com/identity/protocols/oauth2/native-app),
[refresh token lifetime](https://developers.google.com/identity/protocols/oauth2#expiration),
[per-file Drive scope](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).
