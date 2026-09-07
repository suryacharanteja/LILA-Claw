# ADR-003 — Python backend framework

Version: 1.0  
Status: Approved — Option A: FastAPI  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-001 and ADR-002

## Approved decision

Use FastAPI as the Python backend framework for the local client HTTP API and authenticated extension WebSocket connection. Serve the compiled frontend through the backend as established in ADR-001. Future Telegram integration enters the coordinator through its own adapter; its phase remains unchanged.

## Options and rationale

| Option | Benefits | Tradeoff / disposition |
|---|---|---|
| A: FastAPI | HTTP and WebSocket support fit the API-centered client/extension architecture | Existing Flask routes need adaptation; approved |
| B: Keep Flask | Reuses the current control-panel framework | WebSockets require additional integration; async lifecycle limitations need attention; not selected |
| C: Quart | Flask-like asynchronous framework with WebSocket support | Migration compatibility requires validation; not selected because FastAPI better matches the proposed API-centered direction |

This is a fit assessment, not a benchmark claim. Reviewed Python business logic may be reused independently of the web framework. Do not infer that all existing code is suitable for reuse or must be rewritten.

## Boundaries and consequences

FastAPI provides the communication layer, not durable autonomous execution. Workflow persistence, approvals, recovery, cancellation, and duplicate prevention require their own design. Ordinary request-associated background tasks are not a durable job queue.

Worker lifecycle is a separate upcoming decision. ASGI server selection, process supervision, deployment packaging, library versions, authentication details, database, and agent orchestration implementation are not approved by this ADR. Blocking operations must not prevent connection handling or stop controls from responding; the execution design must address this.

Validate HTTP/WebSocket integration, frontend serving, authentication rejection, disconnect handling, and responsive controls during long-running work as part of later implementation verification. No implementation or benchmark has been performed under this approval.

## Sources

Reviewed during the design discussion:

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Flask async behavior](https://flask.palletsprojects.com/en/stable/async-await/)
- [Quart documentation](https://quart.palletsprojects.com/en/latest/)
- [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

## Approval record

Sponsor stated “Option A: approved” after the assistant explicitly proposed FastAPI and separated worker lifecycle from this decision. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Approval covers framework selection only; it does not approve the complete solution design or authorize development.
