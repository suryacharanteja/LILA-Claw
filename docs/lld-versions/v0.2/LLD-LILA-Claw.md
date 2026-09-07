# LILA Claw — Low-Level Design review package

Document ID: LLD-LILA-001  
Version: 0.2  
Status: Comprehensive Phase 1 implementation specification — final approval pending  
Date: 7 September 2026  
Baselines: approved BRD v1.1, SD v0.31, FRD v0.3/FD v0.1, HLD v0.1

## Package contents

| Package | Detailed design | Scope |
|---|---|---|
| LLD-01 | [Foundation and trust](lld/LLD-01-foundation-and-trust.md) | Process ownership, command contracts, API routes, sessions and authentication gate |
| LLD-02 | [Data and privacy](lld/LLD-02-data-and-privacy.md) | Logical schema, versioning, artifact publication, audit, backup and deletion |
| LLD-03 | [Execution and AI](lld/LLD-03-execution-and-ai.md) | States, dispatch algorithm, policies, duplicate handling, checkpoint and cost contracts |
| LLD-04 | [Client and browser](lld/LLD-04-client-and-browser.md) | Screens, UI commands, events, bounded browser tools and supported form adapters |
| LLD-05 | [Packaging and qualification](lld/LLD-05-packaging-and-qualification.md) | Release manifest, installation, updates, migration recovery and acceptance matrix |
| LLD-06 | [Selected protocols and dependencies](lld/LLD-06-selected-protocols-and-dependencies.md) | Exact trust/session/pairing, crypto formats, provider/checkpoint integration, browser strategy and signing choices |
| LLD-07 | [Contracts and invariants](lld/LLD-07-contracts-and-invariants.md) | SQL DDL, JSON Schema, OpenAPI, remaining route contracts and transaction invariants |
| LLD-08 | [Implementation phases and tests](lld/LLD-08-implementation-phases-and-tests.md) | Repository structure, M0–M8 build order, graph nodes, acceptance cases and all 25 BR mappings |

This package specifies the Phase 1 implementation, not a working product. Review all eight chapters and their contract artifacts together. LLD-06/07 provide the concrete choices missing in v0.1 and take precedence over its candidate wording; archived v0.1 remains under lld-versions. Existing approved BRD/FRD/HLD behavior is preserved; new LLD technical choices require this package's final approval. Implementation verification is required during M0–M8, not falsely recorded as already passed.

The deliverable now contains concrete authentication/session handshakes, encryption and backup formats, selected dependencies/provider, SQL DDL, typed API/browser/checkpoint contracts, dispatch/locking algorithms, migration/update procedures, screens and form-adapter rules, phase dependencies, tests and release criteria. No Phase 1 architectural choice is deferred as an unspecified G-01–G-05 gate. Actual signing secrets/production IDs and real browser fixtures are provisioning/qualification inputs with specified procedures; they cannot truthfully be fabricated in a design document.

## Common conventions

- Stable opaque UUID identifiers; UTC timestamps with timezone offset in API serialization; retain named policy/reporting timezones separately.
- Integers for provider money in micro-USD, aggregating before rounding to displayed currency minor units; reservation rounding is upward. No binary floating point for budget enforcement. Tokens/counters are nonnegative integers. Initial provider is USD; no invented exchange rates.
- Mutable records expose a monotonically increasing revision. Updates supply expected_revision and fail on conflict; immutable content versions are never edited in place.
- HTTP commands carry a stable command_id generated once per logical request. Browser actions carry a distinct action_id. Neither identifier is derived from secrets or personal content.
- Every external effect must be linked to its task, run, account, prepared payload version, policy/approval reference, and action ID.
- Separate protocol version, DB schema version, application version, graph definition version and artifact format version.
- Error envelope: {code, message, retryable, correlation_id, current_revision?, blocking_reasons?}. Messages contain no credentials or full sensitive payloads.

## Former design gates — now specified, with build acceptance

| Gate | Concrete specification | Required implementation acceptance |
|---|---|---|
| G-01 | LLD-06 loopback TLS, constrained per-user CA setup, launcher bootstrap, CSRF/session rotation, nonce pairing and worker pipe | M1 trust/replay/impostor tests; no cert bypass |
| G-02 | LLD-06 SQLCipher 0.6.2, AESGCM object/chunk formats, key hierarchy and audit HMAC; LLD-07 DDL | M1/M6 encrypted-canary, corrupt-package and independent-profile restore tests |
| G-03 | LLD-06 async BaseCheckpointSaver mapping and pinned OpenAI model/Responses contract | M0 lock/conformance and M3 replay/factual/cost tests |
| G-04 | LLD-06 semantic DOM/role/label strategy, fixed CDP wrappers, upload capability and evidence rules | M4 synthetic/authorized site fixtures per supported variant; never fabricated selectors or success evidence |
| G-05 | LLD-06 PyInstaller/Inno, Ed25519 manifest and Authenticode trust, atomic version/store activation | M7 installer/signature/rollback tests with owner-provisioned production values |

Design specification closure is distinct from runtime qualification. This package supplies build instructions and pass/fail criteria. It does not certify cryptography, authenticate an actual deployment, prove all live LinkedIn variants, or claim that a dependency lock has already been resolved. Missing/failed build evidence blocks acceptance of the corresponding milestone and release.

## Phases and scope

Implementation follows M0 foundation → M1 trust/storage → M2 domain/controls → M3 worker/AI → M4 browser → M5 full UI → M6 recovery/privacy → M7 packaging → M8 acceptance, with dependency overlaps explicitly defined in LLD-08. These are build increments inside the approved Phase 1. Product Phase 2 Telegram, Phase 3 scheduling and Phase 4 expansion retain their approved order and later-phase addenda requirements. This package does not mislabel future-phase interfaces as complete later-phase LLD.

## Final review highlights

Approve or revise this v0.2 package as one unit. Newly concrete choices include installing a constrained installation-specific CA into the Windows current-user trust store during explicit first-run setup, SQLCipher and AESGCM, OpenAI gpt-4.1-mini-2025-04-14 as the initial bounded drafting provider, English-first adapter qualification, a 100 MiB document limit, and PyInstaller/Inno signed distribution. These are disclosed implementation details, not actions already performed. The provider choice remains behind the approved abstraction; it is subject to factual evaluation, not a claim that it is the best model.

After approval, implement the packages under the agreed development gate and produce the stated evidence. Actual credentials, production extension ID, signing certificate/key, feed URL and authorized test data are deployment inputs. Development fixtures work without these; production packaging/integration must refuse placeholder values. Any change to an approved requirement requires explicit impact review.

## Verification evidence

The supplied [verification script](lld/contracts/verify_design.py) checks SQL syntax/integrity, uniqueness/FK/immutability cases, JSON parsing and API/schema references. [Validation report](lld/contracts/validation-report.json) records actual structural checks, including an explicit skip of full JSON Schema metaschema validation when its validator library is unavailable. This is not SQLCipher encryption, browser, authentication, provider, installation or performance qualification. Those tests belong to M0–M8.

Only documentation and design-contract validation were performed. No product implementation, dependency installation, provider calls, certificate installation or live platform actions were performed.
