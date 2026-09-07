# ADR-020 — Worker communication and checkpoint integration

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-003, ADR-004, ADR-010, ADR-018, ADR-019

## Approved decision

Use a dedicated authenticated local HTTP API between the Python worker and FastAPI coordinator. Store LangGraph checkpoints through a custom adapter that reads/writes through this API. The coordinator retains sole database-write ownership and authoritative business state.

Worker-only routes may be served by the same local FastAPI process. Worker credentials and permissions must be separate from client and extension credentials. Client/extension credentials cannot claim tasks, write checkpoints, or impersonate workers. The internal interface remains loopback-only.

## Options and rationale

| Option | Benefit | Tradeoff / disposition |
|---|---|---|
| A: Internal HTTP API | Reuses FastAPI infrastructure and preserves central state ownership | Requires internal authentication and custom checkpoint adapter; approved |
| B: Windows named pipes | OS-local communication with Windows access controls | Separate protocol and platform-specific integration; not selected |
| C: Worker directly accesses SQLite | Easier integration with some storage adapters | Changes approved coordinator-only write ownership and requires additional state-boundary design; not selected |

## Interaction requirements

- Coordinator assigns work with an ownership token so replaced or stale workers cannot continue acting.
- Worker submits proposed progress, transitions, and browser-action requests.
- Coordinator validates ownership and permissions before persistence or dispatch.
- Checkpoint adapter reads/writes through the internal API; worker does not directly mutate SQLite.
- Retried requests carry stable operation IDs to prevent duplicate operations. Define conflict handling for a reused ID with different content during detailed design.

## Consistency and recovery

A checkpoint write and an external browser action are not one atomic operation. Preserve an action ledger and reconcile uncertain outcomes before replay. The HTTP interface does not itself guarantee durable recovery or exactly-once side effects.

Validate the adapter against LangGraph checkpoint and pending-write behavior. Specify checkpoint/business-state ordering, transactional boundaries, worker replacement, and recovery from failures between steps. These details remain open; do not infer that all checkpoint writes and business transitions share one transaction.

## Remaining decisions and verification

Endpoint schemas, adapter implementation, authentication bootstrap, request timeouts, ownership expiry/renewal, payload limits, replay handling, and exact transaction boundaries remain detailed design work.

Validate unauthorized client/extension access rejection, duplicate requests, conflicting operation IDs, worker replacement, coordinator outages, pending-write recovery, checkpoint round trips, and crashes around external dispatch. No implementation or passing tests are claimed.

## Approval record

Sponsor selected “OptionA” in response to the approval question for authenticated internal HTTP and coordinator-managed checkpoint storage. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this decision only; it does not approve the complete solution design or authorize development.
