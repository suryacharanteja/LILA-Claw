# M2 domain and controls — implementation checkpoint

Status: **In progress. This is not milestone completion, UAT acceptance, or release approval.**

Phase 1 remains the only active product phase. This checkpoint implements the coordinator-owned domain foundation against local deterministic fixtures. Production execution remains blocked: no worker graph, browser dispatch, provider call, or Telegram integration is enabled by these changes.

## Implemented and tested

| Work package | Behavior in this checkpoint | Evidence |
|---|---|---|
| W02.1 — task controls | Durable task/run creation; independent task/global holds; stop cancels unclaimed work and releases its reservations; restart creates a new run; command replay returns the original receipt across process restart | `test_controls.py`, `test_durability.py` |
| W02.2 — facts/artifacts | Immutable fact versions and current-head checks; changed facts revoke affected previews; draft fact/account references; PDF/DOCX format preflight; opaque encrypted LILAOBJ1 publication; integrity verification; missing/corrupt files block use; staging recovery | `test_controls.py`, `test_artifacts.py` |
| W02.3 — authority | Owner-supplied bounded standing policies; exact enumerated approvals as an alternative; 24-hour maximum preview validity; rejected versions remain blocked; policy expiry/revocation and version recheck; daily/run allowances; timezone carry and DST boundaries | `test_authority.py`, `test_boundaries.py` |
| W02.4 — ledger/events | Stable job identity, repost review, application guards; intent/claim separation; a single claimed executor; lease expiry and generation fences; clock rollback blocks expiry-dependent execution; uncertain recovery; idempotent system outcomes; distinct owner-reported completion; receipt lookup, signed list cursors and SSE state events | `test_controls.py`, `test_boundaries.py`, `test_durability.py`, `test_authority.py` |

The runtime opens the domain on its existing business writer and reconciles interrupted action/artifact state before exposing routes. Authentication, CSRF, HTTPS origin/host checks and the existing worker authentication remain in place. Internal account registration, draft preparation, proposal, intent, claim and evidence methods are trusted service boundaries, not public HTTP action-authority endpoints.

Exact approval grants only its enumerated action versions; it creates no standing allowance and grants no AI spending. Standing policies require the owner's explicit limits. AI reservation and factual narrative validation still belong to M3 integration. The tests use fixture facts and evidence; they do not establish that arbitrary model output is factually correct.

## Remaining before M2 can be marked Verified

1. Complete the persisted worker-facing readiness/lifecycle transitions and acceptance cases for Awaiting input, Active and Completed, including unresolved-outcome and zero-result completion guards.
2. Complete the document upload/status/selection API and bounded extraction handoff. This checkpoint accepts bounded bytes in the internal artifact service; it does not expose the approved 100 MiB streamed multipart upload route. Document generation and browser upload additionally require the later worker/browser integrations.
3. Complete explicit correction proposals and their reviewed application for conflicting terminal outcomes. Identical outcome replay is idempotent and uncertain outcomes can be reconciled, but conflicting terminal evidence is currently rejected rather than creating the full correction workflow.
4. Complete structured persisted blocking reasons, audit-chain verification and the remaining crash/fault-injection acceptance matrix, including account/tab capability changes supplied by the browser adapter. Append-only audit generation exists; that alone is not audit verification.
5. Finish API/contract coverage review and the requirement-to-test matrix against LLD-02/03/07/08. The current tests are passing engineering evidence for implemented behavior, not proof that every M2 exit criterion is covered.

Keep all W02 items In progress until their remaining criteria are implemented and verified. Do not advance to M3 or mark the entire Phase 1 scope covered based on this checkpoint.

## Reproduce verification

From the repository root, run `./scripts/verify-m2.ps1` in PowerShell. It uses the locked virtual environment and runs foundation, trust, and domain suites separately with their own pytest configuration boundary, followed by TypeScript checking and the production web build. Results are recorded in the three XML files and `verification.txt`; aggregate results are in `summary.json`.

Fixtures use encrypted temporary databases, synthetic documents and local test services. The trust regression does not install a root certificate. No manual business UAT is requested for this backend checkpoint. The M1 temporary certificate cleanup remains separately open as documented in the M1 evidence.

## Storage and dependencies

Business migration 2 adds implementation metadata for review membership, observed action context, timezone carry and fact immutability. The approved version-1 DDL and preserved LLD snapshots remain unchanged. Auth remains at its existing migration 2. A store records and verifies migration checksums; do not edit an already applied migration to upgrade an installation.

The locked environment contains 95 Python distributions. `tzdata` was added for IANA timezone rules on Windows; `defusedxml`, already present transitively, is now a declared dependency for DOCX XML preflight. Dependency metadata and source hashes are recorded alongside the test results. Starlette's existing AnyIO deprecation warning remains non-fatal; it is not a failed test.
