# ADR-002 — Backend-to-extension communication

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-02, BR-10, BR-14, BR-16, BR-20, BR-23; ADR-001

## Approved decision

The TypeScript extension connects directly to the persistent Python coordinator through an authenticated local WebSocket. The main client retains its local HTTP API. The extension executes browser actions; Python owns durable orchestration.

## Options and rationale

| Option | Benefits | Costs / disposition |
|---|---|---|
| A: Native Messaging and permanent bridge | Browser-managed extension allowlist | Additional process, browser registration, and bridge-to-backend connection; not selected |
| B: Authenticated local WebSocket | Direct connection to the existing coordinator; fewer processes; aligns with OpenClaw's documented execution relay | Requires pairing, authentication, origin validation, endpoint discovery, and reconnect handling; approved |

Neither option inherently guarantees security or autonomy. Telegram commands, results, and approvals can pass through a separate adapter into the coordinator. Explicitly configured standing authority and action-specific approval rules govern autonomy independently of transport. Telegram remains later-phase scope.

## Security and recovery requirements

- Bind the browser-control endpoint to loopback; do not expose it publicly for Telegram.
- Authenticate both peers and validate allowed extension origins. Origin checks alone are insufficient. Secure pairing, credential storage/rotation, and replay protection require detailed design.
- Authenticate the intended coordinator before disclosing credentials; handle an occupied port without trusting an unrelated listener.
- Validate versioned messages, session identity, expiry, account/tab scope, and action authority; bound payload sizes and resource use.
- Persist action intent before dispatch. Receipt acknowledgement is not proof of LinkedIn completion.
- Suspend new dispatch on disconnect; reconnect with backoff, revalidate state, and reconcile uncertain outcomes before retrying outward actions.
- Maintain one account-level execution owner across browsers and sessions. Stop/revocation invalidates subsequent dispatch under stale permissions.
- Browser closure prevents browser execution while durable coordinator state can remain available. Browser startup, worker wake-up, and reconnect behavior need validation; an idle socket is not a durability strategy.

## Future scope — sponsor comment

**Native Messaging can remain a future setup helper**, if installation experience justifies it.

Retained as a future consideration, not approval to implement now. Its possible role is pairing or startup assistance. Any replacement of the approved execution transport requires a later decision.

## Remaining design and validation

Framework/library selection, endpoint discovery, authentication protocol, heartbeat and reconnect timings, installer details, and browser executor APIs remain open. Validate clean Windows installation, unauthorized peers/origins, port conflicts, revoked pairing, incompatible versions, malformed/large messages, browser/coordinator restarts, competing sessions, stop during disconnect, and duplicate-action prevention. Verify Edge separately. File upload and Telegram approval handling require their own workflow validation.

No implementation or live-workflow testing is claimed by this approval.

## Reference evidence

Reviewed during the 7 September 2026 discussion:

- [OpenClaw extension](https://docs.openclaw.ai/tools/chrome-extension): WebSocket execution relay with native setup/wake-up on supported platforms; Windows pairing differs. MacMedha reuse remains unverified.
- [Chrome worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle): lifecycle handling does not replace durable state.
- [Chrome Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging) and [Edge Native Messaging](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging): alternative connection mechanisms.

## Approval and history

Evidence: sponsor stated “Option B : approved” and requested preservation of the future-scope comment above, in task 01a0783f-92d5-78c1-b4c8-80424c720a17.

- 0.1: Initially recommended Option A for its allowlist and installer fit; never approved. Proposed a permanent bridge with possible named-pipe IPC.
- Discussion: OpenClaw research led to a revised recommendation of Option B for direct communication and fewer processes.
- 1.0: Sponsor approved Option B. Permanent bridge/IPC requirements removed from the active design. Native Messaging retained as future setup scope. This approves the transport, not the entire solution design or development.
