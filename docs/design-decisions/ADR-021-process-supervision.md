# ADR-021 — Process supervision and startup

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-10, BR-14; ADR-010, ADR-011, ADR-020

## Approved decision

Run a background supervisor under the operator's Windows user account. Support manual launch and an explicit optional Start at Windows login setting. The supervisor manages the coordinator and separate agent worker.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Manual launch only | Simple startup model | Remote commands unavailable until manually launched after login; not selected as the only mode |
| B: User-session supervisor | Fits the interactive browser and user-scoped credentials; optional login startup | Requires the appropriate Windows user session; approved |
| C: Windows service | Background components can start before login | Complicates interactive browser access and user-scoped credential handling; not selected |

This supports autonomous operation without keeping the client UI open. It does not introduce a Windows service or automatic Windows login.

## Approved behavior

- One launcher starts a single supervisor, coordinator, and worker; prevent competing instances.
- Startup at Windows login is an explicit operator setting, not silently enabled.
- Check process health and restart failed components with bounded retries.
- Surface repeated failures instead of an endless restart loop.
- Closing the client tab leaves background work running.
- Quit LILA Claw prevents further dispatch and gracefully shuts down the managed processes. Intentional shutdown must not trigger crash-restart behavior.
- Recover persisted state and reconcile uncertain external actions before continuing. Process restart alone is not authority to replay work.

## Availability boundaries

Startup at login is not automatic Windows login. After reboot, execution waits for the required user session, browser availability, authenticated account, and valid permissions. Lock-screen behavior requires testing; sleep and logout can interrupt availability. The supervisor cannot make an unavailable browser session execute tasks.

## Remaining details and validation

Supervisor implementation, startup registration mechanism, health checks, retry timing/limits, instance locking, process-tree cleanup, shutdown timeout, browser startup, update coordination, and user-facing failure reporting remain detailed design choices.

Validate clean launch, duplicate launch, enabled/disabled login startup, worker/coordinator crash or hang, repeated-failure handling, intentional quit, supervisor failure, reboot/login, lock/unlock, sleep/resume, and logout. Preserve credential scope and prevent stale workers from dispatching after replacement.

No startup registration, service installation, process changes, or tests were performed under this decision.

## Approval record

Sponsor selected “OptionB” in response to the proposal for a user-session supervisor with optional startup at login. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this startup/supervision approach only. The complete solution design and development remain unapproved.
