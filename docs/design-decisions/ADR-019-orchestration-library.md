# ADR-019 — Orchestration library

Version: 1.0  
Status: Approved — Option B: LangGraph  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-004, ADR-010, ADR-018

## Approved decision

Use LangGraph within the separate Python worker for reasoning and graph execution. The coordinator retains authoritative task state, validates proposed transitions, owns SQLite writes, checks permissions, and authorizes browser dispatch. The extension remains the browser executor.

LangGraph handles interpretation of observations, drafting, permitted-tool selection, and proposed progress. Its checkpoints must integrate with coordinator-owned persistence and must not become a conflicting source of business-task truth. The checkpoint adapter and consistency protocol remain open.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Custom Python state machine | Full control and fewer framework dependencies | Custom graph execution, pause/resume, checkpoint integration, and debugging support; not selected |
| B: LangGraph | Graph execution, checkpoint and interrupt support; already used in the answer pipeline | Integration with persistence, authority, and replay handling required; approved |
| C: Temporal | Dedicated durable workflow platform | Additional service and operational complexity for the initial single-PC installation; not selected |

The existing modules/ai/connections.py uses StateGraph and compiles without a checkpointer. That is a reuse candidate, not evidence of durable workflow recovery. No hosted LangGraph service is selected or required by this approval.

## Recovery requirements

LangGraph interrupt resumption can restart a node from its beginning. Browser actions must therefore pass through coordinator-controlled action identities, authorization, and outcome reconciliation. Replayed graph work cannot blindly repeat external side effects. A checkpoint is not evidence that LinkedIn accepted an action.

Keep business state, graph state, and pending action identities consistent across worker/coordinator crashes. Revalidate permissions and current browser observations before resumed dispatch. The library does not replace deterministic policy or verified-fact checks.

## Remaining choices and validation

Checkpoint adapter, version pinning, graph schemas, migration/retention, internal communication, and atomic persistence boundaries remain detailed design choices. Preserve coordinator database-write ownership; do not install a worker-local SQLite checkpointer that silently changes that boundary.

Validate pause/resume, worker restart, crash between checkpoint and business-state updates, duplicate proposals, stale permissions, and ambiguous browser outcomes. No implementation, dependency change, or passing recovery test is claimed.

## References

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Temporal service](https://docs.temporal.io/temporal-service)

Reviewed during the decision discussion; source review of requirements.txt and modules/ai/connections.py confirmed existing LangGraph usage.

## Approval record

Sponsor selected “optionB” in response to the explicit approval question for LangGraph within the worker with coordinator-controlled persistence and execution authority. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records the library selection only; the complete solution design and development remain unapproved.
