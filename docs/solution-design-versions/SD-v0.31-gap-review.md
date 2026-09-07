# Solution-design consolidation and gap review

Version: 0.4  
Status: Review draft — not solution-design approval  
Date: 7 September 2026  
Baseline: BRD v1.1 and solution design v0.31 (final-review draft)

## Consolidated position

There are 27 approved ADRs: ADR-001 through ADR-006 and ADR-010 through ADR-030. Numbering gaps reflect original discussion topics subsequently resolved under later ADR numbers. Approval records select approaches; they are not implementation or feasibility test results.

The approved product is a Windows 11 x64 local application with React/TypeScript admin and lightweight modes, a compact Chrome extension, a FastAPI coordinator, and a separately supervised Python/LangGraph worker. The coordinator owns durable state and action authority. The extension executes bounded browser actions over authenticated local WebSocket transport; the worker communicates through an authenticated internal HTTP interface.

SQLite and managed artifacts hold encrypted business data. DPAPI protects local secrets/keys. Recovery combines local snapshots and encrypted portable copies, excluding authentication credentials. A minimal tamper-evident journal separates sensitive content from events. Scoped standing permissions support autonomous work within the available Windows/browser session; closing the client does not stop execution. Telegram remains Phase 2 and scheduling Phase 3.

## BRD coverage and remaining elaboration

The following covers all 25 BR IDs. Coverage means an architectural home or explicit outstanding scope, not completed FRD specifications or acceptance evidence.

| BR IDs | Architectural coverage | Remaining work |
|---|---|---|
| BR-01, BR-02 | ADR-023 client modes and compact extension | Detailed journeys must include all BR-02 controls: review prompts, pause, stop, and browser access; ADR feature summaries do not remove stop or review prompts |
| BR-03, BR-04 | ADR-016–020 verified facts, browser tools, orchestration; ADR-024 delivery | Define supported search/application journeys, duplicate identity rules, resume handling, and acceptance cases |
| BR-05, BR-06, BR-07, BR-08 | Reusable permissioned execution foundation; committed staged modules | Exact actions, platform feasibility, and release assignments remain open; no scope removal |
| BR-09 | ADR-030 initial additional catalog: job-search/filter forms; unsupported cases request manual completion | Define exact catalog entries and test supported variants in FRD and validation |
| BR-10 | ADR-004, ADR-018–021, ADR-025 | Recovery/reconciliation contracts and interruption tests |
| BR-11 | Durable outcome state and event journal | Analytics definitions and daily/weekly/total aggregation in FRD; no new analytics service selected |
| BR-12 | ADR-023 UI and coordinator execution ownership | Light/dark themes and accessibility remain required; specify execution-owner UX |
| BR-13 | ADR-011, ADR-025–027 | Export/deletion flows, retention, and recovery-key handling |
| BR-14 | ADR-021, ADR-028 | Validate session availability, health, and graceful interruption |
| BR-15 | ADR-005, ADR-016–020 | Provider/model evaluation, cost reporting and budget semantics |
| BR-16 | ADR-014–015 | Phase 2 Telegram interaction and failure cases |
| BR-17, BR-18 | BRD Phase 3/4 baseline retained | Scheduler and additional-channel design before the relevant phase; not implicitly implemented by backup maintenance |
| BR-19 | ADR-029: both withdrawals in scope, invitation withdrawal first | Validate application withdrawal support; specify cases and exact release assignments in FRD |
| BR-20, BR-23 | ADR-006, ADR-012–014 | Detailed permission matching, expiry, revocation, and material-change rules |
| BR-21 | ADR-005, ADR-028 | Measure hardware targets and package qualification; no GPU required for hosted-AI baseline |
| BR-22 | ADR-016 and coordinator policy enforcement | Factual evaluation set, contradiction cases, and dispatch validation |
| BR-24 | ADR-027 | Journal verification, auditable deletion/retention, stated local threat boundary |
| BR-25 | ADR-004, ADR-016, ADR-018, ADR-027 | Version schemas and references across facts, drafts, documents, workflow definitions, and policies |

## Gaps to resolve or explicitly disposition before complete solution-design approval

1. Scope clarification completed: ADR-029 records BR-19 withdrawal priority and ADR-030 records the initial form boundary. Exact catalog entries, withdrawal release assignments, and capability validation remain open for the relevant FRD/release. Do not silently narrow approved requirements.
2. The conceptual complete job journey and interruption/recovery behavior are included in solution design v0.31 for sponsor approval; not yet approved separately.
3. The v0.31 feasibility table records untested integrations, required evidence, and failure disposition. Approval is requested to carry implementation validation into downstream stages without claiming tests have passed. Existing authorization/document gates still apply.
4. The v0.31 AI evaluation plan covers factual quality, structured output, latency, cost, and data handling. Exact provider/model remains for evaluation and selection; no data transmission or purchase is authorized.
5. The v0.31 package explicitly retains staged scope and assigns deferred detail to FRD/HLD/LLD. MacMedha remains an optional reference, not a blocking dependency or validated reuse source.

These are review recommendations, not newly approved gates or changes to the delivery process. Final solution-design review must distinguish accepted risks from validated feasibility.

## Details assigned to subsequent documents

| Stage | Details |
|---|---|
| FRD | Exact journeys/forms, analytics, themes/accessibility, approval and interruption behavior, retention periods, recovery/performance targets, acceptance criteria, release-specific module scope |
| HLD | Trust/bootstrap protocol, interface contracts, encryption/key and portable-recovery integration, audit integrity/retention structure, checkpoint adapter boundaries, installer/update architecture |
| LLD per module/release | Endpoint/message schemas, event and data schemas, selected library integration, retry timings, migration algorithms, file lifecycle, test cases |
| Qualification and release | Clean-machine measurements, exact tested OS/browser versions, upgrade/restore evidence, browser change handling, UAT and release approval |

No detailed implementation choice may contradict an approved ADR without impact review. Future-phase details need not delay Phase 1 unless they affect its architecture.

## Review outcome

The core architectural choices are recorded. Solution design v0.31 is submitted for final review, including the proposed end-to-end journey and feasibility/risk disposition. Sponsor acceptance of that package remains pending. Following approval, prepare FRD under the agreed process; HLD and LLD remain subsequent deliverables. No implementation tests were run in this documentation review.
