# ADR-011 — Credential protection and recovery

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Resolves: DD-011  
Source: approved BRD v1.1, BR-13, BR-20, BR-23; ADR-004 and ADR-006

## Approved decision

Protect backend secrets using Windows user-scoped DPAPI and restricted filesystem permissions. Use credential re-entry and extension re-pairing as the initial recovery policy after machine migration or credential-store loss.

- Backend secrets include provider API keys, future Telegram bot credentials, and backend authentication secrets. Use user scope, not machine-wide DPAPI protection.
- The extension retains only its own limited pairing credential in extension-local storage restricted to trusted extension contexts. Do not sync it or place provider/Telegram secrets there. Extension-local storage is not an encrypted vault; limit exposure through permission scope, rotation, and revocation.
- Ordinary application backups exclude credentials. Restore business data, re-enter provider credentials, and pair the extension again when moving machines or losing the credential store.
- Restoring an older backup must not reactivate old pairing credentials. Recovery must establish fresh trust and invalidate restored authentication state as necessary; exact anti-rollback and identity-generation mechanics remain to be designed.

## Options and rationale

| Option | Benefit | Tradeoff / disposition |
|---|---|---|
| A: Windows user-scoped protection | Unattended operation under the configured Windows account without another vault password | Migration/profile loss may require re-entry; approved |
| B: Password-encrypted application vault | Portable encrypted backup is possible | Startup unlock interrupts automatic recovery unless another unlock mechanism is added; not selected |
| C: External secrets manager | Centralized access, rotation, and recovery | Additional service dependency, setup, and potential cost; not selected for initial scope |

This fits the Windows-first, single-owner deployment. It does not promise browser execution before Windows login, resistance to a compromised user session, or encryption of the entire SQLite database and artifact collection. Protection and recovery of general business data remain separate design work.

## Operational boundaries

Autonomous operation requires the configured Windows account and its protected credentials to be available. Changing the service identity or moving to pre-login execution requires assessment of credential access and browser-session availability. Do not silently weaken protection to machine scope to solve a deployment issue.

Session renewal remains governed by ADR-006. Recovery does not renew action approvals or justify replaying uncertain external actions. Telegram remains later-phase scope. Native Messaging remains only a possible future setup helper under ADR-002.

## Remaining implementation and validation

Select the DPAPI integration library, file permissions, credential file format, rotation procedure, trusted-extension access configuration, bootstrap/renewal protocol, and recovery identity mechanism during detailed design. Validate fresh installation, same-user restart, wrong-user access rejection, credential loss, machine migration, old-backup restoration, extension storage access boundaries, revocation, and secret exclusion from logs and normal backups.

No implementation or security test results are claimed.

## Sources

- [Microsoft CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata): user-scoped protection and normal user/computer decryption boundaries.
- [Chrome storage](https://developer.chrome.com/docs/extensions/reference/api/storage): extension-local storage and access-level controls.

## Approval record

Sponsor stated “option A: approved” after the proposal explicitly including Windows-protected backend secrets, limited extension-local pairing storage, and credential re-entry/re-pairing for recovery. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this decision; it does not approve the complete solution design or authorize development.
