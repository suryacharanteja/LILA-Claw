# ADR-018 — Workflow orchestration

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-010, ADR-012, ADR-013, ADR-016, ADR-017

## Approved decision

Use a persistent workflow state machine with bounded AI reasoning inside it. Code governs workflow state, permitted transitions, permissions, and budgets. AI interprets observations and proposes steps using approved tools within those boundaries.

The agent worker proposes progress. The coordinator validates transitions, persists state, and authorizes browser dispatch. The extension remains the browser execution endpoint under ADR-017. Waiting for information or approval must not require keeping an AI request running.

## Options and rationale

| Option | Benefit | Tradeoff / disposition |
|---|---|---|
| A: Fixed scripts | Predetermined behavior | Fragile expansion of branches for unfamiliar forms and contextual decisions; not selected as sole orchestration model |
| B: Structured workflow with AI reasoning | Adaptability with explicit state, permission enforcement, and recovery | Requires state definitions, tool contracts, and recovery rules; approved |
| C: Open-ended AI loop | Flexible tool selection | Harder to control costs, approvals, and restart behavior; prompt instructions alone are insufficient; not selected |

Deterministic steps remain useful inside the chosen workflow. The AI may interpret unfamiliar questions, choose approved tools, and adapt its plan, but cannot invent facts, expand permission, or declare success without required evidence.

## Representative application flow

1. Discover and assess: search, apply eligibility rules, and explain matches.
2. Prepare: inspect the form, select verified facts and documents, and draft answers.
3. Validate: check answers, attachments, and permissions.
4. Act or request input: execute within authority or persist a waiting state for clarification/approval.
5. Verify: establish confirmed, failed, or uncertain outcome; reconcile uncertainty before retry.
6. Resume: restore progress after interruption and recheck current browser state and authorization.

This is a conceptual flow, not a final state enumeration or FRD. AI adaptability does not establish support for every unfamiliar form.

## Recovery and ownership

Persist enough state to distinguish preparation, authorized dispatch, in-flight work, and verified outcomes. Recovered tasks must not blindly replay external actions. State transitions and action authorization require deterministic checks in the coordinator, consistent with the existing single-owner and SQLite write-ownership decisions.

Pauses release active work where appropriate while preserving the information needed to resume. Revalidate facts, document versions, permissions, and page context as applicable. Resume does not extend expired authority.

## Remaining choices and validation

Framework/library selection is separate. Define state schemas, transition rules, checkpoints, worker/coordinator message contracts, transactional boundaries, execution ownership, cancellation, AI step/cost bounds, and schema migration in later design and FRD work.

Validate interruption at dispatch boundaries, restart from waiting states, duplicate transition requests, stale observations, invalid model proposals, permission expiry, and evidence-based completion. No framework has been selected and no implementation or testing is claimed by this record.

## Approval record

Sponsor stated “optionB: approved” after the proposal for a persistent workflow state machine with bounded AI reasoning, explicitly deferring framework/library selection. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records the orchestration approach only; it does not approve the entire solution design or authorize development.
