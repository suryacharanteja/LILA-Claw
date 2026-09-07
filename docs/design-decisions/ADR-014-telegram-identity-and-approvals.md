# ADR-014 — Telegram interaction, identity, and approvals

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Delivery: Phase 2  
Source: approved BRD v1.1, BR-16, BR-20, BR-23; ADR-011–ADR-013

## Approved decision

Use a private conversation with the LILA Claw bot, restricted to the operator's explicitly paired numeric Telegram user ID and private chat ID. Do not use username or display name as the authorization identity.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Private bot chat | One place for owner commands, previews, approvals, and results | No shared team conversation; approved |
| B: Private group | Shared visibility and discussion | Requires group and individual-user authorization; membership alone is insufficient; not selected |
| C: Notification channel plus private approvals | Separate activity feed | Two destinations and additional routing; not selected for initial scope |

The selected flow fits the single-owner baseline. Approval does not expand the project to multiple operators or grant authority to other Telegram users.

## Pairing and command flow

1. Operator enables Telegram locally and starts a one-time pairing flow.
2. Operator contacts the bot; the local client confirms the Telegram account being paired before binding access.
3. Persist the authorized numeric user ID and private chat ID. Validate both for commands and approval callbacks.
4. Natural-language instructions become tracked tasks. Work proceeds only within valid workflow permissions and standing policies.
5. Exceptions receive a preview and Approve / Reject buttons. Results return to the paired private chat.

Exact pairing token issuance, expiry, identity display, replacement, and recovery procedures remain detailed design work. Pairing establishes control by the Telegram account, not independent proof of the human's real-world identity.

## Approval rules

- Bind an approval to an action or defined batch, the exact content/version, and expiry. Enforce these bindings in the backend; do not trust callback payloads as authority.
- Duplicate clicks and repeated updates cannot cause repeated external execution.
- A plain “yes” cannot approve an ambiguous pending action.
- Expired or materially changed previews require a fresh decision.
- Silence or timeout is not approval. Standing permissions retain ADR-012 and ADR-013 boundaries.
- Local revocation disables Telegram control. Recheck authorization before dispatch, including after reconnection or restart.

## Open implementation and validation

Polling versus webhooks is the next separate decision. Bot library, update persistence, callback token format, message limits, document previews, delivery retries, and detailed privacy/retention remain open. Telegram credentials use the approved backend secret-protection approach. Telegram delivery does not require exposing the local browser-control endpoint.

Validate wrong sender/chat rejection, pairing reuse, revocation, duplicate callbacks, old previews, policy expiry, reconnect, and independent local/remote approval races before acceptance. No bot has been configured, no messages sent, and no implementation or test results are claimed by this record.

## Reference

[Telegram Bot API](https://core.telegram.org/bots/api): user/chat identifiers and callback mechanisms, reviewed during the decision discussion. Backend authorization is a LILA Claw responsibility.

## Approval record

Sponsor stated “Option A: approved” after the private-bot-chat proposal and interaction rules. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this decision. Telegram remains Phase 2; approval does not authorize implementation or change the release sequence.
