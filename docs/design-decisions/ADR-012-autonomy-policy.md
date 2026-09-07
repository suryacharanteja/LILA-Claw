# ADR-012 — Autonomous action permissions

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-20, BR-22, BR-23; ADR-006

## Approved decision

Use configurable autonomy by workflow and action type through explicitly configured, scoped standing permissions. Within valid permission boundaries the agent executes without repeated approval; exceptions require a decision. This selects a product policy model, not a grant of live LinkedIn execution authority.

The BRD's default preview/approval behavior remains effective until the operator deliberately configures standing authority for a supported action class. Authentication or session renewal does not grant or extend action permission.

## Options and rationale

| Option | Benefit | Tradeoff / disposition |
|---|---|---|
| A: Review every outward action | Individual review of each submission, message, or publication | Excessive review for unattended workflows; not selected as the only mode |
| B: Scoped standing permissions | Autonomous execution within explicit workflow/action boundaries | Requires deterministic policy enforcement and exception handling; approved |
| C: Global permission for all actions | Broad execution authority | Insufficient distinctions between consequential activities; inconsistent with the BRD's scoped approval model; not selected |

## Permission boundaries

A standing permission identifies the account, workflow, supported action types, boundaries, limits, and expiry. The operator may pause or revoke it. Authorization must be checked outside the model; model confidence cannot expand scope.

Examples discussed include automatic search/shortlisting, supported application submission using verified facts and permitted resumes, outreach to an approved audience, and draft preparation with separately configured publication authority. These examples are illustrative, not active permissions or approved default settings.

## Exceptions and recovery

- Missing or contradictory facts require information, not approval of a guess.
- Out-of-scope actions, expired authority, or changed account context require a fresh applicable decision.
- Material changes to an approved preview's content or recipients invalidate that approval and require re-review; do not silently fall back to broader authority to bypass it.
- Uncertain external outcomes must be reconciled before retrying.
- Account challenges pause the affected workflow for required handling.
- Pause/revocation prevents further dispatch; it cannot undo actions already accepted externally.
- Independent work may continue only where its permission and execution prerequisites remain valid.

## Future Telegram approvals

The coordinator may send an action preview and accept an authenticated approve/reject response bound to that action. Silence or timeout is not approval. Telegram approval follows the same account, content/version, expiry, and revocation rules as local approval. Telegram remains later-phase scope; sender identity, chat/channel type, callback protection, and exact interaction mechanics remain open.

## Approval scope and next choices

Exact defaults, limits, expiry periods, policy-edit behavior, and Telegram approval mechanics are not finalized here. Detailed policy precedence, batch approvals, restart persistence, and validation cases belong in subsequent design and FRD work. No implementation or verification is claimed.

Sponsor stated “option B: approved” following the proposal for configurable autonomy by workflow/action type, with the above details explicitly deferred. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records approval of the model only. It does not approve the entire solution design or authorize development.
