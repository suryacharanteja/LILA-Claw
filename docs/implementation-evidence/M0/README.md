# M0 — Foundation handoff

Status: **Engineering Verified**, 8 September 2026. Self-reviewed; no independent reviewer assigned.
Owner authorized M0. Business UAT and release approval are not claimed.
Phase 1 completes before Phase 2, then Phase 3 and later phases.

## Delivered

| Work item | Result | Evidence |
|---|---|---|
| W00.1 | Local Git repository initialized; isolated Python/React/extension source foundation; legacy entry points retained | baseline-hashes.json; new source tree |
| W00.2 | CPython 3.12.14 Windows x64; 94 Python packages hash-locked and compatible; npm lock with integrity hashes; license inventory | environment.json, python-licenses.json, npm-licenses.json, license-review.md |
| W00.3 | Generated Pydantic and TypeScript definitions; full JSON Schema/OpenAPI validation; byte-identical approved SQL promoted to versioned migrations | generated source; pytest.xml |
| W00.4 | Offline provider/browser doubles; in-process command receipt round trip; replay/conflict/reopen tests; repeatable verification scripts | tests/foundation; verification.txt |

## Verification

**27 tests passed, 0 failed, 0 skipped.** These include dependency import and cipher-version checks, schema/metaschema/OpenAPI validation, approved DDL invariant cases, migration rollback, and receipt persistence/replay/conflict tests.
TypeScript typecheck and Vite production build passed.
Both contract generators reproduced identical files.
Offline npm ci from the lockfile passed.
The approved SQLCipher wheel SHA-256 was verified from downloaded bytes.
All 15 approved LLD snapshot hashes matched. See reproducibility.json and sqlcipher-artifact.json.

One dependency deprecation warning remains: Starlette TestClient references an AnyIO alias.
It does not fail the verified tests; no application workaround was introduced.

## Reproduce

From the project root, with CPython 3.12.14 Windows x64, Node 22.19.0, npm 11.10.0 and uv 0.10.10:

1. Run `./scripts/setup-m0.ps1 -Python312 <absolute-path-to-python.exe>` to install locked dependencies.
2. Run `./scripts/generate-contracts.ps1` when validating/generated contracts change.
3. Run `./scripts/verify-m0.ps1` to run the foundation tests, typecheck and build.
4. Run `./.venv/Scripts/python.exe scripts/m0_evidence.py` to refresh the environment/license inventory.

The setup command needs package network access on an empty cache. No user account/API credentials are needed.
The Python and Node runtimes are development prerequisites; end-user bundled installation is M7.
No CI host was configured; the PowerShell verification script is the local repeatable check.

## Demonstration and boundaries

The automated test `test_receipt_roundtrip_replay_conflict_and_restart` submits a synthetic pause command,
checks its persisted receipt, replays it, rejects a conflicting reuse, and reopens the store to recover the same receipt.
The fixture uses `/fixture/` routes and SQLite synthetic data; it has no production launch path or external action capability.
It does not claim real task pause semantics, authentication or encrypted persistence.

The web output is a foundation placeholder, not the M5 business UI. No manual business UAT is required for this scaffold.
M1 supplies trusted runtime, TLS, pairing, DPAPI and encrypted storage; M2 implements actual task/control behavior.
Live browser/provider, performance, backup/recovery and installer tests are not run at M0.
Final bundle license notices, including the missing LangSmith installed notice and relevant native/font licenses, remain M7 obligations as recorded in license-review.md.

Next milestone: **M1 trust and storage**. It has not started in this increment.

