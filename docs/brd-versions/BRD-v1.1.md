# Business Requirements Document — LILA Claw

## Document control

| Field | Value |
|---|---|
| Document ID | BRD-LIS-001 |
| Revision | 1.1 — In review |
| Date | 7 September 2026 |
| Product | LILA Claw — Local Intelligent LinkedIn Assistant |
| Tagline | Your intelligent assistant for LinkedIn. |
| Owner / approver | Product sponsor / user |
| Prepared by | Codex, product-analysis support |
| Source baseline | Approved requirements in v1.0.1 |
| Approval of this revision | Pending sponsor review |
| Change scope | Structure, navigation, supporting registers, and approved delivery-process clarification; no changes to BR-01–BR-25 |
| Review snapshot | [BRD-v1.1.md](BRD-v1.1.md) |

The sponsor confirmed that the requirements are already approved and requested a revised BRD format for final review. The v1.0.1 snapshot remains intact. This revision does not reopen the approved requirements or automatically supersede the prior baseline. Approval of v1.1 applies to this reorganized document and its presentation of the agreed process.

## Contents

1. Executive summary
2. Business context and problem
3. Stakeholders
4. Business objectives and success measures
5. Scope and operating boundaries
6. Business requirements register
7. Business processes and user journeys
8. Business rules and action authorization
9. Quality requirements and exceptional conditions
10. Assumptions, dependencies, constraints, and risks
11. Open decisions
12. Business acceptance
13. Delivery governance and approval
14. Version and change control
15. Glossary
16. References and authoring basis
17. Revision traceability

## 1. Executive summary

LILA Claw will help one professional manage LinkedIn job searching and applications, professional relationships, content, engagement, forms, companies, and communities through a primary client and browser extension. The business need is to reduce repetitive effort while preserving truthful information, user control, and accountable outcomes.

The initial delivery centers on a complete local job-search/application journey and a reliable execution foundation. Remote messaging and scheduling follow in the established order. Broader LinkedIn capabilities remain in the product scope. Standard-machine operation is required; a dedicated host and local AI inference are optional.

This BRD defines the business baseline. Technology alternatives and implementation details belong in solution design, HLD, and LLD. Quantitative benefits, budget, delivery dates, and minimum hardware remain unvalidated; this revision introduces no invented commitments.

## 2. Business context and problem

Create one intelligent browser extension experience dedicated to LinkedIn, controlled primarily from a separate client application. The product helps its operator search and apply for jobs, develop professional relationships, create content, engage with relevant content and communities, complete forms, and follow companies.

Today's repetitive browser work requires repeated data entry, context switching, and manual customization. Simple automation handles predictable fields but struggles with contextual writing and unfamiliar workflows. The desired product combines inexpensive deterministic execution with AI reasoning where customization improves the result.

The complete suite remains the product vision. A staged rollout controls delivery risk without removing requested capabilities from the roadmap.

## 3. Stakeholders

| Role | Responsibility / interest | Current assignment |
|---|---|---|
| Product sponsor | Owns scope, priorities, decisions, acceptance, and approval | User |
| Primary operator | Provides verified facts, delegates work, reviews actions and outcomes | One professional using their own account |
| Product-analysis support | Maintains requirements, options, and traceability | Codex; not an independent approver |
| Technical and QA reviewers | Assess design and verification evidence | Not assigned; no fictional signatories |
| External platform / service providers | Impose access, availability, and integration constraints | Dependencies, not project approvers |

Recruiter/business-development and multi-customer personas are not confirmed launch users. Stakeholder assignments do not expand scope.

## 4. Business objectives and success measures

Objectives are to reduce operator effort, improve relevance and customization, preserve truthful profile information, make actions accountable, and recover safely from interruption.

Measure active operator time per completed workflow, answer correction rate, verified completion rate, duplicate side effects, recovery success, model cost per completed workflow, and user-reported trust. Track job responses/interviews and meaningful networking replies as longer-term outcomes; do not attribute causation without evidence.

Numeric targets require a baseline and agreement. Proposed launch gates: no fabricated factual answers in the agreed evaluation set; no duplicate outward actions in interruption tests; all outward actions have an audit record and explicit outcome status; all unsupported cases preserve progress and stop or request input. These are acceptance proposals, not achieved results or universal guarantees.
Measurement ownership remains with the sponsor. Baselines, numeric targets, timeframes, and collection methods must be agreed before the relevant FRD acceptance gate. The absence of those values is an explicit open item, not evidence of achieved benefits. No ROI or budget estimate is asserted.

## 5. Scope and operating boundaries

- The sponsor's Windows machine with 64 GB RAM and an 8 GB GPU is one intended 24/7 host, not the minimum hardware requirement.
- The product must also work on standard consumer machines without requiring a dedicated GPU. Exact minimum and recommended specifications will be established through testing. This correction does not yet establish support for every operating system.
- Support both ordinary use while the computer/browser are available and optional always-on operation. Hosted AI enables the standard-machine path; local inference is optional and depends on hardware. Provider, cost, and data-transfer choices remain open.
- Chrome is the initial example; Edge support is also desired.
- The operator grants access to selected browser tabs for LinkedIn work.
- A full client UI provides command entry, administration, configuration, and monitoring.
- The extension executes browser work and provides a smaller secondary interface.
- Local instructions are the first interaction channel.
- Later releases introduce a messaging gateway, potentially Telegram and WhatsApp.
- Further releases introduce scheduled/cron work.
- Predictable actions avoid model calls; contextual tasks use AI.
- Delivery sequence: feasibility and BRD, then solution design, then FRD, then development.

Continuous availability means the system can receive and manage work whenever its dependencies are healthy. It does not mean continuous LinkedIn actions or guaranteed uninterrupted execution.

### Delivery scope

1. Phase 1: local client, extension, reliable execution foundation, and a complete job-search/application journey. Preserve networking/content/company modules in the backlog and stage their activation. Exact first-release breadth awaits prioritization.
2. Phase 2: authenticated messaging gateway, initially one selected channel; remote instructions, status, and required reviews.
3. Phase 3: schedules/cron with persistent history, timezone rules, non-overlap, missed-run handling, and cancellation.
4. Phase 4: optional additional channel and more advanced recurring workflows; precise scope remains open.

Broader networking, content, and company capabilities remain committed product scope subject to platform feasibility, but do not have a fixed release assignment in this baseline. They will be delivered as independently permissioned modules after the execution foundation is validated. The alternative plan's numbering (broader workflows in Phase 2, remote control in Phase 3, scheduling in Phase 4) is not adopted silently: v1.0 preserves the sponsor's earlier remote-control/scheduling sequence. Any reassignment is recorded through change control.

Excluded from the initial baseline: unrelated browser automation, multi-customer hosting, guaranteed uninterrupted or restriction-free LinkedIn operation, mandatory local model inference, automatic security-challenge bypass, and unsupported ATS workflows. These exclusions do not remove the supported full-suite LinkedIn capabilities from the roadmap.

## 6. Business requirements register

Origin C = explicitly requested; P = proposed supporting requirement. These codes record provenance, not approval. All requirements below retain their approved v1.0.1 wording; this revision is submitted for document review. Phase assignments form the recommended baseline; unresolved details are tracked in section 11.

| ID | Requirement and business outcome | Status | Proposed delivery |
|---|---|---|---|
| BR-01 | Provide a primary client for instructions, preferences, profiles, administration, queue visibility, and activity history. | C | Phase 1 |
| BR-02 | Provide an extension with compact progress, connection status, review prompts, pause, stop, and browser-access controls. | C | Phase 1 |
| BR-03 | Search jobs using user criteria, explain relevance, shortlist, and prevent duplicate processing. | C | Phase 1 |
| BR-04 | Fill job applications with verified facts and tailored narrative responses; support resume selection/customization and review. | C | Phase 1 |
| BR-05 | Support professional discovery, connection requests, outreach, follow-ups, and relationship context, including batch planning. | C | Full scope; staged activation |
| BR-06 | Draft posts in the user's voice and support authorized publishing. | C | Full scope; staged activation |
| BR-07 | Support relevant likes/reactions, contextual comments, and catch-up activity for professional milestones. | C | Full scope; staged activation |
| BR-08 | Support following companies, company/page workflows, and community discovery and outreach. Exact actions require elaboration. | C | Full scope; staged activation |
| BR-09 | Assist with other LinkedIn forms; distinguish known fields from fields needing judgment or user input. | C | Phase 1 known forms; expand later |
| BR-10 | Preserve settings, progress, and history across navigation, browser closure, and process restart. | C | Phase 1 |
| BR-11 | Show daily, weekly, and total analytics, separating attempted, confirmed, failed, and uncertain outcomes. | C/P | Phase 1 |
| BR-12 | Provide light/dark themes and understandable workflows with one clear active execution owner. | C | Phase 1 |
| BR-13 | Protect local personal information, credentials, and activity records; provide export and deletion controls. | C/P | Phase 1 |
| BR-14 | Enable the Windows host to remain available with visible health, restart recovery, and graceful pauses. | C/P | Phase 1 |
| BR-15 | Use deterministic automation for stable actions and AI for contextual customization, with cost visibility. | C | Phase 1 |
| BR-16 | Accept authenticated remote commands and deliver useful results through a messaging gateway. | C | Phase 2 |
| BR-17 | Support scheduled recurring work with timezone, cancellation, missed-run, and overlap behavior. | C | Phase 3 |
| BR-18 | Extend remote channels and scheduling sophistication as validated by actual use. | P | Phase 4 |
| BR-19 | Support withdrawal workflows. Distinguish connection-invitation withdrawal from application withdrawal; do not assume platform availability. | C | Scope clarification needed |
| BR-20 | Bind permissions to account, workflow, tab/domain, and action; preserve meaningful user control across all command channels. | P | Phase 1 |
| BR-21 | Run the core product on standard consumer machines without a dedicated GPU; keep local AI inference optional and define a tested hardware support baseline. | C | Phase 1 |
| BR-22 | Validate generated facts against approved source information; derive execution permissions through deterministic policy, never model confidence alone. | P | Phase 1 |
| BR-23 | Provide explicit, scoped, expiring and revocable action approvals; invalidate approval when material action details change. | P | Phase 1 |
| BR-24 | Maintain append-only, tamper-evident activity records with privacy controls, defined retention, and auditable corrections/deletions. Do not claim protection against every privileged host modification. | P | Phase 1 |
| BR-25 | Preserve version history for requirements, approved profile facts, drafts, resumes, workflow definitions, and authorization policies so execution can be traced to the versions used. | P | Phase 1 |

Gender-based targeting from the original concept is excluded under the accepted earlier recommendation. Professional relevance replaces it. Random delays are not an account-safety guarantee. Unrestricted access to unrelated browser tabs is not necessary to fulfill the stated selected-tab vision.

## 7. Business processes and user journeys

### Job application

The user defines roles and constraints, reviews the ranked shortlist and matching reasons, delegates supported applications, and sees a tailored answer/resume preview where required. The system pauses on missing facts, verifies completion, and reports outcomes with evidence. Unknown outcomes are reconciled before any retry.

### Networking and content

The user sets professional audience, purpose, tone, and boundaries. The product proposes relevant recipients or content with rationale, supports editing, and executes only within the applicable authorization. The history retains enough context to avoid repetitive outreach and duplicate engagement.

### Local and future remote operation

The local client shows extension connectivity and selected tabs. Commands become trackable work items. A future remote command enters the same permission, queue, review, and reporting flow; messaging does not provide a bypass. Scheduled work uses the same flow and pauses when browser access or required authorization is unavailable.

### User-centered discovery and validation

Every feature must begin with a user need, not a proposed automation technique. During discovery, capture the trigger, current pain, desired outcome, constraints, and how success would be recognized. Map the journey before specifying screens or tools.

Provisional primary persona: one professional operating their own LinkedIn account on a standard personal computer, initially Windows. A dedicated always-on PC is an optional deployment. Job seeker, professional network builder, and content author are different journeys for this operator. Recruiter/business-development usage was present in the original concept but is not yet a confirmed launch persona.

Core jobs to be done:

- Find relevant opportunities and submit truthful, tailored applications with less repetitive effort.
- Maintain useful professional relationships without losing context or sending irrelevant outreach.
- Express the user's own expertise and voice through posts and comments.
- Delegate work locally, see what happened, intervene easily, and later issue commands remotely.

Design principles: visible control; evidence-backed personalization; progressive disclosure; accessible status and stop controls; explainable choices; recoverable failures; minimal repeated questions; economical use of AI; privacy by default.

Validation plan before development: review representative journeys with the sponsor; prototype the main client and compact extension panel; walk through successful and interrupted workflows; validate review effort and understanding of status. Low-fidelity prototypes are a later discovery deliverable, not created in this version.

## 8. Business rules and action authorization

This flow governs actions performed by the future product. It does not request permission to perform such actions now.

### Authorization defaults

| Action class | Default authorization behavior |
|---|---|
| Read/search selected LinkedIn tabs | Run under a user-started workflow and its bounded access permission; avoid repeated approval for every read. |
| Local drafts and known-field preparation | Run under workflow permission, using verified facts; no outward submission implied. |
| Sending applications, invitations/messages, publishing posts/comments, reactions, following, or withdrawals | Require a preview and explicit approval for the action or a defined batch by default. A future standing policy must be deliberately configured for the specific supported action class. |
| Missing facts, ambiguous choices, changed recipient/account or content | Request the missing information or a fresh decision; approving an unsupported guess is not a substitute. |
| Account challenge, legal attestation, sensitive declaration | Pause for user handling or explicit applicable decision; no inferred authorization. |
| External AI data transfer | Require clear provider/data-use choice during setup; do not imply that local storage means all processing remains local. |

### End-to-end flow

1. Authenticate the local or remote operator and establish the account, tabs, workflow, and action scope.
2. Prepare the proposed action from current page state and versioned user facts; validate required fields and evidence.
3. Present a readable preview with recipients/job IDs, content, attachments, action count, exclusions, and unresolved questions. For batches, permit item inspection and exclusion.
4. Record approve, edit, reject, or defer. An approval record includes approver identity, action/batch ID, approved content and attachment version, account, scope, issue time, expiry, and policy version. Exact expiry defaults belong in the FRD.
5. Before dispatch, recheck permission, expiry, revocation, limits, account/tab identity, and whether material details changed. Edits to recipients, facts, answers, attachments, or published content invalidate the affected approval.
6. Execute the approved scope once through the active workflow owner. Repeated remote messages or callbacks must not create duplicate approval or execution.
7. Verify the outcome and record confirmed, failed, or uncertain. An uncertain external result must be reconciled before retry; approval alone is not proof of success.

Pause and emergency stop are always accessible. Revocation blocks undispatched actions; it cannot undo an action already accepted by LinkedIn. Retries must remain within the original authorization and require re-review if material details change. Remote commands and schedules use the same authorization rules; a schedule does not create perpetual approval. Persist approvals and revocations across restarts, while revalidating external state before resumed execution.

## 9. Quality requirements and exceptional conditions

| Condition | Required business behavior |
|---|---|
| Missing, contradictory, or stale applicant information | Request clarification; do not guess or silently reuse conflicting facts. |
| Sensitive or consequential form choices | Use explicit user facts/preferences and applicable review policy. |
| Changed layout, conditional fields, unsupported language | Reassess the page; stop if the target cannot be identified reliably. |
| Duplicate jobs, commands, callbacks, or schedule events | Detect repeats and avoid duplicate external actions. |
| Network loss during submission/publication | Record uncertainty; inspect actual outcome before retrying. |
| Wrong account or tab; user starts manual interaction | Stop or yield ownership; revalidate context before resuming. |
| Invalid resume or upload rejected | Block completion until correct attachment is verified. |
| Logout, challenge, restriction, or platform limit | Pause and explain required user action; no automatic bypass. |
| Browser/worker/service crash; Windows restart | Restore durable work state; recheck prerequisites before executing. |
| PC asleep, logged out, offline, or updating | Report unavailability; do not claim work executed. |
| AI outage, invalid output, excessive cost | Preserve progress; use valid deterministic fallback or pause. |
| Malicious instructions within posts or job descriptions | Treat page content as data, not trusted commands. |
| Stop during an in-flight action | Prevent further dispatch and reconcile the action already sent. |
| External ATS redirect | Use an explicitly supported workflow or hand off; do not claim universal coverage. |
| Data corruption, storage full, failed update | Prevent unsafe continuation; expose recovery and rollback options. |
| Missed or overlapping scheduled run | Apply explicit skip/catch-up and serialization rules. |

The FRD will turn these categories into testable cases. Exhaustive coverage of an evolving external platform is not a credible promise.

## 10. Assumptions, dependencies, constraints, and risks

The following register organizes existing baseline concerns; it adds no new feature or acceptance threshold. Sponsor owns business disposition; technical investigation belongs to solution design.

| Category | Existing condition | Business consequence / treatment | Resolution point |
|---|---|---|---|
| Assumption | One operator and one LinkedIn account | Revisit scope before multi-account or customer hosting | Scope change |
| Assumption | Ordinary consumer hardware can support the bounded workload | Benchmark before publishing specifications | FRD and release verification |
| Dependency | Browser, account session, power, and network are available | Pause and preserve progress when unavailable | Workflow design and testing |
| Dependency | MacMedha reuse has not been verified | No required dependency until access and review succeed | Component selection |
| Constraint | No dedicated GPU required | Optional local inference; provider/data choice remains explicit | Solution design |
| Constraint | Budget, dates, staffing, and numeric service targets are unspecified | Do not infer a financial case, SLA, or delivery commitment | Sponsor planning / FRD |
| Risk | Platform changes or access restrictions | Supported workflows only; account restrictions pause execution | Platform assessment and release |
| Risk | Unknown answers or incorrect attachments | Verified facts, review, and attachment checks | FRD acceptance cases |
| Risk | Interrupted external actions | Preserve uncertain outcomes and reconcile before retry | Recovery design and tests |
| Risk | Sensitive information exposure | Apply established privacy, authorization, and retention requirements | Design and release review |

Likelihood and impact ratings have not been assessed; none are invented here. Historical feasibility and repository research are preserved in the [supporting appendix](../BRD-v1.1-supporting-context.md), rather than presented as settled business requirements.

## 11. Open decisions

The following items can remain open at business-baseline approval because their interim boundaries are explicit. They must be resolved before the indicated dependent work. The sponsor is the accountable decision owner; technical proposals are prepared during solution design.

| ID | Decision | Interim boundary | Required before |
|---|---|---|---|
| D-01 | MacMedha access and reuse | Reference only; no unverified code dependency | Selecting reused components |
| D-02 | Customer/multi-account deployment | One operator and one LinkedIn account initially; multi-tenancy excluded | Expanding business scope |
| D-03 | Broader-suite release assignments | Job journey is the Phase 1 minimum; other modules remain roadmap scope | Release-specific FRD approval |
| D-04 | Web or desktop client; gateway packaging | Local primary client plus compact extension; stack undecided | Solution-design approval |
| D-05 | Action-specific autonomy | Section 8 defaults; broader standing authority requires explicit configuration | Relevant workflow FRD approval |
| D-06 | AI providers, budget, data transfer | No required local GPU; hosted inference optional with informed opt-in | Solution-design approval |
| D-07 | Minimum hardware, browser/OS versions, language and workload | Windows-first, Chrome-first, Edge desired; no untested support claims | FRD criteria, then release verification |
| D-08 | Communities, pages, other forms, withdrawal semantics | Only explicitly supported actions; application withdrawal not presumed available | Respective module FRD approval |
| D-09 | First remote channel and conversation type | One authenticated owner channel first; WhatsApp route unselected | Phase 2 design approval |
| D-10 | Full remote client access | Messaging gateway only in initial remote scope | Any remote UI expansion |
| D-11 | Availability, cost, retention, backup and recovery targets | No availability SLA or infinite retention promised | FRD approval |
Subsequent disposition for D-04: the sponsor approved a local React/TypeScript web client, TypeScript extension, and Python backend in [ADR-001](../design-decisions/ADR-001-local-client-and-language-boundaries.md). Packaging details remain open. The original decision row is retained for lineage; its “stack undecided” wording describes the v1.0.1 review state, not the current ADR status.

## 12. Business acceptance

Before development, the approved FRD must map every in-release BR to observable acceptance criteria and tests. Before release, demonstrate:

- The core job journey on the agreed standard-machine configuration without a dedicated GPU, with measured memory/CPU, responsiveness, and AI cost.
- Truthful factual answers and verified intended attachments in the evaluation set; unsupported answers pause for information.
- No duplicate external actions in the defined restart, timeout, repeated-command, and overlapping-run tests.
- Correct approval expiry, revocation, edited-draft invalidation, wrong-account protection, and emergency-stop behavior.
- Explicit confirmed/failed/uncertain reporting and recovery from browser/gateway interruption without silently resubmitting.
- Secrets excluded from logs, restricted browser access, defined data export/deletion and backup restoration.
- Usable client and extension journeys, including keyboard access, readable status, and actionable error messages.

These are required evidence categories, not claims of completed testing. Quantitative thresholds, test fixtures, test environment, sample sizes, and severity-based defect acceptance must be set at Gate C. The sponsor accepts release limitations explicitly. Broader modules and future channels/scheduling repeat the same release gates for their own scope.

## 13. Delivery governance and approval

The sponsor approved the sequence: **BRD → solution design and feasibility/options → FRD → HLD → LLD → development → testing/UAT → release**. FRD and HLD inform each other; LLD is prepared per module or release slice. See the [agreed delivery process](../delivery-process.md).

| Review | Required result | Approval responsibility |
|---|---|---|
| BRD | Business scope, requirements, constraints, and open boundaries understood | Sponsor |
| Solution design | Feasible approach, options, tradeoffs, and ADRs reviewed | Sponsor; technical advice where assigned |
| FRD | Detailed behavior and measurable acceptance traced to BR IDs | Sponsor; QA/technical advice where assigned |
| HLD / LLD | Architecture and implementation detail reviewed for the relevant release/module | Sponsor; technical advice where assigned |
| Verification / UAT | Evidence against approved acceptance criteria and defect disposition | Sponsor accepts evidence |
| Release | Installation, rollback, limitations, operations, and platform-access assessment | Sponsor explicitly authorizes release |

This elaborates the prior delivery gates with the sponsor-approved HLD/LLD steps. An individual ADR approval does not approve the complete solution design. Document approval does not grant runtime authority for LinkedIn actions. Unassigned reviewers are not treated as completed reviews.

### Revision approval record

| Revision | Decision | Evidence |
|---|---|---|
| 1.0.1 requirements | Approved baseline | Prior progression approval and sponsor's current confirmation that requirements are already approved |
| 1.1 reorganized BRD | Pending final review and approval | No sign-off inferred from the instruction to prepare it |

Review should confirm requirement preservation, business scope, organization, open-item accuracy, and the agreed delivery process. Approval wording may be: “I approve BRD-LIS-001 v1.1.” Changes requested will be incorporated before sign-off. Prior approval history is preserved in the [approval record](../approval-records/BRD-v1.0.1-approval.md).

## 14. Version and change control

Use MAJOR.MINOR.PATCH versions after v1.0. A major change alters the business purpose, operating model, or removes/changes committed scope incompatibly. A minor change adds or materially adjusts requirements, phases, approval rules, or acceptance expectations. A patch corrects wording or formatting without changing meaning. Versions 0.1 and 0.2 were discovery drafts.

- Keep the canonical Markdown file as the latest working document. Preserve version snapshots in docs/brd-versions/; do not overwrite an approved snapshot.
- The v0.2 source snapshot and v1.0 review snapshot are retained. v0.1 is documented in the historical change log but its exact file was not archived; do not reconstruct it as an authentic snapshot.
- Record each approval separately against its exact snapshot/version. When Git is used, include the commit reference and an annotated baseline tag such as brd-v1.0 after approval. No Git commit or tag is implied by this document.
- Keep BR IDs stable. Retired requirements remain recorded as retired with rationale; never reuse their IDs. FRD items, tests, defects, and release notes trace back to BR IDs.
- Keep a change log containing version, date, author, affected requirements, rationale, decision, and approval reference. An editorial patch can be owner-reviewed without repeating the full gate; any business-impacting change requires sponsor approval.
- The last approved baseline remains effective while a proposed revision is reviewed. Downstream documents must identify their source BRD version; assess and update their traceability when the baseline changes.

### Change-request flow

Submit CR → assess scope/UX/cost/schedule/security/testing impact → propose disposition and new version → sponsor approves, rejects, or defers → archive the new baseline and decision → update affected design/FRD/tests. Do not implement an unapproved material change simply because it appears in the working copy.

Each CR records: CR ID, requester/date, current baseline, affected BR IDs, current versus proposed behavior, business rationale, options, dependencies and impact, reviewer recommendation, sponsor disposition/date, target version/release, and downstream updates. The exact approval statement or record reference is retained. CR-001: Sponsor requested and authorized the project naming update to LILA Claw, expanded as Local Intelligent LinkedIn Assistant, with the tagline Your intelligent assistant for LinkedIn. Disposition: applied in v1.0.1 on 6 September 2026. Editorial naming change only; requirement IDs, scope, and phase assignments are unchanged. Evidence: sponsor message “go ahead and update it” following the naming proposal. Overall BRD approval remains pending.

### Revision history

v0.1: captured initial suite requirements, client/extension operating vision, Windows host, hybrid execution, later messaging and scheduling; added feasibility assessment, proposed phases, design-thinking approach, and unresolved decisions. Requirements discovery remains open.

v0.2: corrected reference to OpenClaw/MacMedha; recorded repository retrieval limitation; added standard-machine support and optional dedicated-host/local-inference modes. Reviewed the sponsor's separately prepared plan: its component breakdown is a useful solution-design input, while its different phase order remains a proposal rather than a change to the BRD baseline.

v1.0: consolidated final-for-approval BRD; added document control, requirement provenance, standard-machine constraints, logical architecture responsibilities, independent authorization validation, tamper-evident audit requirements, controlled decision register, version control, document sign-off, runtime action approval, and delivery acceptance gates. Sponsor approval pending.

v1.0.1: applied sponsor-authorized product name LILA Claw, expansion Local Intelligent LinkedIn Assistant, and tagline. Preserved v1.0 snapshot; no scope change or overall BRD approval inferred.
The approval-pending statements above are historical records of their respective preparation dates. Subsequent approval is recorded separately.

CR-002 / v1.1, 7 September 2026: sponsor requested BRD restructuring while preserving approved requirements. Reorganized content; added stakeholder and consolidated risk/constraint views; retained all 25 requirement rows verbatim; moved historical feasibility/reuse content to a linked appendix; reflected separately approved HLD/LLD delivery-process clarification. Preparation authorized; v1.1 final review approval pending. Minor version used because the approved governance elaboration is included alongside editorial reorganization. Scope and feature phase assignments unchanged.

## 15. Glossary

| Term | Meaning in this project |
|---|---|
| BRD | Business Requirements Document: needs, scope, outcomes, and constraints |
| FRD | Functional Requirements Document: detailed behavior, rules, and acceptance |
| HLD / LLD | High-Level Design / Low-Level Design |
| ADR | Architecture Decision Record: options, rationale, status, and consequences |
| ATS | Applicant Tracking System; external workflows require explicit support |
| Confirmed / failed / uncertain | Distinct external-action outcomes; attempted does not mean completed |
| C / P | Original requirement provenance: explicitly requested / proposed supporting requirement; not current approval status |

## 16. References and authoring basis

Research date: 7 September 2026. Structure informed by the publicly published [Microsoft HVE-Core BRD template](https://github.com/microsoft/hve-core/blob/main/.github/skills/project-planning/requirements-author/templates/brd/brd-full.md) and [Microsoft Learn requirements guidance](https://learn.microsoft.com/en-us/dynamics365/guidance/implementation-guide/process-focused-solution-define-requirements).

Microsoft HVE-Core Team attribution: template identifies CC-BY 4.0. Adaptation uses its broad organization of context, stakeholders, objectives, requirements, constraints, acceptance, traceability, risks, and sign-off. Project content comes from the approved LILA Claw baseline. No claim of Microsoft endorsement or a company-wide mandated format is made.

Searches did not locate a comparable official public Google or OpenAI BRD template. Third-party Google Docs templates and community posts are not official company standards. This is a project-tailored BRD, not claimed certification against a universal standard. The Microsoft template also includes functional detail; this project keeps detailed FR specifications in its separately agreed FRD. Its identifier conventions and example thresholds are not imported over approved project requirements.

Historical external research references remain in the supporting appendix with their original date and verification limitations. No new platform-feasibility assessment is asserted by this editorial revision.

## 17. Revision traceability

| v1.0.1 source | v1.1 destination | Treatment |
|---|---|---|
| §1 Vision | §2 | Retained verbatim |
| §2 Design thinking | §7 | Retained verbatim |
| §3 Operating vision | §5 | Retained verbatim |
| §4 Objectives | §4 | Retained; missing measurement details explicitly tracked |
| §5 BR-01–BR-25 | §6 | Every requirement row unchanged, including delivery and provenance |
| §6 Journeys | §7 | Retained verbatim |
| §7 Exceptions | §9 | Retained verbatim |
| §8 Feasibility / §9 Reuse / §12 Sources | Supporting appendix | Retained verbatim as historical supporting context |
| §10 Phases | §5 | Feature phase assignments unchanged |
| §11 Decisions | §11 and §5 exclusions | Retained; cross-reference corrected; D-04 later disposition annotated |
| §13 History / §16 Change control | §14 | Retained with subsequent-status clarification |
| §14 Action approvals | §8 | Retained verbatim |
| §15 Document approvals | §13 and delivery process | Current approval status and agreed HLD/LLD steps made explicit; original remains archived |
| §17 Acceptance | §12 | Retained verbatim |

Detailed BR-to-FR-to-design-to-test mapping will be created with those downstream artifacts. This table is editorial lineage, not a claim that implementation or test coverage exists.
