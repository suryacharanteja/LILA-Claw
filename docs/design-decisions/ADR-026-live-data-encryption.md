# ADR-026 — Live-data and local-snapshot encryption

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-004, ADR-011, ADR-025

## Approved decision

Encrypt the live database, managed documents/evidence, and local recovery snapshots at the application level. Protect local encryption keys using Windows user-scoped DPAPI and automatically unlock under the configured Windows account, without another routine application password prompt.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Windows protection only | Restricted folder permissions and drive encryption simplify implementation and operation | Depends on host configuration; copied files do not retain application-level encryption; not selected as the complete approach |
| B: Application encryption with automatic unlock | Protects stored copies and supports unattended application startup after Windows login | Adds packaging, key-management, and recovery complexity; approved |
| C: Application encryption with manual unlock | Adds a separate passphrase requirement | Restart recovery waits for manual unlock; not selected |

Option B fits personal-data protection and the approved autonomous user-session model. Automatic unlock does not protect against an attacker controlling the same Windows user session. This decision does not promise pre-login operation or authorize changes to Windows drive-encryption settings.

## Approved behavior

- Use an established encrypted SQLite implementation. SQLCipher is a candidate, not a selected dependency; Python/Windows packaging and licensing require validation.
- Encrypt managed resumes, evidence, and local snapshots using established authenticated-encryption libraries. Retain restricted filesystem permissions.
- Protect local encryption keys using the approved user-scoped DPAPI credential protection. Ordinary application restarts under the configured account require no extra manual unlock.
- Preserve portable recovery independently of the original Windows profile through ADR-025's recovery mechanism. Recovery of business data must not depend on recovering the original machine's authentication credentials.
- Keep credentials excluded from ordinary backups. Detailed recovery packaging must ensure business data remains decryptable through the separate recovery mechanism without embedding authentication secrets or unprotected recovery keys.
- Control temporary plaintext required for document viewing or browser uploads, clean it up after use, and avoid sensitive content in logs. Cleanup is not a guarantee of forensic erasure.
- Provide an explicit protection choice for user-exported files.
- Loss of the Windows profile or protected keys requires recovery; do not silently fall back to unencrypted storage.

## Remaining details and validation

Select the database implementation, document encryption library, key hierarchy and rotation, snapshot encryption, recovery packaging, temporary-file lifecycle, and export behavior during detailed design. Cover database journals, auxiliary files, and failure paths so they do not undermine the selected at-rest protection.

Validate clean Windows packaging, ordinary restart unlock, unavailable keys, corrupted ciphertext, interrupted writes, document upload/view cleanup, sensitive-log exclusion, and restoration on a new Windows profile using the portable recovery mechanism. Measure performance on the supported hardware baseline. No encryption implementation, dependency installation, host-setting change, or tests were performed for this approval.

## References

- [Microsoft encryption guidance](https://learn.microsoft.com/en-us/windows/security/book/operating-system-security-encryption-and-data-protection): drive encryption and device-loss protection.
- [SQLCipher design](https://www.zetetic.net/sqlcipher/design/): transparent database-page encryption; candidate feasibility evidence.
- [Microsoft DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata): user-scoped protection and usual user/computer recovery boundaries.

## Approval record

Sponsor selected “B” in response to the proposal for application encryption with automatic unlock under the configured Windows account. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approves the encryption approach, not a specific library, the complete solution design, or development/release authorization.
