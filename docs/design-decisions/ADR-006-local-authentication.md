# ADR-006 — Local client and extension authentication

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-13, BR-20, BR-23; ADR-001–ADR-004

## Approved decision

Use explicit local pairing followed by automatically renewed, revocable sessions for the client and extension. No separate cloud identity account or application username/password is required for the initial single-owner deployment.

The installed launcher establishes a trusted setup session. The operator explicitly pairs the extension through a short-lived, single-use flow. Client and extension receive separate credentials with limited permissions. Reconnection and renewal are automatic while the pairing remains valid; the operator can revoke each connection from settings. Revoked credentials cannot renew sessions.

The backend must be authenticated to the connecting peer as well. A listening port or origin check alone does not establish backend identity. Detailed bootstrap and mutual-authentication mechanics remain open and require security review.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Local pairing and device-bound credentials | Local operation, no cloud account, unattended reconnect, per-connection revocation | Requires secure bootstrap, credential protection, and renewal; approved approach |
| B: Application username/password | Familiar login and potential multi-user fit | Adds password management; unattended operation still needs stored credentials or renewable sessions; not selected |
| C: Cloud identity login | Centralized accounts and future team access | Identity-provider dependency and account-management complexity; not selected for initial scope |

The rationale is a single-owner local application with autonomous operation. Authentication establishes connection identity, not authority to perform every action. Workflow permissions, standing authority, approval expiry, and revocation remain independently enforced. Session renewal does not renew expired action approvals.

## Credential protection and boundaries

Windows user-scoped DPAPI was proposed but not approved within this authentication decision. Subsequent [ADR-011](ADR-011-credential-protection.md) approves backend DPAPI protection, limited extension-local pairing storage, and re-entry/re-pairing recovery. Detailed implementation remains open; backend DPAPI does not automatically protect browser storage.

Exact pairing protocol, device binding, session lifetimes, renewal/replay handling, bootstrap secret delivery, encryption, credential rotation, and backup/migration behavior remain open. Device-bound is the intended trust scope, not a claim of hardware attestation or protection against a compromised user session.

Telegram sender authentication and remote approval handling remain separate design decisions and retain their later delivery phase. No cloud identity infrastructure, Native Messaging helper, or new approval policy is introduced by this decision.

## Validation required

Verify single-use pairing expiry and replay rejection; rejection of an impostor local server; separate client/extension scopes; unauthorized origins; automatic renewal after valid reconnect; revocation of active connections and renewal credentials; restart persistence; clock/expiry handling; and isolation between session renewal and action approval. Test Windows-user/device migration and credential loss once storage is selected.

No implementation or security-test results are claimed. The entire solution design remains under development.

## References

- [OWASP WebSocket security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [Microsoft DPAPI CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), reviewed as a candidate backend secret-protection mechanism

## Approval record

Sponsor stated “option A: approved” after the proposal for local pairing and renewable, revocable sessions, with exact protocol, storage, and lifetimes explicitly left to detailed design. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records approval of the authentication approach only; it does not authorize development or finalize remaining security choices.
