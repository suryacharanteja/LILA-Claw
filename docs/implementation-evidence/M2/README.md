# M2 — domain and controls

Engineering status: **Verified against local doubles and encrypted-store fixtures.** Sponsor UAT and Phase 1 release acceptance remain pending. M1 temporary certificate cleanup remains separately open.

Phase 1 is the only active product phase. Production readiness still blocks execution: no graph, provider call, LinkedIn submission or Telegram operation is enabled here.

## Delivered behavior

| Package | Implemented behavior | Primary tests |
|---|---|---|
| W02.1 — controls | Durable receipts, independent holds, preserved Awaiting input, Active/Blocked/Completed transitions, discovery/candidate/outcome completion guards, zero-match reason, stop cancellation, restart/recovery fences | controls, durability, lifecycle_corrections, domain_exit |
| W02.2 — facts/documents | Immutable facts; conflicting imports remain proposals; source/account checks; PDF/DOCX validation; authenticated multipart receive to 100 MiB; encrypted publication/status/recovery; selection; bounded extraction handoff | artifacts, uploads, fact_conflicts, criteria |
| W02.3 — authority | Explicit standing limits; exact batch approvals; review details and replay; rejection/expiry/revocation; run/daily reservations; timezone/DST carry; latest claim checks and midnight crossing | authority, boundaries, m2_acceptance, domain_exit |
| W02.4 — identity/ledger/events | Stable identity/repost review; mandatory post-filtering; criteria-edit lineage; intent/claim serialization; refreshed browser capability checks; persisted blockers; uncertain outcomes; reviewed terminal corrections; audit verification; signed paging and schema-conformant SSE | criteria, lifecycle_corrections, m2_acceptance, response_contracts |

The runtime verifies the local audit chain and reconciles interrupted action/artifact/upload state before attaching domain routes to the existing HTTPS/authentication boundary. The coordinator remains the sole business-store writer. Internal worker/browser methods accept trusted adapter inputs; public clients cannot use those methods to assert execution authority.

## Verification

Run `./scripts/verify-m2.ps1` from the repository root in PowerShell. It uses the locked environment and separately runs foundation/trust/domain tests, TypeScript checking and the web build. See `summary.json`, the JUnit XML files and `verification.txt`. `test-traceability.json` records individual tests, requirement mappings, fixture/source digests, fault points and outcomes. See [acceptance mapping](acceptance-mapping.md) for later integration obligations.

The final run has **99 passing tests: 27 foundation, 19 trust and 53 domain**, with no failures, errors or skips. TypeScript checking and the web build pass. The existing Starlette/AnyIO deprecation warning is non-fatal. Preserved LLD snapshot hashes and the approved protocol copy are checked separately.

## Subsequent milestone boundaries

- M3 consumes the queued extraction handoff and implements graph/checkpoint replay, provider costs and factual narrative validation. Document READY means validated encrypted bytes are available, not that facts were extracted or verified. Extraction handoff bounds output and requires PROPOSED facts. No OCR is promised.
- M4 supplies the actual browser capability observer and qualifies filters/forms/fingerprints/outcome evidence. M2 uses explicit doubles. Job-condition evaluation is labeled post-filtering; ambiguous salary currency/period/range comparisons remain REVIEW.
- M5 implements screens, pending-request UX, reviewed generation interactions, reporting and settings. Domain receipts/snapshots/events are tested; user-facing AC-018 assertions still require integrated client tests and UAT. No manual business UAT is requested for M2.
- M6 extends audit verification for authorized retention/deletion and backup/restore. Local chain/head checks detect inconsistencies and tail deletion against the retained head; they do not claim protection against rollback of an entire consistent database and its head. Document export remains a privacy integration.
- M7/M8 retain clean-machine, full failure/recovery, performance and release qualification. Passing M2 does not mark every cross-milestone FR complete.

Only selection is enabled on document commands now; generation/export require later integrations. Additive criteria-edit, review preparation/read and correction-read routes support approved behavior without changing preserved baseline schemas. SSE data retains a numeric event cursor; SSE resume IDs are separately signed, principal-scoped and expiring.

## Upload and storage notes

Authentication/CSRF checks occur before upload consumption and again before acceptance. One receive/publication slot bounds concurrent memory. Incremental multipart parsing enforces file/field/header/total-size bounds and a receive timeout. Bytes remain in bounded memory until encrypted publication; no plaintext upload spool files are created. The STAGING receipt is the durable acceptance record; the status route reports current READY/FAILED state. Failed/interrupted uploads remain visible.

Business migrations 3–6 add lifecycle/correction/audit-head metadata, document status/selection, action blockers and immutable action-criteria references. Applied migrations 1/2 and approved version-1 DDL were preserved. Version-2 upgrade and checksum-failure tests pass. Business schema is version 6; auth remains version 2.

The locked environment contains 96 Python distributions. Added `python-multipart` 0.0.32 provides incremental parsing; its Apache-2.0 license is retained in `dependency-licenses/`. The earlier Windows tzdata addition and explicit defusedxml declaration remain. Dependency metadata, source hashes and environment versions accompany this evidence.

Next milestone: **Phase 1 M3 — worker and AI**. Phase 2 and later phases have not started.
