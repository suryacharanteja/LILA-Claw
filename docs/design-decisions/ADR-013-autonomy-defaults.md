# ADR-013 — Autonomy defaults, limits, and expiry

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-012

## Approved decision

Use reusable, time-bounded policies to authorize matching tasks until their explicit limits or expiry are reached. Numeric limits and durations are user-configurable; none are silently assumed.

| Setting | Approved behavior |
|---|---|
| Search and local drafts | Run within the user-authorized workflow without repeated prompts |
| Outward actions | Require preview approval until the operator explicitly enables standing permission for that action type |
| Scope | Specific account, workflow, action types, audience/job criteria, and permitted documents |
| Limits | Explicit per-run and daily action caps; applicable AI spending budget |
| Expiry | Operator selects an end date/time when enabling the policy; no hidden indefinite authority |
| Limit reached or expired | Pause affected actions and request renewal or revised limits |
| Restart | Preserve policy and usage counters; revalidate before resuming |
| Policy changes | Require explicit operator authorization; agent cannot expand its own permissions |

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: One task/run permission | Clear boundaries for occasional work | Repeated setup for recurring work; not selected as the sole model |
| B: Reusable time-bounded policies | Supports unattended recurring work with deliberate renewal | Requires limits, counters, expiry enforcement, and occasional renewal; approved |
| C: Permission until revoked | Less renewal effort | Stale authority may persist indefinitely; changes BRD expiry requirement; not selected |

The seven-day example discussed was illustrative, not an approved default. No action counts, spending amounts, or universal validity period were selected. Action caps control delegated scope and do not guarantee platform acceptance.

## Relationship to prior approvals

ADR-012 governs scoped standing authority and exceptions. ADR-006 session renewal does not extend policy expiry. Reusable policies do not bypass missing-fact handling, material changes to approved previews, account checks, stop/revocation, or reconciliation of uncertain outcomes. Telegram renewal or policy editing must authenticate the operator and capture an explicit decision; mechanics remain open.

## Detailed design still required

Define policy precedence, validation before enablement, what counts toward each cap, reservation of capacity for in-flight actions, retry/uncertain-outcome accounting, daily-reset timezone and clock behavior, budget accounting, and atomic enforcement across processes. Specify renewal notifications and batch behavior. Do not reset counters on restart or treat expired permissions as valid while waiting for a reply.

Validate limit boundaries, expiry during execution, restart persistence, concurrent requests, counter rollover, revocation, and attempts by model output to expand scope. No implementation or test results are claimed.

## Approval record

Sponsor stated “option B: approved” after the proposal for reusable policies with explicit limits/expiry and the configuration-default table. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records approval of this policy model and defaults, not numeric settings or the entire solution design.
