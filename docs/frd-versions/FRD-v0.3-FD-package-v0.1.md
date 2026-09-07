# FRD consolidated functional-decision review

Document ID: FRD-FD-REVIEW-001  
Version: 0.1  
Status: Proposed package — sponsor approval pending  
Date: 7 September 2026  
Companion: FRD-LILA-001 v0.3

## Approval boundary

Review FD-001 through FD-008 together. FD-001 retains its existing approval; all new elaborations and defaults in this package are proposed. Approval would establish the Phase 1 functional baseline and the stated later-phase scope/acceptance boundaries. Later-phase detailed FRD addenda remain required before their implementation. No proposed default is an enabled setting or execution authorization in a running application.

The main FRD's FR-001–FR-029 and acceptance criteria remain part of this package. This companion resolves functional review questions; HLD/LLD select technical mechanisms without changing these behaviors. Tests described here are future acceptance obligations, not completed results.

## FD-001 — Task controls

Retain approved Pause, Stop, Resume, Restart, Pause all and Quit behavior. Pause preserves queued work; Stop ends a run and cancels undispatched actions; Restart creates a new run with duplicate/outcome checks. Acknowledgment is required before reporting success. Closing the client alone does not stop work.

Proposed clarification: task pauses and the global pause are independent holds. Resume all clears only the global hold; it does not clear a task's individual pause or restart stopped runs. New tasks can be created while globally paused but cannot execute. A task blocked for facts, permission, budget or uncertain outcome remains blocked after Resume until the underlying condition is resolved. Pause/stop requests retain pending status across UI reconnect until reconciled with the coordinator.

Task states: Draft (not started), Queued (eligible pending ownership), Active, Awaiting input, Blocked (a dependency or authority is unavailable), Paused, Stopped, and Completed. Completion means all candidates are processed or explicitly skipped and no unresolved action remains; zero matches may complete with that explanation. Stopped runs can retain unresolved outcomes, which remain visible and block duplicate actions. State labels do not replace individual action outcomes.

Acceptance: Resume all cannot clear an individual pause; restart cannot clear an uncertain submission; acknowledged stop prevents new dispatch even after process recovery. Retain AC-018-01–08 from the main FRD.

## FD-002 — Search criteria and duplicate handling

Provide titles/keywords, location, remote/hybrid/on-site, experience level, employment type, posting age, and company inclusion/exclusion where supported. Optional salary and other criteria may be evaluated only from available evidence. Unsupported native filters may use clearly labeled post-filtering of retrieved information; never claim the platform applied an unsupported filter.

Each condition is explicitly a must-have or preference. Must-have mismatch excludes; unknown mandatory facts hold the candidate for review. Preferences rank candidates and explain tradeoffs without silently excluding them. Manual override of a mandatory condition requires an explicit criteria change for the affected scope, not an AI override. Preserve the criteria version per action; re-evaluate remaining candidates after edits.

Duplicate scope is the same applicant/account across tasks and runs. Prefer platform job ID; if absent, use a normalized canonical URL where reliable. Unresolvable identity requires review before submission. Title/company/location similarity flags a possible repost, not a definitive duplicate. Distinct vacancies can proceed under normal rules.

Confirmed prior applications and user-reported manual applications block automatic reapplication. Pending/uncertain submissions block another attempt until reconciled. A failed attempt is retryable only with evidence that submission did not occur and valid current authority. Rediscovery updates discovery metadata rather than creating another application. Deleting application history may remove duplicate evidence; show that consequence before deletion and do not promise detection of erased history.

Acceptance: test exact rediscovery across runs, manual prior application, uncertain submission after restart, two distinct IDs with similar titles, suspected repost, unknown mandatory salary, excluded company, criteria edits and missing reliable identity. Each must produce the specified skip/hold/eligible state without an unauthorized submission.

## FD-003 — Facts, drafts, resumes and approvals

Imported documents create proposed facts; they do not automatically overwrite verified values. The owner confirms facts and provenance. Explicit owner-confirmed corrections supersede prior versions. Conflicting sources require a choice; neither latest import nor model confidence establishes precedence. Let the owner mark a fact outdated; previously marked stale facts cannot be used until reconfirmed. Ask about time-dependent facts when the form requires a current answer not established by stored information; do not invent a universal automatic expiry for all facts.

Changing factual wording or values in a draft proposes a fact correction; it does not bypass verification. Narrative style edits may proceed without re-entering unchanged facts, but material changes to destination, applicant/account, resume version, submitted answers, or action type invalidate a preview approval. Standing permission is re-evaluated against the changed action rather than treated as a frozen preview approval.

Show the job/destination, applicant, selected resume/version, prepared answers, unresolved fields, and permission basis in review. Batch approval binds an enumerated set of versioned actions; adding a candidate does not inherit that approval. Missing facts cannot be supplied by approving the batch. Rejection prevents dispatch of that action version; later revision requires new validation and authority.

Resumes: support importing PDF/DOCX, selecting a version, extracting proposed facts where possible, and generating a reviewed tailored version from verified content. An unreadable/scanned document requests manual fact entry or a readable replacement; OCR is not implicitly promised. Do not fabricate employers, dates, qualifications or experience to match a vacancy. Retain the exact submitted document reference and integrity information within retention limits.

Acceptance: test conflicting imports, stale facts, unsupported experience claims, factual draft edits, changed resume after approval, adding to an approved batch, rejected drafts and corrupt files. No affected dispatch occurs until facts and current authority validate.

## FD-004 — Forms and manual handoff

The first catalog targets LinkedIn-native application journeys with contact facts, work/education facts, screening questions, narrative responses, resume upload, and final review/submission, plus job-search/filter forms. This is a functional catalog, not proof that every live variant works. HLD/LLD define detection and adapters; qualification records exact validated variants. Losing coverage of a required target must be reported as a release limitation for review, not silently accepted by shrinking the catalog.

Field rules: fill text/numbers/dates only with verified meaning and appropriate formatting; choose a dropdown/radio option only when its meaning matches a verified answer; never approximate an unknown eligibility answer. Required unfamiliar fields, consent/attestation language not covered by authority, challenges, or unexpected account/domain changes pause affected work. Do not bypass access challenges.

Manual handoff displays the job link, last known step, completed and unresolved items, selected documents, and the reason for handoff. The owner chooses Continue manually, Mark submitted, Mark not submitted, or Leave unresolved. Mark submitted is user-reported and blocks duplicates; Mark not submitted after an uncertain automated dispatch alone does not establish retry safety without reconciliation. The user can return supported unfinished work to the agent after readiness checks. No browser session credentials are included in handoff exports.

External employer sites initially receive handoff rather than automated completion. When unsupported fields are completed manually inside a supported flow, inspect the current state again before continuing; do not replay earlier steps blindly.

Acceptance: exercise each supported field family, upload failure, changed form, external redirect, challenge, manual finish and return, and ambiguous completion. Submission confirmation needs outcome evidence, not merely a clicked button or closed modal.

## FD-005 — Limits, approvals and measurable quality targets

Keep autonomy opt-in per workflow/action scope. Standing policies require an explicit expiry timestamp, per-run cap, daily cap, and applicable AI budget; no unlimited or silently populated action allowance. The owner supplies values during setup. Show optional expiry presets (1 day, 7 days, 30 days) plus custom expiry, with no preselected grant. Action limits are configurable positive integers; the daily limit applies across runs sharing the same policy, not independently per run. Tightening/revocation applies to future dispatch; a new run or restart cannot reset consumed daily authority.

Count submitted action attempts against action caps, including failed/uncertain dispatches; discovery and local preparation do not consume submission caps. Do not refund an uncertain attempt automatically. Preserve counters across restart. Show daily reset in the configured policy timezone; a timezone change must not create a second allowance for already-consumed work. Expiry uses an absolute instant displayed in local time. Unreliable time or unresolved counter state blocks dependent dispatch until reconciled.

Preview approvals expire after 24 hours by default or sooner on material change/revocation; the owner can select a shorter period. This is distinct from standing-policy expiry. Budget currency is shown explicitly; no conversion is invented. Show estimated and reported AI cost separately. Before an AI call, reserve a conservative bound using a validated price configuration and enforced output limit. If a reliable bound cannot be established under a hard monetary budget, pause AI work and request configuration; never display unknown cost as zero. Final provider billing may differ from local estimates and must be labeled accordingly.

Proposed acceptance targets, measured on the ADR-028 test baseline:

| Measure | Target and boundary |
|---|---|
| Local command acknowledgment | 95th percentile at most 2 seconds while coordinator is healthy; after 5 seconds without acknowledgment display pending/unavailable, never fabricated success |
| Status visibility | A connected client reflects persisted coordinator changes within 2 seconds at the 95th percentile |
| Warm application start | Main client usable within 15 seconds in 95% of 20 measured starts on the 8 GB SSD test machine; excludes OS boot and provider/browser readiness |
| Recovery assessment | Within 60 seconds after backend/browser dependencies are available, show recovered task state or an explicit unresolved/blocking reason; not a promise to complete external reconciliation within 60 seconds |
| Factual acceptance | Zero unsupported factual claims reaching dispatch in an agreed minimum 100-case mixed field/drafting evaluation set; no universal correctness claim |
| Authority and duplicates | Zero unauthorized or duplicate outward dispatches across the approved interruption/permission test matrix |
| Remote response time | No Phase 1 remote-service latency guarantee; measure hosted AI and platform latency separately |

The 8 GB machine is a qualification target, not a proven supported minimum. A missed target requires remediation or explicit acceptance of a revised target before release.

Acceptance also includes expiry during preparation, cap reached by another run, uncertain attempt accounting, cost-price mismatch, unknown usage, and restart/timezone changes without allowance resets.

## FD-006 — Retention, export, deletion and recovery

Proposed initial defaults are configurable and shown in administration:

| Category | Default |
|---|---|
| Verified active facts and selected current documents | Retain until replaced/deleted by owner; explain ongoing retention |
| Application records, audit events, referenced historical versions | 365 days after the associated run becomes terminal, unless needed by unresolved work |
| Unselected drafts and inactive unreferenced versions | 90 days after last use |
| Browser screenshots/detailed evidence | 30 days after terminal outcome; unresolved evidence retained with visible reason |
| Diagnostic logs | 14 days; sensitive content/credentials excluded |
| Managed backups | Daily while available, retain up to 30 days; pre-update snapshot before applying changes |

Do not silently delete the sole usable backup during rotation; if preservation exceeds retention, report the exception and request resolution. An unavailable configured external destination does not count as backup success. Never delete outside the app's managed backup set. Keep enough space for safe rotation or fail visibly. Daily housekeeping is independent of Phase 3 user-workflow scheduling.

Export offers structured JSON/CSV and selected documents with a manifest of versions, dates and outcome provenance. Default to encrypted portable export; ordinary readable export requires an explicit selection explaining its protection. Credentials are never part of ordinary export/backup. Key recovery setup requires the owner to confirm separate custody; no routine manual unlock is added.

Deletion previews affected facts/files/history and dependent active tasks, analytics and duplicate detection. Pause/cancel affected dispatch before deletion. Remove eligible content and append a minimal deletion event without retaining the deleted payload. Audit expiry uses explicit retention boundaries; do not promise indefinite lineage after authorized expiry. Display backup expiry and detached-copy limitations. On restore, apply available deletion records; an old standalone copy cannot prove newer deletion intent and must be flagged for review before resumption.

Backup target: at most 24 hours between successful scheduled snapshots while the app, disk and destination are continuously available; display missed intervals and latest success. After downtime perform one catch-up backup when available. Qualification recovery target: restore and validate a 1 GB package within 10 minutes on the baseline machine, excluding operator credential entry and external-action reconciliation. Restore begins staged, validates integrity/compatibility and shows replacement scope; invalid packages do not replace working data.

Acceptance: expired data, active references, paused deletion, disk-full, absent destination, only remaining backup, wrong recovery key, altered package, old detached restore, and migration failure. No claim of guaranteed forensic erasure or deletion of detached exports.

## FD-007 — Screens, accessibility and analytics

Main screens: onboarding/readiness; task creation and criteria; queue/task detail; candidate/application review; verified profile/documents; history/analytics; administration (connections, policies, usage, backups, export/deletion, health and updates). Lightweight mode exposes routine task creation, progress, review, results and task controls; admin mode adds full configuration. Deep links from extension open the exact task/version. Shared permissions/state remain coordinator-enforced.

Onboarding sequence: launch → readiness → browser pairing → profile/document confirmation → provider configuration → optional standing policy → task start. Save incomplete setup and explain blockers; absence of a standing policy means explicit review, not unusable installation. Recovery-key and backup destination setup are clearly visible independent steps; incomplete backup setup is not reported as protected recovery.

Support system/light/dark theme choice. All primary flows must work with keyboard-only navigation, visible focus, labeled controls and readable validation messages. Do not communicate state by color alone. At 200% zoom preserve access to primary controls; announce material status/validation changes to assistive technology without repeatedly interrupting navigation. These are product acceptance requirements, not a claim of formal accessibility certification.

Reporting timezone defaults to the Windows timezone captured during setup, editable by the owner. Display it and use Monday 00:00 as start of reporting week. Store occurrence instants so reporting timezone changes recalculate views without rewriting event history. Policy limit windows retain their separately displayed policy timezone.

Count attempts by dispatch time and final outcomes by outcome-recorded time, label these bases, and distinguish system-verified and user-reported completion. Attempt counts need not equal same-day final outcomes. An uncertain outcome later corrected to confirmed updates the action's final status without creating a second application. Total analytics reflect retained history and indicate deletions/retention coverage; never imply a lifetime total after history removal.

Acceptance: consistent state in both modes and extension, keyboard/zoom/theme review, reporting at midnight and week boundaries, timezone changes, delayed outcomes, correction and deletion effects.

## FD-008 — Release scope and acceptance package

Phase 1 release includes FR-001–FR-029 and FD-001–FD-007: supported application/discovery flows, administration/lightweight/extension surfaces, facts/documents, policy enforcement, outcome analytics, encrypted persistence, audit/privacy, recovery, installer/update and health. No first-release omission is implied by grouping implementation into increments.

Keep Phase 2 Telegram, Phase 3 scheduling and Phase 4 channel/recurrence expansion. Networking/content/company and withdrawal modules remain committed staged scope; exact release assignment is intentionally not promised here. Each later module needs a reviewed FRD addendum before implementation, including these minimum obligations:

| Module | Functional acceptance boundary |
|---|---|
| Networking | Professional relevance criteria, explicit recipient/batch membership, approved or scoped standing action authority, duplicate outreach checks, factual content and outcome history |
| Content and engagement | Reviewable user-voice drafts, grounded personal claims, action-specific publish/react/comment permissions, edit invalidation and outcome verification |
| Company/community | Explicit action catalog and entity/domain scope; unsupported actions receive explanation/handoff |
| Withdrawal | Invitations first; distinguish applications; validate support, consequences and authority before dispatch |
| Telegram | Only paired owner identity can command/approve; duplicate updates cannot duplicate actions; stale/materially changed approvals rejected; pending delivery never claimed received |
| Scheduling | Timezone, missed-run, cancellation and overlap policy explicitly configured; restart preserves state and does not authorize duplicated dispatch |
| Additional channels | Preserve the same identity, permission, privacy and audit rules; no silent cross-channel authority |

Initial qualification matrix: supported Windows 11 Home and Pro x64, Chrome Stable at release, Intel and AMD represented across test machines, 8 GB SSD baseline and 16 GB preferred configuration. Record exact builds, CPU, free space, browser/extension versions and provider/model versions in release evidence rather than assuming future versions work. Include a clean standard-user install without Python/Node developer runtimes, and all interruption/backup/update cases identified in the approved SD.

Minimum evidence suite: 100 factual cases (30 known facts, 20 missing, 20 contradictory/stale, 20 narrative grounding, 10 material edits); every FD-002 duplicate scenario; each FD-004 field family and handoff exception; interruption at before dispatch, after dispatch and before outcome persistence; permission revocation/expiry; all AC-018 controls; privacy/restore cases and numerical targets above. Prefer fixtures/synthetic data; real-site tests with external effects require explicit action authorization. Tests never authorize real applications merely by being in the suite.

Release review must include BR→FR→test traceability, measured results, known limitations, supported catalog, recovery evidence, and sponsor UAT/release disposition. No unresolved defect allowing unauthorized/duplicate dispatch, fabricated factual submission, credential exposure, or destructive recovery is acceptable for release. Failing an acceptance target requires remediation or an explicitly approved requirement change; do not relabel failure as success.

## One consolidated approval

Requested approval: FRD-LILA-001 v0.3 together with this review v0.1, including all eight FDs, proposed defaults, measurable targets, acceptance obligations, Phase 1 scope, and later-phase addendum boundaries. Approval proceeds to HLD under the agreed process; it does not claim tests passed or authorize immediate deployment. FD-001 remains approved regardless of whether the rest of this proposed package needs edits.
