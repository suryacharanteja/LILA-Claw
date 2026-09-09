# M2 acceptance mapping

This maps the domain portion of the approved BRD/FRD/FD/LLD to engineering evidence. It does not replace release criteria or remove later-milestone requirements.

| Baseline / behavior | M2 evidence | Remaining integration |
|---|---|---|
| AC-018-01: pause preserves pending work and permits reconciliation | Pause/claim race, pause-denied claim, recovery and outcome tests | M4 transport; M5 pending display |
| AC-018-02: resume cannot renew authority/facts | Expired policy after resume, fact edits, stale leases and revocation | M3 graph re-entry; M5 actionable display |
| AC-018-03/06/08: stop, durable holds, restart, retained outcomes | Reopened-store receipts/holds, cancellation, uncertainty and provenance | M4 transport interruption; M5 no-reversal wording |
| AC-018-04: new task under global pause | New-task-under-global-pause test | M5 mode parity |
| AC-018-05/07: unreachable backend and close versus Quit | Durable receipt lookup; M1 runtime/quit regression; global quit holds before shutdown | M5 disconnected/pending/close UI; M7 packaged quit |
| FD-002, FR-004/008, T-JOB | Exact rediscovery, distinct/repost review, unknown identity, confirmed/manual/uncertain guards; mandatory salary, exclusions/preferences and criteria-edit lineage | M4 native discovery/filter catalog |
| FD-003, FR-009/011/028, T-DATA | Conflict proposals, head/source ownership, immutability, changed facts, corrupt/missing files, upload/status/selection/recovery | M3 extraction/generation and 100-case factual suite; M5 review UI |
| FR-012/013, T-COST-01..03 | Explicit/standing grants, exact members/rejection/expiry, run/daily caps, timezone/DST/midnight and claim rechecks | M3 monetary reservations/timeouts/rates |
| T-REPLAY domain boundaries | Failed-intent rollback, committed intent/claim recovery, late proven failure, duplicate outcomes, reviewed terminal corrections, stale previews/leases | M3 checkpoints; M4 socket/receipt failpoints; M6 restore |
| LLD-07 envelopes and paging | Receipt/TaskSnapshot/Event schema tests; auth/CSRF; scoped expiring cursors; SSE snapshot-required | M4 extension parity; M5 resynchronization |
| LLD-02/06 integrity | SQLCipher regressions, v2 upgrade, AEAD corruption, audit segment/key/tail checks | M6 retention, detached backups and cross-profile recovery |

Live browser actions, provider evaluations, personal-data extraction, packaged installation and business UAT were not run. They remain assigned to the approved later milestones. Tests use synthetic inputs and controlled local runtime services.
