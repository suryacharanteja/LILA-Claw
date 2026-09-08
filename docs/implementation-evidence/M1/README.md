# M1 — Trusted runtime and storage

Status: **Technical verification passed; temporary certificate cleanup pending.**
Date: 8 September 2026. Phase 1 only; M2 and later phases have not started.

## Implemented and checked

| Work item | Delivered behavior | Evidence |
|---|---|---|
| W01.1 | Separate supervisor, coordinator and worker processes; owner mutex; authenticated local-only named pipe; port fallback; bounded crash restart; persisted intentional Quit | process topology, control pipe and runtime integration tests |
| W01.2 | Constrained installation CA and renewable leaf; DPAPI private keys; private key loaded through an owner-only memory pipe; HTTPS only; one-use fragment bootstrap and secure cookie; strict Host/Origin and body bounds | TLS, expiry, wrong-origin, wrong-issuer and bootstrap tests; Chrome qualification pending |
| W01.3 | Separate UI/extension/worker identities; UI renewal/CSRF; epoch reset; signed extension pairing; owner confirmation; 15-minute extension sessions and renewal; immediate revoked-socket closure; fenced worker generations | session, pairing, WebSocket and worker tests |
| W01.4 | Separate SQLCipher business/auth databases; DPAPI key separation; owner/SYSTEM ACL; serialized writes; keyed WAL; checksummed migrations; rollback and key/integrity checks; atomic protected-file publication | encrypted canary, migration, writer and ACL tests |

The supervisor obtains worker bootstrap registration over the authenticated control
pipe, then passes credentials through an explicitly inherited anonymous pipe. Worker
credentials never enter argv/environment/checkpoints. Worker HTTPS verifies the CA
and installation SPKI before sending its bearer credential. Process launch avoids
the Windows venv redirector so the supervised PID is the actual coordinator/worker.

The UI is a foundation connection preview. Task execution remains explicitly blocked
with EXECUTION_NOT_IMPLEMENTED; the worker currently provides authenticated liveness,
not the M3 graph. No real applications, messages, browser actions or provider calls
were performed. User login startup, packaged entry points and signed distribution
remain M7; domain reconciliation and durable task holds are integrated in M2/M3.

## Verification

- **27 M0 regression tests passed.**
- **19 M1 tests passed.**
- TypeScript typecheck and web build passed.
- Evidence: [verification transcript](verification.txt), [foundation results](foundation-regression.xml), [M1 results](trust.xml).
- One non-failing dependency deprecation warning remains in Starlette's TestClient/AnyIO alias.

Tests use the actual Windows DPAPI, ACL, mutex, pipe, SQLCipher and TLS primitives;
API/WebSocket tests also use in-process clients. The process topology and loopback
integration tests start actual isolated child processes. Wrong-SID validation uses
the real process token against a substituted expected SID; no second Windows account
was created. These results do not establish Chrome trust behavior until the separate
browser test passes, or final clean-machine/performance qualification.

## Pending before M1 acceptance

Both technical decisions are resolved by [delegated approval](../../approval-records/M1-trust-and-bootstrap-decision.md).
Chrome qualification passed with normal certificate validation. The one-use,
60-second bootstrap launch exception is enabled for new installations; provider,
worker and session secrets remain excluded. Manual business UAT comes later.

Only temporary certificate cleanup remains. See Latest disposition below for the
Windows removal command and the exact certificate. M1 is not yet accepted and M2
has not started.

## Reproduce / review

Run `./scripts/verify-m1.ps1` from the project root. It uses the locked M0 development
environment and saves both regression and M1 evidence without overwriting M0 reports.

The development launcher is `./scripts/run-lila.ps1 -Operation setup|run|open|status|quit`.
Setup requires explicit interactive confirmation before changing CurrentUser Root.
Declining setup preserves the prepared identity and allows setup to be retried.
Automatic authenticated open uses the approved narrow bootstrap exception; existing installation opt-outs are retained.

The prepared browser qualification is `scripts/qualify-m1-browser.py`, targeting
`.local/m1-browser-review`; it requires the explicit confirmation flag and performs
cleanup in `finally`. The test uses CDP only to inspect this local UI; the production
browser controller remains the approved extension design. It uses no TLS bypass and
does not put bootstrap secrets in Chrome arguments. This authorized test has now passed; cleanup remains pending.

## Latest disposition

The user delegated the disclosed technical decisions; see [approval record](../../approval-records/M1-trust-and-bootstrap-decision.md). The Chrome test passed: the local UI established an authenticated session without a TLS bypass. Both earlier decision requests are resolved. No manual business UAT is required for M1.

Temporary certificate cleanup is still pending. The standard Windows removal returned ERROR_CANCELLED; a follow-up removal was rejected by automatic approval review (blocked by policy, no detailed reason supplied). Read-only verification confirms that the exact test certificate remains in CurrentUser Root. Do not mark cleanup complete or M1 accepted until absence is verified. The owner can run the original confirmation-driven removal command and accept the Windows prompt:

```powershell
certutil.exe -user -delstore Root D46EEBF7C0B8CF5176B7CD7B3C5E3F840006E164
```

This targets only the prepared LILA test CA. The application runtime and isolated Chrome test have stopped. M2 is the next implementation milestone after this remaining cleanup.
