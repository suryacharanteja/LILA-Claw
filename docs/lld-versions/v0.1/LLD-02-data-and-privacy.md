# LLD-02 — Data, encryption and privacy

Version: 0.1  
Status: Proposed; G-02 format/crypto gate open  
Parent: [LLD review package](../LLD-LILA-Claw.md)

## Proposed schema contracts

UUID primary keys unless noted; enforce foreign keys and NOT NULL for ownership/state/version fields. Coordinator serializes writes. Monetary amounts are integer minor units with explicit currency; revisions and sequences are integers. Schema migrations are sequential, checksummed and tracked in schema_migrations(version, checksum, applied_at).

| Table | Principal fields and constraints |
|---|---|
| tasks | id, account_id, instruction_version_id, criteria_version_id, state, revision, created_at |
| runs | id, task_id, generation, state, individual_hold, stop_requested, created_at, terminal_at; unique(task_id,generation) |
| execution_control | singleton scope, global_hold, revision; coordinator-owned |
| jobs | id, platform, external_id?, canonical_url?, identity_status; unique(platform,external_id) where external_id is present |
| candidates | id, run_id, job_id, criteria_version_id, eligibility, relevance_ref; unique(run_id,job_id) |
| applications | id, account_id, job_id, effective_outcome, provenance, revision; unique(account_id,job_id); attempts stored separately |
| facts / fact_versions | stable fact id; version id, source_ref, verification_status, value_ref, supersedes_id, created_at; immutable versions |
| documents / artifact_versions | document id; version id, encrypted_object_ref, format, integrity_ref, readiness, created_at; only READY versions dispatchable |
| draft_versions | id, application_id, content_ref, fact_version_refs, artifact_version_id, created_at |
| policies | id, revision, account/action/domain/tab scope, expires_at, run_cap, daily_cap, timezone, currency, ai_budget, revoked_at |
| approvals | id, payload_version_id, enumerated_batch_ref?, expires_at, state; no mutable approved payload |
| budget_windows | policy_id, window_id, currency, reserved, consumed, limit_revision; unique(policy_id,window_id,currency) |
| actions | id, application_id, run_id, kind, payload_version_id, authority_ref, dispatch_state, dispatch_generation, revision |
| outcomes | id, action_id, outcome, provenance, evidence_ref, supersedes_id?, occurred_at; corrections append |
| checkpoints | run_id, graph_version, namespace, checkpoint_id, parent_id, content_ref, sequence; unique(run_id,namespace,checkpoint_id) |
| audit_events | sequence, event_id, kind, entity_ref, minimal_metadata_ref, previous_commitment, authentication_ref, segment_id |
| operations | id, kind, phase, subject_ref, expected_revision, error_code; restartable export/deletion/restore jobs |
| backups | id, manifest_ref, snapshot_sequence, destination_ref, completed_at?, expiry_at, status |

Logical references above become normalized join tables or validated foreign keys in the final DDL; do not store unvalidated arbitrary JSON in place of integrity-critical relations. Enforce no two active mutating submission attempts per application using a transaction-backed uniqueness guard. Unknown job identity remains non-dispatchable until reviewed rather than manufacturing a global ID from title similarity.

## Artifact publication

1. Allocate opaque object/version ID and STAGING row. Generate destination under the managed root; never use a user filename as a path.
2. Stream into a restricted temporary file using the selected authenticated encryption format; verify size/type and derive content integrity metadata.
3. Flush and atomically rename into the managed encrypted object store on the same volume.
4. In a database transaction set READY, publish the version reference and append the event.
5. On recovery, verify STAGING items and either finish publication or delete abandoned unreferenced objects. Missing READY objects block dependent work and report corruption.

User exports are separate operations with an explicit destination/protection choice. For viewing/upload, decrypt only needed material into a restricted temporary scope, track its owner action/session, and remove it when complete or after crash cleanup. Deletion is not a forensic-erasure guarantee.

## Encryption and portable format gate

G-02 must fix encrypted SQLite build/driver, artifact authenticated cipher and versioned header, nonce generation, key separation/wrapping, audit canonicalization/authentication, journal/temp-file protection, and recovery-key derivation/wrapping. Use established libraries; no homemade cryptographic primitives.

Separate local data keys, portable recovery keys and authentication credentials. Local keys unlock through user-scoped DPAPI. A portable recovery package must decrypt on a new profile using the separately held recovery secret, without including original authentication secrets. Never copy only DPAPI-wrapped keys and call that portable recovery.

## Backup protocol

Backup operation phases: PLANNED → SNAPSHOTTING → COPYING → VERIFYING → COMPLETE or FAILED.

Coordinator briefly serializes manifest selection with metadata publication: pin required immutable READY artifacts and select snapshot boundary, obtain a consistent SQLite snapshot, then copy pinned encrypted/decrypt-and-reencrypted content through the portable format as specified by G-02. Verify every manifest item before marking COMPLETE. A checkpoint or database copy alone is not an artifact-consistent backup.

Manifest: format_version, app_version, schema_version, backup_id, created_at, snapshot_sequence, object list (opaque id, version, size, integrity information), graph/policy version information, and retention/deletion boundary metadata. Authenticate the manifest with the chosen package format. Avoid revealing sensitive filenames outside encryption. Exclude credentials/session renewals; import must establish fresh trust rather than restoring credential validity.

Retention uses approved FRD category defaults (365/90/30/14 days as applicable, backups 30 days) and active-reference holds. The daily backup job attempts one catch-up after downtime; no uncontrolled burst of missed jobs. Pinning is removed after success/failure reconciliation. Do not delete the last usable backup without surfacing the retention exception.

## Restore protocol

VERIFY package and key → STAGE isolated store → validate schemas/artifacts and migration compatibility → PREVIEW affected data and available deletion history → owner confirms → QUIESCE dispatch/workers → ACTIVATE consistent DB/object set → fresh local key/credential handling → RECONCILE with all restored tasks paused.

Maintain an activation journal so a crash chooses one complete old or new store rather than mixing them. New-host restore never trusts older pairing/session material. A failed verification leaves current data intact. An older detached copy carries an explicit history limitation; unknown later deletions or revocations cannot be inferred.

## Audit and deletion

Audit event contents are minimal and versioned; detailed sensitive payloads are separate. Cryptographic segment format remains G-02. Corrections append superseding references. Retention retirement writes an authenticated boundary describing the removed range without retaining erased payloads; verify against retained boundaries. Local host/key compromise can invalidate the evidentiary model and must not be described as impossible.

Deletion phases: PREVIEW → CONFIRMED → BLOCK_DEPENDENCIES → REMOVE_CONTENT → VERIFY → COMPLETE. Each phase is restartable. Include selected facts, artifact versions, related pending work, reporting and duplicate-history consequences in preview. Record minimal intent/completion events; do not copy removed content into the event itself. Failures remain visible and do not produce a success receipt. Available deletion manifests are applied during restore; detached exports cannot be erased remotely.

Acceptance: FK/uniqueness violations, staged file crash at each boundary, disk full, manifest mismatch, wrong key, tampered ciphertext, last-copy retention, deleted-history analytics, original-profile loss, interrupted activation and repeated deletion retries. All must respect FRD recovery targets and no-dispatch-on-invalid-state rules.
