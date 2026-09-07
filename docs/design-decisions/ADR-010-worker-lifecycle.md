# ADR-010 — Worker lifecycle and supervision

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Resolves: DD-010  
Source: approved BRD v1.1, BR-10, BR-14, BR-20, BR-23; ADR-001–ADR-003

## Approved decision

Run long-running agent workflows in a separate, supervised local Python worker with persisted task state. Keep FastAPI coordination separate from agent execution. Both processes use the bundled Python runtime; users do not install separate environments.

## Responsibilities

| Component | Responsibility |
|---|---|
| FastAPI coordinator | Client API, extension WebSocket, permissions, stop commands, and later Telegram integration; dispatch browser actions only under valid authority |
| Agent worker | Plan tasks, call AI, and advance workflows; request browser actions through the coordinator |
| Persistent storage | Retain queued tasks, progress, approvals, and outcomes |
| Supervisor | Start processes, detect failures, and restart with bounded retries |
| Extension | Execute authorized browser actions through its existing direct WebSocket connection to FastAPI |

## Options and rationale

| Option | Benefit | Tradeoff / disposition |
|---|---|---|
| A: Workflows in FastAPI process | Fewer processes and simpler packaging | Shared failure boundary and potential responsiveness impact from blocking work; not selected |
| B: Separate supervised worker | Isolates agent work from API handling and allows independent worker restart | Requires inter-process communication, supervision, and recovery logic; approved |
| C: Distributed task system and broker | Supports multiple workers and machines | Extra infrastructure for initial single-PC scope; Celery's documented lack of official Windows support is an additional concern for that specific candidate; not selected |

The main rationale is responsive control and failure isolation for unattended work. Separation does not guarantee responsiveness under host-wide resource exhaustion or provide a security sandbox by itself. Actual behavior requires validation.

## Recovery and control requirements

- Workflow state outlives an HTTP request or worker process. Do not use request-associated background tasks as the durable queue.
- Coordinator can block further browser dispatch when the worker stalls or the user requests stop.
- Restore persisted progress after failure; recheck permissions and reconcile uncertain external outcomes before retrying. Restart does not authorize blindly resubmitting an application.
- Stop prevents further dispatch but cannot undo an action already accepted externally.
- Prevent overlapping ownership and stale worker requests during restart. Detailed ownership and cancellation protocols belong in HLD/LLD.
- Supervisor retries must be bounded and failures visible. Process supervision does not resolve ambiguous business outcomes automatically.

## Open choices and validation

Database, schema, worker-to-coordinator transport, supervisor implementation, service versus user-session packaging, resource limits, restart timing, and deployment server remain separate choices. This ADR selects the process arrangement, not those implementations.

Later verification must cover worker crash/stall, coordinator restart, clean shutdown, stop during in-flight work, stale requests after restart, persisted approvals, duplicate prevention, and behavior on the agreed standard Windows machine. No implementation or test results are claimed.

## Reference context

Reviewed during the decision discussion: [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/), [Python process-based parallelism](https://docs.python.org/3/library/multiprocessing.html), and [Celery FAQ](https://docs.celeryq.dev/en/stable/faq.html). These inform the options; no particular process library or task framework is selected here.

## Approval record

Sponsor: “Option B: approved”, following the proposal for a separate supervised Python worker with persisted task state. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Approval covers this decision only, not the complete solution design or development. Version 1.0 records the approved decision.
