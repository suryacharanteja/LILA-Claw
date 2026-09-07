# LLD-08 — Implementation phases, work packages and acceptance

Version: 0.2  
Status: Approved within LLD v0.2 — see ../approval-records/LLD-v0.2-approval.md

## How implementation uses this LLD

BRD defines committed outcomes; approved FRD defines observable behavior/defaults; HLD assigns architecture; this LLD defines the contracts, algorithms, storage and build tasks. Implementers must follow all four. A technical change within a contract is ordinary implementation; changing authority, supported scope, retention, provider data handling or user-visible semantics requires an impact record and review. Do not treat coding convenience as approval to change requirements.

Phase 1 milestones below are dependency-ordered build increments, not reductions of Phase 1 release scope. All milestones and required acceptance pass before Phase 1 release review. No estimates of days/weeks are asserted without staffing and implementation evidence. Each milestone produces a reviewable commit/change set, evidence and updated traceability; no automatic deployment follows.

## Proposed repository layout

```text
src/lila/
  runtime/      launcher.py supervisor.py process_lock.py health.py
  security/     bootstrap.py pairing.py sessions.py tls.py dpapi.py
  api/          commands.py queries.py events.py uploads.py internal.py
  contracts/    generated_models.py errors.py canonical.py
  storage/      connection.py writer.py repositories/ migrations/
  domain/       tasks.py facts.py policies.py identity.py outcomes.py
  execution/    dispatcher.py ledger.py leases.py reconciliation.py
  worker/       graph.py checkpoint_http.py provider.py validation.py
  privacy/      artifacts.py encryption.py audit.py retention.py backup.py restore.py
web/src/        routes/ components/ api/ state/ accessibility/
extension/src/  service_worker.ts pairing.ts tools/ adapters/ content/
packaging/      lila.spec installer.iss release_manifest.py updater/
tests/          unit/ contracts/ integration/ fixtures/ windows/ qualification/
```

The existing Flask/Selenium program remains separate during build. Do not mutate its entry points to silently mix controllers. Reuse only reviewed functions with retained license notices and tests. Initial candidates are document generation/extraction, configuration validation and prompt examples; no direct adoption of permissive CORS, CSV operational state or Selenium execution.

## Phase 1 milestone plan

| Milestone | Inputs / dependencies | Concrete implementation work | Exit evidence |
|---|---|---|---|
| M0 — Reproducible foundation | Approved LLD; no credentials needed | Create isolated source tree, dependency locks/hashes, generated contracts, test harness, license inventory and fixture provider/browser doubles | Dependency resolution on CPython 3.12 Windows x64; schema/contract checks; reproducible import/build smoke; no floating installs |
| M1 — Trusted runtime and storage | M0 | Supervisor/locks, constrained local TLS setup, launcher pipe/bootstrap, sessions/pairing, SQLCipher store, migrations and DPAPI keys | Wrong peer/origin/replay rejected; encrypted canaries absent from DB/WAL; cold/warm start and crash/quit tests |
| M2 — Domain and controls | M1 | Tasks/runs, independent holds, facts/documents/versioning, policies/approvals, command receipts, duplicate identity and event stream | All FD-001/002/003 deterministic scenarios using doubles; race/transaction constraints hold |
| M3 — Worker and AI | M2 | Async LangGraph HTTP saver, restricted serialization, graph replay, selected provider adapter, reservations/usage, grounded draft schemas | Checkpoint conformance, stale-generation rejection, 100 factual cases on fixtures and authorized provider evaluation, no fabricated dispatch |
| M4 — Browser execution | M2; M3 for narrative journey | WSS extension authentication, selected-tab context, semantic adapters, form fingerprinting, upload capability, outcome rules | Synthetic positive/negative fixtures for every tool; wrong tab/account/domain fails closed; authorized real-site variant qualification before enabling submission |
| M5 — Full client experience | M2, integrates M3/M4 | All approved screens, admin/lightweight navigation, review/batches/manual handoff, theme/accessibility, analytics and usage | Both modes/extension agree on revisions; pending commands honest; keyboard/zoom/theme and timezone/provenance checks |
| M6 — Recovery and privacy | M1/M2; full execution integration | Consistent snapshots, portable format, restore/rekey, audit segments/corrections, retention/deletion/export and recovery UI | Cross-profile restore, fault injection, retained holds, no restored authority, 1 GB restore target and deletion/coverage checks |
| M7 — Packaging and updates | M1–M6 | Onedir builds, per-user Inno installer, optional login registration, signed feed verification, staged migration/activation, uninstall data choices | Clean-machine qualification, test-signed development feed and tamper rejection, interrupted activation recovery, no runtime dependency installation |
| M8 — Phase 1 acceptance | M0–M7 | Complete regression, performance measurements, source-to-test traceability, known limitations, operational runbook and UAT | All FRD targets met or explicitly revised; no unauthorized/duplicate dispatch, secret leak or destructive restore defect; sponsor release decision |

M5 UI scaffolding may proceed after M2 while M3/M4 are implemented; final integration requires both. M6 crypto primitives begin at M1, but end-to-end restore acceptance needs action ledger state. These dependencies avoid postponing security/recovery until the end. They do not authorize additional agents or parallel tasks by themselves.

## Graph node sequence

Graph state contains run_id, criteria_version, current_candidate_id, prepared_payload_id, fact_refs, artifact_ref, blocker_ids and last_action_id. Nodes: readiness → discover_page → classify_candidates → select_candidate → prepare_facts → draft_narrative (optional) → validate_payload → ensure_action → await_authority/outcome → record_progress → next_candidate. Every node returns JSON updates; coordinator decides authoritative transitions. Interrupt for input stores the checkpoint and exits the active AI call. Re-entry revalidates references and uses the existing logical_step_key.

discover_page and next_candidate have deterministic termination: max candidates from user run criteria, no unseen IDs on two successive pages, user stop, source exhausted or authority/time budget reached. No hidden unlimited browsing loop. Default discovery page batch is 25; if platform exposes fewer items, use observed count. User configures desired candidate count before starting; no inference that all discovered jobs are authorized for submission.

## Verification IDs and fault injection

| ID range | Required cases |
|---|---|
| T-AUTH-01..08 | Valid bootstrap; replay; expired code; impostor TLS server; wrong Origin; concurrent pair consume; revoke active socket; wrong worker generation |
| T-DATA-01..08 | DDL/FK constraints; immutable row update; interrupted staging; missing READY object; bad AEAD tag; plaintext canaries; concurrent writer/counter conflict; failed migration |
| T-CTRL-01..08 | AC-018-01..08 exactly as approved, plus independent global/task-hold assertions inside pause/resume cases |
| T-JOB-01..08 | Exact rediscovery; cross-run confirmed; manual prior; uncertain guard; proven failed retry; distinct vacancy; possible repost; unknown mandatory criterion |
| T-FACT-001..100 | FD-008 distribution: 30 known, 20 missing, 20 contradictory/stale, 20 narrative, 10 material edits; fixture truth labels are owner/reviewer-approved |
| T-BROWSER-01..10 | Context; search; text; numeric/date; option mapping; upload; changed fingerprint; final submit confirmation; challenge/external handoff; uncertain/lost reply |
| T-REPLAY-01..08 | Crash before intent; after intent; after claim before send; after send; after receipt; before outcome commit; after outcome commit; stale worker on replacement |
| T-COST-01..06 | Run cap; cross-run daily cap; timezone edit; invocation timeout; unknown/stale rates; reservation reconciliation without negative counters |
| T-PRIV-01..10 | Wrong backup key; truncated/reordered chunks; new-profile restore; deletion dependencies; old detached copy; retention boundary; disk full; last usable copy; temp cleanup; credential exclusion |
| T-UI-01..06 | Keyboard/focus; 200% zoom; themes; state resync; midnight/week/timezone; outcome correction/manual provenance/retention coverage |
| T-UPD-01..08 | Clean install; optional startup; tampered artifact; wrong signer; downgrade; crash during migration; activation health failure; uninstall preserve-data default |

Every test records test_id, requirement IDs, milestone, environment versions, fixture digest, preconditions, injected fault point, observed state, pass/fail, and evidence location. Use deterministic fixture clocks to exercise expiry/DST boundaries without changing host time. Test database begins empty per case unless a recovery test explicitly restores it. Assert both positive outcome and absence of unintended dispatch.

Test harness exposes named failpoints in dev builds only: after_intent_commit, after_send_claim, after_socket_write, after_receipt, before_outcome_commit, before_artifact_publish, after_restore_stage, before_active_pointer_replace. Production builds disable invocation of failpoints. External-effect tests require separate explicit action authorization, not just LLD approval.

## Complete BR traceability

| BR | FR / module | Delivery | Primary evidence |
|---|---|---|---|
| BR-01 | FR-001/004, web/task | P1 M2/M5 | T-UI, T-JOB |
| BR-02 | FR-002/014/018, extension | P1 M4/M5 | T-CTRL, T-BROWSER |
| BR-03 | FR-006–008, identity/search | P1 M2/M4 | T-JOB |
| BR-04 | FR-009–016, facts/resumes/forms | P1 M2–M5 | T-FACT, T-BROWSER |
| BR-05 | Networking module contract | Staged addendum | Per-recipient authority/duplicate tests |
| BR-06 | Content module contract | Staged addendum | Draft/version/publish tests |
| BR-07 | Engagement module contract | Staged addendum | Context and action-specific authority tests |
| BR-08 | Company/community module | Staged addendum | Supported action and scope tests |
| BR-09 | FR-006/014/016, catalog | P1 M4 | T-BROWSER |
| BR-10 | FR-019/024/025, recovery | P1 M2/M6 | T-REPLAY, T-PRIV |
| BR-11 | FR-020, analytics | P1 M5 | T-UI-06 |
| BR-12 | FR-021/018, UI/ownership | P1 M2/M5 | T-UI, T-CTRL |
| BR-13 | FR-003/023–027, privacy | P1 M1/M6 | T-AUTH, T-DATA, T-PRIV |
| BR-14 | FR-019/029, supervisor | P1 M1/M7 | T-REPLAY, T-UPD |
| BR-15 | FR-010/022, worker/budget | P1 M3 | T-FACT, T-COST |
| BR-16 | Telegram inbox/outbox | P2 | Identity/dedup/approval expiry tests |
| BR-17 | Schedule module | P3 | DST/overlap/missed-run/cancel tests |
| BR-18 | Channel extensions | P4 | Channel parity/authority tests |
| BR-19 | Withdrawal action modules | Staged, invitations first | Support/consequence/outcome tests |
| BR-20 | FR-012–014, policy | P1 M1/M2 | T-AUTH, T-COST |
| BR-21 | FR-029, qualification | P1 M7/M8 | Baseline performance/clean install |
| BR-22 | FR-009–010, validation | P1 M2/M3 | T-FACT |
| BR-23 | FR-012–013, approvals | P1 M2 | T-AUTH, T-CTRL, T-COST |
| BR-24 | FR-027, audit | P1 M6 | T-DATA/T-PRIV |
| BR-25 | FR-028, immutable versions | P1 M2/M6 | T-DATA/T-FACT |

## Product phases beyond Phase 1

The approved FRD explicitly requires later-phase addenda. This package is implementation-ready for Phase 1 design and defines stable extension contracts below; it does not falsely claim exact later-platform forms or every future channel is already specified.

Phase 2 Telegram adapter interface: ingest(update_id, verified numeric user/chat, command) → durable inbox; map to the same command service; persist processing before advancing long-poll offset; outbox record for notifications/approval prompts. Binding includes action_version/expiry/owner and rejects ambiguous text approvals. Run one receiver; schedule reconnect with bounded backoff. Required addendum selects UI text, exact callback payload/signature and notification policy before P2 build; no public inbound listener.

Phase 3 scheduling interface: schedule_id, revision, workflow_version, named timezone, rule, misfire_policy, overlap_policy, enabled, next_due_utc; trigger key=(schedule_id,scheduled_instant) unique and maps to run_id. Cancellation sets a future-trigger fence and separately offers stop of active run. Define DST ambiguity and skip/catch-up policy in P3 FRD/LLD review; reuse durable commands and action authority, never infer consent from a schedule alone.

Phase 4 channels implement authenticate_sender, normalize_command, deliver_event and bind_approval without adding dispatcher authority. Networking/content/company/withdrawal modules register typed action schemas, exact scopes, deterministic validation and outcome classifiers. No module obtains unrestricted CDP or bypasses the coordinator.

Those future addenda are planned release work, not unresolved Phase 1 blockers. If the sponsor wants all future-phase detailed LLD before any implementation, that is a different planning scope requiring the approved later-phase FRD decisions first.

## Release inputs versus design decisions

Owner-provisioned values: provider API key and consent/configuration, backup destination/recovery-key custody, signing key/certificate, release URL, production Chrome extension ID, and authorized test account/data. They are secrets/environment identifiers that cannot be invented in documentation. Missing values block the corresponding real integration or publication, not construction/testing with explicit doubles. Production build validates them and fails if placeholders remain.

## Definition of done

For each milestone: implemented contracts match LLD; generated schemas/types and migrations consistent; tests/evidence linked; logs scrubbed; no uncontrolled dependency/license change; known issues recorded; no off-scope live effects. For Phase 1: all M0–M8 evidence, FRD quantitative targets, full required form catalog, recovery/update proof, and sponsor UAT/release approval. LLD document approval authorizes the next agreed build gate, not automatic live operation.
