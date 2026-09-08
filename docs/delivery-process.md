# LILA Claw — Agreed delivery process

Version: 1.0  
Status: Approved process  
Recorded: 7 September 2026

Sponsor evidence: “let us document this approach, let us go ahead and follow the process goin ahead”. This approves the previously discussed sequence and document boundaries.

| Stage | Responsibility of document |
|---|---|
| BRD | Business needs, scope, outcomes, constraints, and business acceptance |
| Solution design | Feasibility, multiple options, tradeoffs, decisions, and conceptual architecture |
| FRD | Detailed functional behavior, rules, exceptions, and measurable acceptance |
| HLD | Components, interfaces, data flow, deployment, and architecture |
| LLD | Module-level schemas, API contracts, state transitions, algorithms, and errors |
| Development | Implement the approved release/module specifications |
| Testing / UAT | Verify requirements and obtain sponsor acceptance of evidence |
| Release | Obtain explicit release authorization with operational readiness and rollback |

Feasibility continues across stages. FRD and HLD are iterated together where needed. LLD is reviewed for each module or release before its implementation; future-phase detail does not hold up unrelated approved work.

Every design discussion records the problem, criteria, options, recommendation, consequences, outstanding validation, and sponsor decision. Proposed and approved ADRs remain distinct. Sponsor approves document gates with technical/QA advice where assigned. Preserve traceability from BR IDs through FRD, HLD/LLD, and tests. Material changes require recorded impact and approval; preparation is not sign-off.

Current priority: execute M0 reproducible foundation under the [approved implementation plan v1.1](implementation-plan.md), with its [32 P1 work packages and 10 later milestone entries](implementation-work-items.json). See the [conditional approval and full-scope clarification](approval-records/implementation-plan-approval.md). LLD v0.2, BRD v1.1, SD v0.31, FRD v0.3/FD v0.1 and HLD v0.1 remain approved. Implementation has not started under this planning turn. Later product phases retain their detailed addendum requirements. Native Messaging remains a future setup consideration.

For each usable milestone, the developer implements and performs relevant automated, integration, regression and smoke checks, including security/recovery verification where applicable. The owner then performs manual UAT against a supplied build and checklist with expected outcomes. Track defects, fix and retest, and record owner acceptance separately from engineering verification. Foundational milestones use engineering evidence and demonstrations until business behavior is usable. Complete integrated UAT before release and retain the explicit release authorization gate. This workflow does not require repeat approval for routine fixes within approved requirements.

## Current execution record — 8 September 2026

The owner directed completion of Phase 1 before Phase 2, then Phase 3 and later phases; see [phase sequencing](phase-sequencing.md). M0 is engineering Verified with [evidence](implementation-evidence/M0/README.md). M1 has not started. Earlier planning-time statements that implementation had not begun are historical. Business UAT and release acceptance remain pending.

Current M1 update: runtime/authentication/storage implementation and automated checks are available in [M1 evidence](implementation-evidence/M1/README.md). M1 remains In review only for temporary certificate cleanup; both technical decisions are resolved and Chrome qualification passed. M2 has not started; Phase 1 remains the only active product phase.
