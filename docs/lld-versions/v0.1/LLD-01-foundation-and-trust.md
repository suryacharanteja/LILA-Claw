# LLD-01 — Foundation and trust

Version: 0.1  
Status: Proposed; G-01 authentication gate open  
Parent: [LLD review package](../LLD-LILA-Claw.md)

## Modules and process state

Proposed module boundaries: runtime/supervisor, runtime/launcher, api/commands, api/events, security/sessions, security/pairing, services/health, contracts/envelopes. These names describe planned code; no modules are created by this document.

Supervisor state: STARTING → READY → DEGRADED or STOPPING → STOPPED. Acquire a per-user exclusive OS lock before launching; PID files are informational only. A second launcher contacts the existing authenticated instance and opens its UI. Do not kill an arbitrary process that occupies the configured port. Persist intentional-stop state before shutdown and distinguish it from crash recovery.

Proposed health polling: every 2 seconds, report unhealthy after 3 missed responses, restart at 1/2/4-second backoff, then stop automatic retries after 3 restart attempts in 5 minutes and expose intervention required. Health checks do not wait for an AI request to finish. Shutdown allows 10 seconds for worker quiescence before termination, while coordinator preserves unresolved dispatched outcomes. Tune only with tests against the FRD targets.

Coordinator startup order: acquire owner lock → open/validate store → apply authorized compatible migrations → restore pause/stop and authority state → reconcile dispatch ledger → expose readiness. HTTP liveness can be available before execution readiness; readiness returns named blockers without secrets.

## Command processing

Request envelope: {command_id, expected_revision?, payload}. Authenticated identity is taken from the verified session, not the supplied payload. Persist (principal_id, command_id, request_digest, result_code, result_body, created_at). Same identity/ID with same digest returns the original receipt. Same ID with different content returns COMMAND_ID_REUSED. After command receipts expire, clients must resync rather than replay stale commands; business uniqueness constraints remain the durable defense.

Processing order: authenticate → authorize operation scope → validate schema/body size → check command reuse → check object revision → apply transaction → append audit/event → commit → return receipt. Dispatch-related commands commit before enqueueing any external effect. A lost reply is resolved by querying the command receipt; a timeout is not permission to issue a new logical command.

| Proposed route | Method | Contract |
|---|---|---|
| /api/v1/health | GET | Sanitized liveness; authenticated readiness details |
| /api/v1/tasks | POST/GET | Create task with criteria version / paged query |
| /api/v1/tasks/{id} | GET/PATCH | Snapshot / version-checked draft update |
| /api/v1/tasks/{id}/commands | POST | start, pause, resume, stop or restart with expected_revision |
| /api/v1/execution/commands | POST | pause_all, resume_all, quit; full command authorization |
| /api/v1/reviews/{id}/commands | POST | approve or reject exact payload version/batch membership |
| /api/v1/commands/{id} | GET | Receipt scoped to authorized owner |
| /api/v1/events | GET | Authenticated event stream with last cursor |
| /api/v1/facts, /documents, /policies | GET/POST | Scoped resources; versioned changes through commands |
| /api/v1/privacy/commands | POST | Export/deletion preparation or confirmed application |
| /internal/v1/work/acquire | POST | Long-poll acquisition; worker identity required |
| /internal/v1/work/{lease}/heartbeat | POST | Ownership generation and liveness |
| /internal/v1/checkpoints/* | GET/POST | Scoped coordinator checkpoint adapter |
| /internal/v1/proposals | POST | Draft/action proposal; never direct browser dispatch |

Pagination uses opaque cursors and bounded limits (default 50, maximum 200). General command bodies default to a 1 MiB limit; document uploads use a distinct streaming path with configurable size limits and staged validation. Reject over-limit payloads before materializing them in memory. Exact document maximum is part of artifact qualification, not a hidden restriction on approved user documents.

Errors: 400 INVALID_REQUEST, 401 AUTH_REQUIRED, 403 SCOPE_DENIED, 404 NOT_FOUND, 409 REVISION_CONFLICT/COMMAND_ID_REUSED, 413 PAYLOAD_TOO_LARGE, 422 VALIDATION_BLOCKED, 503 DEPENDENCY_UNAVAILABLE. Domain blockers can accompany a successfully persisted task command; distinguish receipt from completed execution.

## Events and reconnection

Event: {cursor, event_id, occurred_at, entity_type, entity_id, revision, kind, summary}. Summary contains minimal display data; detailed sensitive data is fetched under authorization. Client deduplicates event_id and ignores lower revisions. An expired cursor returns resync_required followed by a current snapshot; never imply an event stream is the sole durable source of truth.

Proposed heartbeat interval 5 seconds; client shows connection uncertainty after missed heartbeat/transport failure, while preserving Requested command state. Poll fallback requests snapshots at a bounded interval and stops when streaming recovers. Do not place bearer tokens in event-stream URLs.

## Trust protocol requirements — blocking detail

Distinct client/extension/worker credentials; reject cross-scope use. Session expiry, revocation and action-policy expiry are independent. Bind browser requests to permitted origins and reject cross-site state changes. Internal routes must not be accessible merely because a request is on loopback. Authenticate the server before delivering bootstrap/pairing secrets.

Proposed pairing state machine: CREATED → OWNER_CONFIRMED → CONSUMED, with EXPIRED/REVOKED terminal alternatives. One-use consumption must be atomic; concurrent attempts cannot both receive credentials. UI displays the peer/browser context to be paired. Failed authentication logs only a correlation ID and sanitized reason.

G-01 must select and specify the concrete backend identity proof, launcher-to-browser bootstrap, origin/anti-forgery mechanism, certificate/key or signed-challenge handling, session storage/rotation, revocation behavior on active sockets, and worker secret handoff. Do not implement the envelope as an authentication protocol by itself. No secret in query strings, command-line arguments, durable checkpoints or logs.

Acceptance: duplicate launcher, port collision, crash-loop cutoff, intentional Quit, replayed command with changed payload, stale revision, resync after cursor expiry, concurrent pairing consumption, impostor backend, cross-origin commands, revoked active socket and stale worker credentials.
