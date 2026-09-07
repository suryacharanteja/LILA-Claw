# LLD-05 — Packaging, updates and qualification

Version: 0.2  
Status: Implementation specification — approval pending  
Parent: [LLD review package](../LLD-LILA-Claw.md)

## Distribution layout

Per-user binaries under LocalAppData/Programs/LILAClaw/versions/{app_version}/; mutable data under LocalAppData/LILAClaw with data/, staging/, runtime/ and logs/ as defined in LLD-06. User-selected backup/export destinations are outside version directories and never recursively deleted by uninstall without explicit selection. Validate standard-user filesystem behavior during M7.

Bundle runtime/launcher/coordinator/worker and compiled web assets with pinned dependencies and a software inventory. Chrome extension is a separate reviewed distribution with protocol compatibility checks. No Python/Node installation requirement and no silent Windows service or login registration; startup-at-login follows the explicit owner setting.

## Release manifest contract

{manifest_version, app_version, platform, architecture, artifact_uri, artifact_size, digest_algorithm, artifact_digest, signature_metadata, protocol_min, protocol_max, schema_from, schema_to, migration_ids, release_notes_ref, minimum_supported_upgrade_version}.

Verify manifest authenticity with a trusted publisher configuration and then artifact integrity; a digest received beside an unsigned download is insufficient authentication. Reject wrong platform/architecture, oversized downloads, unknown signer, downgrade and incompatible upgrade paths with a visible reason. Never execute downloaded scripts before verification.

LLD-06 selects PyInstaller onedir, Inno Setup 6, Ed25519 manifests, Authenticode verification and rotation/activation rules. Publisher certificate/key, production feed URL and extension ID are release-owner inputs checked by production build. No publisher identity is invented here; test feeds cannot publish stable releases. Owner update confirmation remains required.

## Installation and update operation

Install: validate supported target → verify package → stage immutable version → register launcher/uninstall → initialize local store/trust → optional login-start setting → launch readiness → guide Chrome installation/pairing. Missing provider/facts/backup setup remain named readiness items, not installation failure or implied permission.

Update phases: AVAILABLE → OWNER_CONFIRMED → VERIFIED → QUIESCING → SNAPSHOT_COMPLETE → STAGED → MIGRATING → ACTIVATING → HEALTHCHECK → COMPLETE; failure records last completed phase.

Before quiescence stop new admission/dispatch, persist control state and reconcile/record in-flight uncertainty. Backup must complete before destructive migration. Stop old worker/coordinator under supervisor ownership; no old generation may dispatch after activation. Run migrations against a recoverable staged copy where practical; activation journal records the consistent version/store pair.

After activation, check schema version, crypto/key access, coordinator API, worker protocol, artifact availability and retained control state. Extension mismatch blocks mutating operations until compatible; backend update approval cannot force browser-managed extension updates.

Failure before activation leaves old version/store intact. Failure after a schema-changing activation requires a compatible recovery set and explicit restore preview; do not simply point old binaries at an incompatible new database. Preserve uncertain external actions across all recovery paths; a pre-update snapshot alone does not prove actions after that snapshot did not happen.

## Migration and uninstall

Migrations carry sequential IDs, checksums and supported from/to versions. Never silently run unknown or edited historical migrations. Preserve immutable content version identifiers and event lineage. Record backup and activation IDs so recovery can report the selected point in time.

Uninstall stops managed processes, removes startup integration and application binaries, and offers explicit retained-data versus delete-data selection. Default preserve personal data/backups. Do not delete browser-managed extension data or detached exports by assumption; show separate cleanup steps where necessary. Reinstall must not resurrect a revoked pairing from ordinary backup.

## Qualification matrix and evidence

Record exact app/extension/protocol/schema/provider versions, Windows build, CPU, RAM, disk and free space per run. Initial matrix includes supported Windows 11 Home/Pro x64, Intel/AMD represented across machines, Chrome Stable, 8 GB SSD target and 16 GB preferred configuration. No ARM64/Edge/Windows 10 support claim from incidental compatibility.

| Test group | Cases and pass condition | Functional trace |
|---|---|---|
| Q-01 Trust and commands | Impostor backend, replay, cross-origin, revoked scopes, ID reuse and stale revisions rejected | FR-003, FD-001 |
| Q-02 Search/duplicates | All FD-002 exact/manual/uncertain/repost/unknown-mandatory cases; no duplicate submit | FR-004–008 |
| Q-03 Facts and review | Approved 100-case factual set and material edits; zero unsupported factual dispatch in that set | FR-009–013, FD-003/005 |
| Q-04 Browser | Each catalog field family, upload, changed context, challenge and manual handoff; verified/uncertain outcomes correctly separated | FR-014–017, FD-004 |
| Q-05 Interruption | Before send, after send and before outcome commit; stale worker, pause/stop/restart and global holds | FR-018–019, AC-018-01–08 |
| Q-06 Privacy/recovery | Key loss, wrong key, corruption, deletion, retention, disk full and new-profile restore; no credential leakage | FR-023–028, FD-006 |
| Q-07 UI/reporting | Theme, keyboard, zoom, timezone, delayed outcomes and correction/retention coverage | FR-001–002, FR-020–021 |
| Q-08 Limits/costs | Expiry, daily counters across runs/restarts/timezone edits, unknown usage and provider timeout | FR-012–013, FR-022 |
| Q-09 Installation/update | Clean standard-user install, optional startup, duplicate launch, wrong signature, interrupted migration and rollback | FR-029 |

Use the FRD thresholds without alteration: local command/status p95 at most 2 seconds, pending/unavailable indication after 5 seconds without acknowledgment, warm start within 15 seconds in 95% of 20 baseline runs, recovery assessment within 60 seconds after dependencies available, daily backup interval at most 24 hours while continuously available, and 1 GB restore validation within 10 minutes under stated exclusions. Report raw samples and test conditions. No zero-defect guarantee outside the evaluated cases.

Record tests as planned/not-run/passed/failed with evidence links; no empty test set passes by default. Use synthetic fixtures first. Any external application submission, message, withdrawal or other live effect requires actual user action authorization, independent of document/test approval.

## Delivery order and gates

Implement the shared G-01–G-05 contracts now specified in LLD-06/07 in the M0–M8 order from LLD-08. Resolve hash locks at M0, validate trust/encryption at M1, qualify browser adapters before enabling their actions, and provision real release trust inputs before stable distribution. Do not enable incomplete adapters or plaintext fallbacks to make end-to-end demos appear successful.

Final release evidence includes BR→FR→test mapping, supported form/platform matrix, security/factual/recovery results, known limitations, UAT and explicit release approval. LLD approval alone is not authorization to publish or perform live actions.
