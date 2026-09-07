# LLD-03 — Execution, policies and AI

Version: 0.1  
Status: Proposed; G-03 adapter/provider gate open  
Parent: [LLD review package](../LLD-LILA-Claw.md)

## Task states and holds

| Command/event | Preconditions | Result |
|---|---|---|
| Start | Draft task, no existing active run | Create Queued run; readiness/authority checks determine eligibility |
| Acquire | Queued, no global/individual hold, dependencies ready | Active under a new worker generation |
| Missing facts | Active affected application | Awaiting input; other eligible candidates may proceed serially |
| Dependency/authority failure | Any nonterminal executing/queued work | Blocked with reason; no dependent dispatch |
| Pause | Nonterminal run | Set individual hold; preserve queue; prevent new dispatch before acknowledgment |
| Resume | Paused/nonterminal | Clear individual hold only; re-evaluate all blockers and global hold |
| Pause all / Resume all | Owner-authorized command | Set/clear global hold only; never restart stopped work |
| Stop | Nonterminal run | Set stop fence, cancel undispatched actions; Stopped with in-flight outcomes still reconciled |
| Restart | Stopped run | New generation/run; duplicate and unresolved-action checks still apply |
| Complete | All candidates processed or explicitly skipped; no unresolved actions | Completed, including zero-match reason where applicable |

Displayed run state is derived with terminal stop and explicit holds taking precedence over eligibility. Persist independent hold reasons rather than overwriting one enum and losing them. Store individual action outcomes separately.

## Action ledger

Action lifecycle: PREPARED → WAITING_AUTH or READY → DISPATCH_INTENT → DISPATCHED/UNCERTAIN → CONFIRMED or FAILED. CANCELED is permitted only before dispatch intent has been claimed for sending, unless reconciliation proves nothing was sent. Corrections append outcomes and recompute effective status; they do not erase the original evidence.

DISPATCH_INTENT means a durable intent exists and transmission may occur. A crash in this state is treated conservatively as possibly sent until dispatch evidence is reconciled. “Failed” must record whether no submission is established; a network timeout alone does not establish that fact.

### Dispatch algorithm

1. Receive worker proposal with run/ownership generation, payload_version and referenced facts/documents.
2. Validate all references and supported tool/schema; reject model-supplied authority or arbitrary browser instructions.
3. Begin coordinator write transaction. Read latest holds, account/tab scope, policy/approval versions, expiry/time reliability, duplicate guard and limits.
4. If blocked, persist reason without dispatch. If eligible, reserve action allowance, insert identified intent and minimal audit event, then commit.
5. Serialized dispatcher rechecks control fences and context before claiming send. A concurrently acknowledged pause must win against unclaimed dispatch. Mark the action claimed and transmit the same action_id; acknowledgment after claim explicitly treats it as in-flight.
6. On extension receipt, record transport receipt; on outcome observations, classify with the validated adapter rules.
7. Reconcile reservations to attempts conservatively. Uncertain sends keep their allowance consumed/reserved and block duplicates until resolved.

Never hold a database transaction open while awaiting browser/network/AI response. A durable outbox is a recovery ledger, not permission to blindly replay every unacknowledged browser command.

## Worker ownership and checkpoint contract

Lease: {lease_id, run_id, worker_id, generation, expires_at, allowed_work_kind}. Proposed heartbeat every 2 seconds with 10-second expiry. Expiry fences new proposals from that worker; the coordinator alone issues replacement generations. Late outcome evidence can be attached to existing actions without giving an old worker new dispatch rights.

Checkpoint adapter operations at the application boundary: read_latest(run, namespace), read(checkpoint_id), list(after_cursor), append(checkpoint,parent,expected_sequence), append_pending_writes(checkpoint,task_key,writes), and mark_terminal(run). Writes require valid scope/generation and are idempotent by checkpoint/task identity. Persist immutable checkpoint payloads with versioned serializer and bounded sizes; reject executable/deserialization formats from untrusted content.

G-03 must map these operations to the exact selected LangGraph saver API, serialization and pending-write semantics. This application contract is not a claim that these are SDK method signatures. Interrupt/replay must re-enter coordinator gates; replaying a graph node cannot generate a new external submission identity for an existing logical action.

## Duplicate identity algorithm

Scope application history by owner account and platform job identity. Stable platform ID wins; otherwise use a validated canonical URL. Unknown reliable identity blocks submission. Compare secondary normalized company/title/location information only to flag possible reposts. Exact rediscovery updates candidate metadata. A candidate confirmed distinct remains separately eligible after review.

Lookup outcomes across runs: CONFIRMED or user-reported applied → skip; unresolved/dispatch intent → hold; FAILED with evidence of no submission → policy-governed retry; possible repost → review. Deletion of history reduces available evidence and must not be presented as a clean guarantee of no previous application.

## Facts and authorization

Require verified fact versions for deterministic fields and source-grounded narrative validation. Facts imported from resumes are proposals until confirmed. An approval binds payload version, destination/account, action kind and exact enumerated batch. Material edits invalidate preview approval. Standing policies are re-evaluated against new details; they do not require repeated preview prompts when the changed action is still within valid scope.

Policy evaluation returns {allowed, reasons, policy_revision, approval_id?, limit_window_id, reservation_id?}. No truthy string or model score is accepted as authorization. Revocation/expiry applies at the latest pre-dispatch check. Daily windows use the configured policy timezone with an absolute start/end, preserve counters across restarts, and prevent allowance reset through timezone edits.

## AI invocation and costs

Provider request: {invocation_id, run_id, task_kind, approved_context_refs, output_schema_version, max_output_tokens, reservation_id, provider_config_version}. Separate tool observations from trusted instructions; never allow retrieved content to modify budget, system policy or peer identity.

Reserve conservative cost using selected provider prices/context/output limits. Use idempotent invocation IDs locally, but do not assume a provider deduplicates requests. Timeout can leave billing uncertain; retain reservation and reconcile rather than retry for free. Abort/ignore late output from a fenced worker, recording available usage without dispatching its action proposals.

Validate structured output shape, permitted field values and factual support. A schema-valid answer is not necessarily true. Invalid response → bounded regeneration only within budget or owner clarification; missing facts are not repairable through repeated creative prompting. No silent provider fallback.

G-03 closure requires exact model/provider, SDK interface, pricing source/update behavior, supported output limits, credential handoff and data-handling evaluation. No provider purchase or real personal-data evaluation is authorized by this draft.

Acceptance: crash before/after send and outcome commit; duplicate commands; checkpoint replay; old-worker proposal; stop/send race; expiry during drafting; policy timezone edits; material batch edits; ambiguous provider timeout/cost; incomplete facts and prompt-injection attempts. Zero unauthorized/duplicate outward dispatch is the approved acceptance target.
