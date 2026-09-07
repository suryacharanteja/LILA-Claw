# ADR-015 — Telegram update delivery

Version: 1.0  
Status: Approved — Option A: long polling  
Date: 7 September 2026  
Delivery: Phase 2  
Source: approved BRD v1.1, BR-16; ADR-014

## Approved decision

Receive Telegram commands and approval callbacks through long polling from the local Python backend. Use outbound HTTPS requests to Telegram; no public inbound endpoint, tunnel, or cloud relay is required for this integration. Send previews and results through separate outbound Bot API requests.

Long polling waits for updates and returns when they arrive or the request times out. It is not infrequent periodic checking. The Telegram receiver must remain responsive independently of long-running agent work; exact task/process placement remains detailed design work.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Local long polling | Simple installation, outbound connectivity only, low operational burden | Local application must run; small recurring idle request overhead; approved |
| B: Direct webhook to PC | Push delivery without renewing idle polling requests | Reachable HTTPS endpoint/tunnel, certificates, and endpoint protection; not selected |
| C: Cloud webhook relay | Can durably receive updates while the PC is offline | Additional service, hosting, credentials, and data handling; not selected |

Long polling is selected for overall simplicity in the single-owner Windows deployment, not as a claim of universally superior efficiency. No latency/resource benchmark has been performed. A cloud relay can be reconsidered if extended offline intake becomes a requirement; it is not authorized for implementation by this decision.

## Delivery and recovery requirements

- Maintain one active update receiver per bot. Detect conflicting instances.
- Persist received updates before advancing the acknowledgement offset. Deduplicate received updates and callbacks before processing; receipt is not workflow completion.
- Recheck paired user/chat identity, action content/version, permissions, and expiry after reconnection. Transport recovery does not revive expired approvals.
- Track outgoing notifications locally and retry appropriately. An uncertain send outcome can produce duplicate notifications if retried; do not claim exactly-once notification delivery. Repeated approval messages must still reference the same controlled action and cannot trigger duplicate execution.
- Use bounded retry/backoff and respect Telegram retry instructions; expose connection failures and pending work.
- Long polling and webhooks are mutually exclusive for a bot. Any configured webhook conflict must be surfaced and deliberately resolved; do not silently discard pending updates.

## Availability limitation

Telegram retains undelivered updates for no longer than 24 hours. Commands that never reach the local application can be lost during a longer outage. Locally persisted tasks remain available. Do not equate restored connectivity with proof that all offline messages were received. Reconcile state and communicate possible gaps after extended outages.

Receiving an instruction does not make the browser available. LinkedIn execution still requires the host, browser, authenticated session, and applicable permissions.

## Remaining design and validation

Polling timeout, HTTP client/library, allowed update types, atomic inbox/offset handling, outbox retry rules, stale-command handling, and supervisor integration remain open. Validate crash between receipt and acknowledgement, duplicate updates, token revocation, rate limiting, webhook conflicts, concurrent receivers, prolonged outage, expired approvals, and uncertain notification sends.

No bot configuration, live messaging, implementation, or testing is claimed. Phase 2 sequencing remains unchanged.

## Reference

[Telegram Bot API — getting updates and getUpdates](https://core.telegram.org/bots/api#getupdates), reviewed during the discussion: long polling, acknowledgement offsets, webhook exclusivity, and update retention.

## Approval record

Sponsor stated “optionsA: approved” after comparison of long polling, direct webhook, and cloud relay efficiency and installation experience. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records approval of long polling only; it does not approve the complete solution design or authorize development.
