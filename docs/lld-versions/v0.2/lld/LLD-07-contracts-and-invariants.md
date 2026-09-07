# LLD-07 — Data/API contracts and transaction invariants

Version: 0.2  
Status: Implementation specification — approval pending

## Normative artifacts

- [schema-v1.sql](contracts/schema-v1.sql): initial business database DDL, uniqueness/foreign keys/checks and immutable-record triggers.
- [protocol-v1.schema.json](contracts/protocol-v1.schema.json): strict typed command, state, browser and checkpoint bodies. Validate formats explicitly; JSON Schema format annotation alone is insufficient.
- [openapi-v1.json](contracts/openapi-v1.json): core mutation routes and response/error envelopes. Auth/stream/read/upload operations below complete the API surface.

All HTTP path IDs are owner-scoped. Check account ownership through FK joins rather than trusting a body account_id. Reject unknown fields and duplicate JSON keys. Unicode normalization/canonicalization precedes digest creation but never changes numeric identifiers. Enforce 1 MiB ordinary body limit; checkpoint strings individually valid restricted JSON and complete aggregate payload <=4 MiB. Documents stream separately up to 100 MiB. Browser frames <=1 MiB excluding separately paged observations. Lists maximum 200 per page, cursor scoped to query/account and expires in 24 hours.

## Auth and auxiliary routes

| Route | Request | Response and rules |
|---|---|---|
| POST /api/v1/auth/bootstrap | {token:base64url32} | {principal_id,csrf_token,expires_at}; sets secure cookie; one-use 60s; 401 on replay |
| GET /api/v1/auth/session | valid cookie | {principal_id,csrf_token,expires_at,credential_epoch}; no-store |
| POST /api/v1/auth/renew | cookie+CSRF, {command_id} | rotated session+CSRF; credential epoch validated |
| POST /api/v1/auth/revoke | {command_id,principal_id,expected_revision} | receipt; closes matching sockets and renewals |
| GET /api/v1/events | cookie; Last-Event-ID or opaque after cursor | SSE id/event/data; initial snapshot_required if expired; 5s heartbeat |
| GET /api/v1/{tasks,jobs,applications,facts,documents,policies,history,backups} | limit/after, fixed allowlisted filters | {items,next_cursor,as_of_revision,coverage}; no arbitrary SQL/filter expressions |
| GET /api/v1/commands/{id} | identity+command ID | original receipt, 404 if unknown; never resubmit under a new ID to guess |
| POST /api/v1/documents/uploads | streamed multipart plus command_id, account_id, filename | {upload_id,operation_id,status:'STAGING'}; sniff PDF/DOCX format, reject unsafe/archive bombs |
| GET /api/v1/documents/uploads/{id} | owner scope | readiness/error/version_id; extraction is bounded background work |
| POST /api/v1/documents/{id}/commands | {command_id,expected_revision,operation:select/generate/export,source_version,format:pdf/docx} | operation receipt; reviewed source facts required for generation |
| POST /api/v1/policies/{id}/commands | {command_id,expected_revision,operation:revise/revoke,policy?} | append policy version, update head, invalidate affected future dispatch |
| GET /api/v1/analytics | from/to/reporting_timezone | per-day/week totals by dispatch/outcome time, provenance and coverage; bounded 3660-day query |
| POST /api/v1/settings/commands | {command_id,expected_revision,section,value} | validated section schema: theme, timezone, retention, backup, startup, provider or updates; owner-only |
| POST /api/v1/provider/credentials | {command_id,provider:'openai',api_key} | no key echo; encrypt into auth store, redact request body logging; returns credential version ID |
| POST /api/v1/operations/{id}/confirm | {command_id,expected_revision,preview_digest} | performs only exactly previewed export/delete/restore/update scope |
| GET /internal/v1/checkpoints | run_id,namespace,checkpoint_id? | checkpoint tuple or null; generation scope checked |
| GET /internal/v1/checkpoints/list | run_id,namespace,before?,limit,filter? | checkpoint tuples, newest first; filter equality metadata only |
| POST /internal/v1/ai/reservations | invocation_id,run_id,lease_id,generation,provider_config_version,limits | reservation/bound or COST_CONFIGURATION_REQUIRED |
| POST /internal/v1/ai/results | invocation_id,reservation_id,generation,status,usage,response_ref? | idempotent usage reconciliation; late results cannot acquire dispatch rights |
| WSS /extension/v1 | Origin exact release extension ID | nonce authentication then frames described below; no commands until authenticated |

Settings value schemas: theme enum(system,light,dark); timezone valid IANA name; retention integer days 1..3650 by named category (current active facts/documents allow retain_until_deleted); backup destination opaque configured reference plus enabled boolean; startup enabled boolean; provider endpoint fixed allowlist/model exact/config rates integers and checked_at; updates stable feed configuration from signed release only. New retention changes preview affected deletion and do not silently purge on PATCH. Action grant fields cannot be embedded in unrelated settings.

Extension frames use {type,payload}: type=browser_action carries BrowserAction server-to-extension; browser_outcome carries BrowserOutcome extension-to-server; control carries {command_id,expected_revision,operation,task_id?} from an explicit extension UI gesture, with operation pause/resume/stop/restart/pause_all/resume_all. Require task_id for task operations; deny task outside the paired account and validate current revision/authority. Global commands only control holds, never settings or grant expansion. control_receipt carries Receipt; state_event carries Event; no provider/secret/admin mutation frame exists. Content scripts cannot send control frames directly; service worker verifies the extension UI sender context and normalizes the command. Pending controls use normal idempotent command service and acknowledgment semantics.

BrowserAction tool-dependent validation is mandatory after general schema validation: fill_fields requires nonempty field_values and a fingerprint; attach_document requires document_capability and fingerprint; advance_step/submit_application require expected_step and fingerprint; inspect_outcome requires existing_action_id; discover_jobs requires query; inspection tools cannot carry mutating arguments. Reject unrelated arguments rather than ignore them. Schema generators include these discriminated-union rules as model validators.

## Transaction T1: idempotent command

BEGIN IMMEDIATE → find (principal,command_id); if present compare digest and return existing result, or 409 reuse conflict → read target revision → validate command/scope → mutate records and append audit/event → insert receipt → COMMIT. Business receipts kept 365 days unless privacy deletion removes associated content; terminal action uniqueness persists as retained history. A receipt can say accepted while an operation remains in progress; do not encode external success in it. Validation errors before mutation need not create a receipt; commands that change state do.

## Transaction T2: authority and submission fence

One asyncio dispatch/control lock plus writer transaction. Check global and individual holds, run terminal state, worker lease generation, account/tab capability, current verified fact/draft/artifact versions, expiry and explicit or standing authority. Preview approval membership must match action_id AND payload_version. Check submission_guards for any prior confirmed/manual/uncertain action, per-run/daily counters and reservations. Insert intent/guard/reservations and increment relevant revision/event atomically.

Claim send under the same lock used by pause/stop acknowledgment. A claimed action is treated as in-flight from that point, even if send later fails. Release the lock before waiting for external result. Stop may acknowledge while that one action is in-flight but must not claim it was canceled. Only proof of non-submission releases a guard; uncertain/timeout never does. Cross-run confirmed/manual history adds a guard regardless of whether the old action remains in the active queue.

## Transaction T3: result and correction

Validate authenticated extension identity, action ID, claimed generation and expected job context. Duplicate identical outcome/event returns prior receipt. Conflicting later evidence creates a correction proposal, never overwrites an immutable outcome. Coordinator applies validated correction with supersedes_id, updates application projection and guard, appends audit/event, reconciles counters without negative values, commits. Owner-reported completion is a different provenance; owner 'not submitted' after uncertainty triggers inspection/review rather than automatic guard removal.

## Other integrity rules not expressible by a single FK

- facts.current_version must reference a fact_versions row belonging to that fact; the supplied DDL triggers enforce head assignment and head deletion order. Create the fact with null head before inserting its first version.
- Action run.task account, application account, policy account and approval account must agree before intent; cross-account mismatch is 403, including attempts through internal routes.
- Checkpoint namespace/parent references remain within a run; special pending writes update only their reserved index semantics. Idempotent ordinary put with same digest returns current config; different digest at same checkpoint ID is 409.
- Immutable content can be deleted only by privacy/retention operation after live dependencies are canceled/pinned/reconciled. Order deletion child-to-parent, record coverage boundary, retain active required content; do not disable foreign_keys to force cleanup.
- Money uses micro-USD internally (LLD-06), timestamps UTC for comparisons, monotonic timers for process leases. If wall time jumps backward >60s, pause expiry-dependent dispatch and report TIME_UNRELIABLE until a valid wall-time check/owner reconciliation; monotonic lease still fences workers.
- Daily window change cannot free previously spent allowance: carry used+reserved amount into the first replacement window on timezone change, with audit evidence. Policy revision tightening checks remaining limits immediately.

## Protected auth-store schema

Separate encrypted database, excluded from backup: principals(id,kind,scope_json,revision,revoked_at); credentials(id,principal_id,epoch,secret_hash,expires_at,revoked_at); sessions(id,principal_id,epoch,token_hash,csrf_hash,expires_at,renewed_to,overlap_until); pairing(id,secret_hash_or_protected_secret,server_nonce,client_nonce,attempts,expires_at,state); provider_secrets(id,provider,dpapi_blob,revision); bootstrap(hash,expires_at,consumed_at); settings_auth_epoch(singleton,epoch). Pairing secrets needed for HMAC verification are DPAPI-wrapped, not plaintext; revoke/epoch transaction closes peer sessions after commit and before admitting new dispatch.

Startup re-creates auth state on fresh installation/profile recovery. No business-data schema import may write this store. Auth-store backup is intentionally absent; user re-pairs/re-enters credentials. Schema/application migrations never log decrypted values.

## Error catalog

401 AUTH_REQUIRED/SESSION_EXPIRED/PAIRING_REPLAY; 403 SCOPE_DENIED/ORIGIN_DENIED/STALE_WORKER; 409 REVISION_CONFLICT/COMMAND_ID_REUSED/OUTCOME_UNRESOLVED/DUPLICATE_APPLICATION; 422 FACTS_REQUIRED/ARTIFACT_NOT_READY/POLICY_EXPIRED/LIMIT_EXHAUSTED/UNSUPPORTED_VARIANT/COST_CONFIGURATION_REQUIRED; 503 BROWSER_UNAVAILABLE/STORE_UNAVAILABLE/INTEGRITY_FAILURE/TIME_UNRELIABLE. retryable is true only for safe transport/read retries; mutating application outcomes require reconciliation irrespective of HTTP retryability.

## Contract verification

Validate schema-v1.sql in an isolated in-memory SQLite instance for syntax/FK/index/trigger checks; separately validate encryption/migrations using SQLCipher during M1. Validate JSON Schema syntax and OpenAPI references; generated Pydantic/TypeScript models must conform to shared schema. Structural checks do not qualify production security, live site adapters or all business constraints.
