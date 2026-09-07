# ADR-027 — Activity audit integrity, retention, and deletion

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-13, BR-24, BR-25; ADR-004, ADR-025, ADR-026

## Approved decision

Maintain a local append-only, tamper-evident event journal with separately managed sensitive details. Cryptographically link/authenticate events and provide integrity verification, auditable corrections/deletions, and category-specific retention controls. Encryption alone does not provide the required audit integrity.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Ordinary editable database history | Simple implementation | Does not satisfy the approved tamper-evidence requirement; not selected |
| B: Local protected event journal | Fits local operation and supports traceability and privacy controls | Requires integrity verification and careful deletion/recovery design; approved |
| C: Journal with independent external verification | Stronger evidence against local history rewriting through externally retained checkpoints | Adds infrastructure, connectivity, and retention responsibilities; not selected |

Option B fits the local-first architecture and the BRD's explicit protection boundary. It does not establish independent evidence against an attacker controlling the machine and its keys.

## Approved behavior

- Record instructions, policy changes, approvals, dispatch, confirmed/failed/uncertain outcomes, recovery, and deletion as meaningful events.
- Correct history through new events referencing the earlier event and explaining the correction, rather than silently overwriting it.
- Keep resumes, answers, and detailed evidence outside the minimal event journal. Exclude credentials and unnecessary personal information from logs.
- Delete eligible sensitive content and append a minimal deletion event. A deletion marker alone is not removal of underlying information.
- Define separate retention periods for activity events, evidence, diagnostic logs, and backups. Exact durations remain for review; append-only operation does not imply indefinite retention.
- Apply backup retention explicitly and show when retained copies expire. Detached exported backups cannot be remotely erased. Restore must account for deletion history available to the application; do not claim that an old standalone backup contains newer deletion decisions.
- Verify journal integrity during recovery and periodic maintenance. Surface failures and pause execution that depends on untrusted history.

## Protection boundary

Local cryptographic verification can detect certain alterations. It cannot reliably prove that an attacker controlling both the host and keys has not rewritten or rolled back all journal and verification state. Independent external verification is not selected. Do not claim universal tamper prevention, guaranteed rollback detection, or immunity to privileged host modification.

## Remaining details and validation

Define event schemas, canonical encoding, authentication/key management, checkpoint and segment handling, correction references, and verification behavior in detailed design. Retention and authorized deletion must preserve verifiable continuity or explicitly record the resulting history boundary. Assess identifiers and references for privacy as well as payload contents.

Specify how deletion history, backups, and restoration interact, including incomplete knowledge after recovery from an older detached copy. Select category-specific retention periods and user-facing export/deletion flows during FRD review.

Validate event modification/reordering/deletion detection within the stated threat model, interrupted writes, correction lineage, actual content deletion, retention expiry, backup/restore behavior, log minimization, and handling of integrity failures. No implementation or tests were performed for this decision.

## Reference

[OWASP logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) recommends tamper detection, minimizing sensitive log content, and retention controls for logs and copies. The proposed local journal is a project design choice, not a claim that OWASP mandates this exact implementation.

## Approval record

Sponsor selected “B” in response to the proposal for a local tamper-evident event journal with separately managed sensitive details. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approval covers the audit, retention, and deletion approach, not exact retention durations, the complete solution design, or development/release authorization.
