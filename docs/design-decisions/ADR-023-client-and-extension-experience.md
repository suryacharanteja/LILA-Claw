# ADR-023 — Admin, lightweight client, and extension experience

Version: 1.0  
Status: Approved — refined proposal  
Date: 7 September 2026  
Source: approved BRD v1.1; DD-008; ADR-001, ADR-006, ADR-012, ADR-021

## Approved decision

Provide a full admin mode and a lightweight daily-operation mode within the same local React/TypeScript web application, plus a compact browser extension interface. All surfaces use the same Python coordinator and authoritative task, permission, approval, and history state.

## Interface responsibilities

| Surface | Responsibilities |
|---|---|
| Full admin client | Configure workflows, verified facts, documents, permissions, approvals, agent activity, history, AI providers, Telegram, application settings, and recovery |
| Lightweight client | Give instructions, start configured workflows, track progress, review requests, view results, and pause/resume work |
| Browser extension | Pair/connect, select permitted tabs, show current action and connection status, request a pause, and open the relevant task in the main application |

Features retain their previously approved delivery phase; exposing Telegram configuration here does not move Telegram into Phase 1.

## Options and rationale

The original options were a full main client with a lightweight extension, a full interface duplicated in both places, and an extension-first interface. The sponsor refined the proposal to include a lightweight daily client alongside full admin control and limited extension features.

Implementing admin and lightweight experiences as modes of the same application shares components, avoids another installation or runtime, and keeps detailed configuration separate from routine interaction. A separately installed lightweight application is not selected. Duplicating the full administration interface in the extension and making the extension the primary workspace are not selected.

## Behavior and authority

- Closing a client does not stop background execution; execution remains subject to standing permissions and required service/browser availability.
- Persist requests requiring input so they can be reviewed later. Phase 2 Telegram approvals follow the existing identity and approval decisions.
- Admin means full LILA Claw application control, not Windows administrator privileges.
- UI modes are not an authorization boundary. Enforce any access restrictions in the backend; hiding a control is insufficient. This decision does not introduce a multi-user role system.
- Show pause requests as pending until acknowledged; a pause cannot undo an action already submitted.
- Resume and approval requests remain subject to coordinator validation and current authority. Changing interface mode does not expand agent permissions.

## Remaining details and validation

Screen layouts, navigation and mode switching, detailed review flows, accessibility, extension popup versus side-panel presentation, interruption handling, and acceptance criteria belong in FRD/UX design and subsequent engineering specifications.

Validate state consistency across surfaces, reconnect behavior, pending versus acknowledged controls, approval freshness, backend enforcement, and continued authorized execution after closing the client. No UI implementation or testing was performed for this decision.

## Approval record

Sponsor requested “full contrl admin level client and plus lightweight uiux client with browser extension also few features”. After the refined proposal recommended two modes in the same local application and a compact extension interface, the sponsor replied “approved”. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approval covers interface responsibilities and the shared-application approach, not the complete solution design or development authorization.
