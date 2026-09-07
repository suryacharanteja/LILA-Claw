# ADR-025 — Business-data backup and recovery

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; ADR-004, ADR-011, ADR-022

## Approved decision

Provide automatic local recovery snapshots plus encrypted portable recovery copies to an explicitly configured external destination. After setup, backups operate without recurring approval prompts. Frequency, retention, and destination remain configurable; no numeric defaults or destination are selected here.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Local backups only | Simple recovery from application errors | Same-disk copies do not protect against disk loss; not selected as the complete approach |
| B: Local snapshots plus encrypted portable copies | Routine recovery and recovery onto another machine | Requires destination setup and safe custody of a recovery key; approved |
| C: Managed cloud backup | Convenient off-device protection | Adds service dependency, account setup, and potential cost; not selected |

Option B supports unattended backups and recovery after loss of the original machine, provided a usable independent copy and its recovery key remain available. No cloud service or account connection is authorized by this decision.

## Approved behavior

- Back up business data such as profiles, documents, tasks, and history. Ordinary backups exclude credentials under ADR-011. Machine migration requires credential re-entry and extension re-pairing.
- Produce a consistent recovery package containing a database snapshot, matching document versions, and an integrity manifest. Coordinate artifact retention/copying with the database snapshot; a database snapshot alone does not ensure filesystem consistency.
- Encrypt portable recovery copies using a dedicated recovery mechanism independent of the original Windows profile. Protect any locally retained backup secret using the approved credential storage and keep the recovery key separately from the backup. Do not include recovery secrets in the ordinary backup payload.
- Show the last successful backup and report failures or unavailable destinations; do not label an incomplete copy as successful.
- Validate a restore package in a staging location and show what will be restored before replacing current data.
- Keep restored tasks paused until permissions and external outcomes are reconciled. An older backup must not reactivate revoked credentials or silently replay applications or other outward actions.

Local snapshot protection and encryption of the live database/artifacts remain a separate explicit design decision. Portable backup encryption does not establish that live data or local snapshots are encrypted.

Backup housekeeping does not move the Phase 3 user-workflow scheduling feature into Phase 1.

## Remaining details and validation

Select backup format, encryption and key-management implementation, setup/recovery-key handling, retention and deletion behavior, destination support, snapshot coordination, restore compatibility, recovery objectives, and disk-space handling during detailed design. Establish how older restored permissions are reconciled before permitting execution.

Validate interrupted backups, unavailable destinations, corrupted or altered packages, wrong or missing recovery keys, matching database/artifact versions, restoration onto a clean machine, credential exclusion, migrations, and prevention of unauthorized or duplicate dispatch after restoration. No implementation, backup configuration, or recovery tests were performed for this decision.

## Reference

[SQLite backup documentation](https://www.sqlite.org/backup.html) describes consistent database snapshots; coordination with managed artifact files remains application responsibility.

## Approval record

Sponsor selected “B” in response to the proposal for automatic local backups plus encrypted portable recovery copies. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approval covers the backup and recovery approach, not live-data encryption, the complete solution design, or development/release authorization.
