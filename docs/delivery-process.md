# LILA Claw — Agreed delivery process

Version: 1.0  
Status: Approved process  
Recorded: 7 September 2026


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

Current priority: consolidated review of [HLD v0.1](HLD-LILA-Claw.md). FRD v0.3 and FD package v0.1 are approved; see the [approval record and snapshots](approval-records/FRD-v0.3-approval.md). Solution design v0.31 and BRD v1.1 remain approved. HLD is proposed, including module/interface ownership, recovery/data flows and explicit protocol/dependency validation work. After HLD approval, prepare the listed LLD packages before their implementation. No implementation feasibility tests are claimed. Native Messaging remains a future setup consideration.
