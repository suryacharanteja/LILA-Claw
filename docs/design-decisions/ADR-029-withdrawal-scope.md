# ADR-029 — Withdrawal scope and delivery priority

Version: 1.0  
Status: Approved  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-19; ADR-012, ADR-013, ADR-017, ADR-024

## Approved decision

Keep both pending connection-invitation withdrawal and submitted job-application withdrawal in scope. Deliver invitation withdrawal first, with the networking module. Deliver application withdrawal after validating platform support for the applicable application flows. Exact release assignments remain for FRD review.

This clarifies BR-19 without changing its approved wording or the existing BRD phase sequence. Withdrawal is not a prerequisite for the initial job-search/application journey.

## Rationale and alternatives

Invitation withdrawal fits invitation tracking and relationship management. Application withdrawal needs separate assessment for LinkedIn and external employer portals, depending on where the application was submitted. Supporting only invitations would omit the other requested workflow; committing both to the initial job journey before validation would introduce an unverified dependency. The approved approach preserves both workflows with staged, evidence-based activation.

## Approved behavior

- Show the exact invitation or application affected and explain the consequence before authorization.
- Default to explicit approval. Unattended withdrawal requires a deliberately configured, scoped standing policy under the existing permission decisions.
- Record confirmed, failed, or uncertain outcomes; do not treat a click or request dispatch as confirmation.
- When withdrawal is unavailable, explain the limitation and provide a manual route where known.
- Do not assume that either a particular LinkedIn flow or an external employer portal supports withdrawal. This decision is a scope/priority selection, not platform capability evidence.

## Remaining work

Define supported withdrawal cases, capability checks, consequences, review/standing-policy behavior, outcome verification, and release assignments in FRD and subsequent design. Any external-portal execution must satisfy the existing browser/domain permission boundaries and receive the necessary design assessment; this decision does not grant blanket access to employer sites.

No implementation, platform actions, or capability tests were performed for this approval.

## Approval record

Sponsor replied “yes” to the recommendation “both in scope, invitation withdrawal first, application withdrawal subject to validated platform support”. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approval clarifies withdrawal scope and priority. Complete solution-design approval and development/release authorization remain pending.
