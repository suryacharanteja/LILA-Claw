# ADR-004 — Persistence and artifact storage

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-10, BR-13, BR-24, BR-25; ADR-010

## Approved decision

Use SQLite for structured application data and a managed local folder for documents and retained evidence. No separate database server is required for the initial single-operator, single-PC deployment.

| Storage | Contents |
|---|---|
| SQLite | Profiles, tasks, workflow progress, approvals, action history, document versions, and file references |
| Managed local folder | Resumes, generated documents, and retained evidence |
| Protected credential storage | API keys, Telegram credentials, and pairing secrets; mechanism remains a separate decision |

Record each managed document's identifier, version, and integrity hash in the database. Keep database-write ownership in the coordinator; the separate agent worker requests state changes through it. Detailed internal communication and storage-access implementation remain for HLD/LLD.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: SQLite plus local files | Embedded transactional storage; simple installed-product deployment | One writer at a time; coordinated database/file recovery required; approved |
| B: PostgreSQL plus local files | Better fit for many concurrent writers and shared-server deployments | Additional service, configuration, updates, and recovery procedures; not selected |
| C: JSON/CSV plus local files | Readable and convenient for export | Custom transaction, locking, relationship, and recovery machinery would be required; not selected as operational storage |

SQLite fits the current deployment scope. Future Telegram access reaches the coordinator and does not itself require a server database. Reconsider PostgreSQL if shared multi-user hosting or measured write concurrency warrants it; migration is not assumed to be automatic. JSON/CSV remain possible export and configuration formats.

## Consistency, security, and recovery

- SQLite transactions do not include filesystem changes. Design staged file writes, explicit readiness states, reconciliation, and consistent backups before implementation is accepted.
- Only verified, ready document versions may be used for outward actions. Missing or mismatched files must block dependent dispatch.
- Database choice does not itself provide encryption or the BRD's tamper-evident audit guarantees. Credential protection, encryption/key management, audit design, retention, and deletion require further decisions.
- Preserve task state and approval lineage across restarts. Restore does not justify replaying uncertain external actions.
- Keep database and managed artifacts local to the host; any future network/shared storage requires separate assessment.

## Open implementation choices and validation

Schema, database access library, journal/durability configuration, migration tooling, file layout, backup/restore protocol, retention settings, and storage quotas remain open. No WAL mode or specific encryption library is selected by this ADR.

Later verification must cover interrupted database/file updates, disk-full conditions, missing or corrupt artifacts, schema upgrades, consistent backup restoration, duplicate-action prevention after recovery, and coordinator responsiveness during writes. No implementation or test results are claimed.

## Sources

Reviewed during the decision discussion: [SQLite appropriate uses](https://www.sqlite.org/whentouse.html), [SQLite WAL documentation](https://www.sqlite.org/wal.html), and [PostgreSQL architecture](https://www.postgresql.org/docs/current/tutorial-arch.html). Recommendation is a project fit assessment, not a benchmark claim.

## Approval record

Sponsor stated “Option A: approved” after the proposal for SQLite plus managed local file storage. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this approved storage decision. It does not approve the complete solution design or authorize development.
