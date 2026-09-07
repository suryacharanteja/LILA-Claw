# LILA Claw — Functional Requirements Document

Document ID: FRD-LILA-001  
Version: 0.3  
Status: Consolidated review draft — approval pending  
Date: 7 September 2026  
Baselines: approved BRD v1.1 and SD-LILA-001 v0.31

## Purpose and review boundary

Specify observable product behavior, rules, exceptions, and acceptance criteria from the approved business and solution baselines. This consolidated draft covers the Phase 1 job journey and cross-cutting requirements, with explicit later-phase traceability. The [complete FD-001–FD-008 review package v0.1](FRD-functional-decisions-review.md) is an integral part of this version and supplies defaults, detailed rules and measurable acceptance criteria. FD-001 is already approved; new elaborations remain proposed. No implementation or test results are claimed.

Review this document and its companion in one approval. The companion defines functional catalog boundaries, quality/retention/budget rules and principal screen flows. Exact live variants/builds require implementation qualification, and technical mechanisms belong in HLD/LLD. Later-phase detailed addenda remain required before their implementation; this approval does not pretend their complete specifications exist.

## Actors and operating scope

The owner uses either full admin or lightweight mode in one local application. Both operate on the same tasks and permissions. The browser extension provides compact browser controls and review access. Autonomous execution uses the owner's explicitly configured authority; no separate multi-user role system is assumed.

Phase 1 targets Windows 11 Home/Pro x64 and Chrome Stable, subject to qualification. Initial hosted AI needs no dedicated GPU. Closing the web client leaves authorized background work running while the user session, backend, browser, and required authentication remain available. A logged-out or sleeping host is not represented as able to execute browser work.

## Functional requirements and acceptance criteria

Each acceptance statement is a test obligation to refine and execute later, not a claim that a test passed.

| ID | Required behavior | Acceptance criterion | BR trace |
|---|---|---|---|
| FR-001 | Provide admin and lightweight modes sharing task state | A task created in either mode appears with the same identifier and current state in the other; switching modes does not grant new execution authority | BR-01, BR-20 |
| FR-002 | Provide extension connection/tab status, review access, pause, stop, and access controls | Disconnection is visible; a review prompt opens the corresponding task; pause/stop acknowledgments are distinguishable from pending requests | BR-02, BR-12 |
| FR-003 | Pair clients explicitly and support revocation with automatic valid reconnect | A revoked pairing cannot reconnect or renew; renewing a client session does not extend an action policy | BR-13, BR-20, BR-23 |
| FR-004 | Capture job criteria and preserve the instruction version used | Search activity identifies its criteria version; changed criteria do not silently rewrite an existing action's lineage | BR-01, BR-03, BR-25 |
| FR-005 | Check readiness before executing dependent work | Missing resume/facts, unavailable browser, invalid authority, or exhausted budget yields an actionable state and blocks affected dispatch | BR-04, BR-14, BR-20, BR-22 |
| FR-006 | Search and filter using the supported form catalog | Supported criteria are applied and retained; unsupported controls cause a clear request for assistance rather than guessed interaction | BR-03, BR-09 |
| FR-007 | Present shortlist relevance tied to user criteria and available job information | Each retained job has a relevance explanation; absent job facts are not presented as known | BR-03, BR-22 |
| FR-008 | Prevent duplicate processing/submission using durable identity and action state | A rediscovered job with a known prior application is flagged; uncertain dispatch is not automatically submitted again | BR-03, BR-10 |
| FR-009 | Maintain versioned verified profile facts with provenance | Changing a fact creates a distinguishable version; affected prepared actions are revalidated before dispatch | BR-04, BR-22, BR-25 |
| FR-010 | Fill factual fields deterministically and ground narrative drafting in approved facts | Missing or contradictory facts prompt clarification; unsupported claims do not reach dispatch merely because a model is confident | BR-04, BR-15, BR-22 |
| FR-011 | Support resume selection/customization and versioned review | The resume used is identified by version; missing/corrupt artifacts block dependent execution; edits trigger revalidation | BR-04, BR-25 |
| FR-012 | Evaluate authority against exact current action details | Expired/revoked policies or materially changed approval previews block dispatch until valid authority exists | BR-20, BR-23 |
| FR-013 | Support bounded standing permissions without routine per-action prompts | An in-scope action with valid facts and unexhausted limits proceeds; an out-of-scope action cannot inherit authority from unrelated work | BR-15, BR-20, BR-23 |
| FR-014 | Execute only on permitted account/domain/tab and supported flow | Selecting another account/tab does not silently transfer permission; unsupported flow preserves progress and requests assistance | BR-02, BR-09, BR-20 |
| FR-015 | Record attempted, confirmed, failed, and uncertain outcomes distinctly | Dispatch alone cannot produce confirmed status; ambiguous results remain uncertain and block automatic duplicate submission | BR-10, BR-11, BR-24 |
| FR-016 | Provide manual handoff for unsupported/external employer forms | Handoff records progress and reason without claiming submission; owner-reported completion remains distinguishable from system verification | BR-04, BR-09, BR-24 |
| FR-017 | Pause affected work for missing information while allowing unrelated eligible work | A clarification request persists across restart; unrelated work still obeys the single execution-owner and permission rules | BR-10, BR-12, BR-22 |
| FR-018 | Apply approved FD-001 task-control semantics | Pause preserves queued work; Stop cancels undispatched actions in the current run; acknowledged controls prevent affected dispatch and reconcile in-flight outcomes | BR-02, BR-14 |
| FR-019 | Recover durable state after browser/process interruption | Recovery reconciles dispatched actions before resume; it does not renew authority or blindly replay external effects | BR-10, BR-14, BR-23 |
| FR-020 | Show daily, weekly, and total outcome analytics | Counts reconcile with recorded outcome categories; corrections are reflected without counting a single action as two confirmed submissions | BR-11, BR-24 |
| FR-021 | Provide light/dark themes and understandable status/accessibility behavior | Both themes expose readable status and controls; keyboard/focus and accessibility criteria are specified before acceptance | BR-12 |
| FR-022 | Show AI usage and enforce configured action/cost limits | The owner sees available cost/usage information; unavailable usage is not displayed as zero; exhausted applicable limits pause affected work | BR-15, BR-20 |
| FR-023 | Protect live data and local snapshots with automatic account-scoped unlock | Missing keys do not trigger plaintext fallback; ordinary valid-account restart needs no additional vault prompt | BR-13, BR-14 |
| FR-024 | Create consistent local and encrypted portable backups after setup | A successful backup contains matching database/artifact versions; failure or unavailable destination is visible; credentials are excluded | BR-10, BR-13 |
| FR-025 | Validate and preview restoration, then reconcile restored work | Invalid packages cannot replace current data; new-machine recovery uses the separate recovery mechanism and fresh credentials/pairing | BR-10, BR-13, BR-23 |
| FR-026 | Provide export and real deletion with category-specific retention | Eligible content is removed, not only marked; a minimal audit event remains where appropriate; detached-copy limitations are explained | BR-13, BR-24 |
| FR-027 | Maintain tamper-evident events and auditable corrections | A correction references the original event; detected integrity failure is visible and dependent work pauses within the stated local threat boundary | BR-24 |
| FR-028 | Preserve fact/document/draft/workflow/policy version lineage | An action can be traced to versions used, subject to explicit retention/deletion boundaries rather than fabricated missing history | BR-25 |
| FR-029 | Provide bundled install, health, optional login startup, and controlled updates | Clean-machine qualification needs no developer runtime; closing UI differs from Quit; updates reconcile work and validate health | BR-14, BR-21 |

## Job journey and state interpretation

Instruction → readiness → discovery/shortlist → preparation → authorization → execution → outcome recording → next eligible work. Authorization may use standing permission and does not imply a prompt at each transition.

Task state and action outcome are distinct: a task can be waiting for input while a previous action is confirmed; an action can be uncertain while the task is paused. FD-001 in the companion defines Draft, Queued, Active, Awaiting input, Blocked, Paused, Stopped and Completed, including independent task/global holds. Technical transition implementation belongs in HLD/LLD. Never collapse uncertain outcomes into failure simply to allow retries.

## Phase 1 form catalog for elaboration

| Catalog group | Target behavior | Boundary |
|---|---|---|
| Job search/filter | Supported LinkedIn job-discovery controls | Exact controls and variants require validation |
| Application facts | Contact, work/education history and known screening facts | Verified information only; unfamiliar meaning requires clarification |
| Application narrative | Contextual answers based on approved facts | Factual validation before dispatch |
| Resume and final review | Select/upload validated document version and authorize final action | Actual upload/transition/outcome paths must be qualified |
| External employer or unsupported flow | Preserve progress and present manual handoff | Automated completion outside initial catalog |

## Later-phase functional traceability

| BR IDs | Retained requirement and delivery boundary | Required elaboration before delivery |
|---|---|---|
| BR-05 | Professional discovery, invitations, outreach/follow-up, relationship context and batch planning; staged networking module | Exact actions, permissions, previews, duplicate rules and outcomes |
| BR-06 | Voice-aligned post drafting and authorized publishing; staged content module | Draft review, publication authority and verification |
| BR-07 | Relevant reactions/comments and professional milestone catch-up; staged module | Context and action-specific permission rules |
| BR-08 | Company/page, following, community discovery and outreach; staged module | Exact platform-supported actions and release assignment |
| BR-16 | Phase 2 private owner Telegram bot with paired numeric identities and long polling | Deduplicated commands, action-bound approval callbacks, expiration, outages and delivery uncertainty |
| BR-17 | Phase 3 recurring work | Timezone, cancellation, missed runs, non-overlap and persisted history |
| BR-18 | Phase 4 additional channels/advanced recurring work | Select extensions after use-based validation |
| BR-19 | Both withdrawal types; invitations first with networking | Exact supported cases, consequences, approval/standing policies, manual routes, and application-platform validation |

These rows preserve scope; they are not a complete later-phase FRD or a fixed release assignment for the broader suite. Phase 1 cross-cutting controls apply when those modules are activated.

## Approved FD-001 — Task controls

Approval: [sponsor record](approval-records/FD-001-task-controls-approval.md). This section is approved functional behavior; it does not approve the complete FRD.

| Control | Behavior |
|---|---|
| Pause task | Prevent further task dispatch, preserve queued work/progress, and reconcile in-flight actions |
| Resume | Continue paused work only after rechecking facts, permissions, budgets, browser availability, and unresolved outcomes |
| Stop task | End the current run and cancel its undispatched actions; preserve history and outcomes |
| Restart | Create a new run after checking duplicates and unresolved actions; do not resume the stopped run as though it were paused |
| Pause all | Pause active tasks and hold new execution until explicitly resumed |
| Quit application | Prevent new dispatch and gracefully shut down background processes, preserving recovery state |

Closing the client tab/window leaves agents running. Paused/stopped work does not automatically restart after crash or reboot. The extension exposes task controls and clearly labeled Pause all; later Telegram commands use these same meanings.

Show Requested until the coordinator acknowledges the control. An unreachable backend must not yield a false success message. Already-submitted actions cannot be undone and must retain confirmed, failed, or uncertain outcomes as appropriate.

| Acceptance ID | Scenario and expected outcome |
|---|---|
| AC-018-01 | Pause with queued and in-flight work: after acknowledgment, no new affected dispatch occurs; queued work remains and the in-flight outcome is reconciled |
| AC-018-02 | Resume after authority expires or facts change: dependent dispatch stays blocked until current checks pass |
| AC-018-03 | Stop a run: undispatched actions are canceled; history remains; restart uses a new run and checks duplicate/uncertain actions |
| AC-018-04 | Pause all while another task arrives: new execution remains held until explicit resume |
| AC-018-05 | Backend unreachable: pause/stop never appears acknowledged without coordinator evidence |
| AC-018-06 | Crash/reboot after pause or stop: persisted control state prevents automatic continuation |
| AC-018-07 | Close client versus Quit: closing preserves authorized background work; Quit prevents dispatch and initiates graceful shutdown |
| AC-018-08 | Submitted action followed by stop: UI does not claim reversal; actual or uncertain outcome remains recorded |

Acceptance cases specify future tests; none have been executed. Detailed request identifiers, race handling, acknowledgment persistence, and transition implementation belong in HLD/LLD. The companion proposes explicit independent task/global pause semantics without silently clearing user-imposed holds.

## FRD decision register

| ID | Topic | Consolidated review disposition |
|---|---|---|
| FD-001 | Pause, stop, resume and cancellation | Approved: see task-control section and approval record; implementation details remain for HLD/LLD |
| FD-002 | Search and duplicate identity | Proposed in companion: mandatory/preference criteria, exact identity, suspected reposts, manual and uncertain outcomes |
| FD-003 | Fact and draft review | Proposed in companion: owner-confirmed provenance, contradiction handling, material edits and versioned resume review |
| FD-004 | Forms/manual handoff | Proposed in companion: field rules, initial catalog, handoff choices and outcome provenance |
| FD-005 | Limits and quality targets | Proposed in companion: explicit policy grants, 24-hour preview expiry, cost bounds and measurable targets |
| FD-006 | Retention/export/deletion | Proposed in companion: category defaults, daily backup, export/deletion and recovery behavior |
| FD-007 | UI and analytics | Proposed in companion: screen flow, themes/accessibility, timezone/week boundaries and corrections |
| FD-008 | Release and validation scope | Proposed in companion: Phase 1 coverage, later-phase addenda, qualification matrix and evaluation suite |

## Consolidated approval request

Review FRD-LILA-001 v0.3 and the [functional-decision package v0.1](FRD-functional-decisions-review.md) together. Approval covers all eight FDs, proposed defaults and acceptance criteria, the Phase 1 functional baseline and explicit later-phase boundaries. FD-001 retains its earlier approval. After approval, proceed to HLD; no test success, completed LLD, immediate development or release authorization is implied. Requested changes can identify any FD/FR ID and be consolidated before approval.

## Version history

- 0.1: Initial FRD draft with Phase 1 requirements, later-phase traceability, and open functional decisions.
- 0.2: Recorded FD-001 approval and task-control acceptance criteria; advanced to FD-002. Complete FRD approval remains pending.
- 0.3: Prepared all eight functional decisions for one consolidated review, with companion v0.1 defining defaults, measurable criteria and staged acceptance boundaries. Approval remains pending.
