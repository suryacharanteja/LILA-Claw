# LILA Claw — Low-Level Design review package

Document ID: LLD-LILA-001  
Version: 0.1  
Status: Draft for consolidated review — not implementation-ready  
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

These are proposed implementation contracts, not implemented or tested software. Review all five together; shared contract changes must update both producers and consumers. Existing approved behavior takes precedence over a conflicting proposal. All new technical constants below are proposed tunable implementation defaults; they do not change approved functional targets or grant action authority.

## Common conventions

- Stable opaque UUID identifiers; UTC timestamps with timezone offset in API serialization; retain named policy/reporting timezones separately.
- Integers for money in configured currency minor units, with rounding upward for reservations. Never binary floating point for budget enforcement. Tokens/counters are nonnegative integers.
- Mutable records expose a monotonically increasing revision. Updates supply expected_revision and fail on conflict; immutable content versions are never edited in place.
- HTTP commands carry a stable command_id generated once per logical request. Browser actions carry a distinct action_id. Neither identifier is derived from secrets or personal content.
- Every external effect must be linked to its task, run, account, prepared payload version, policy/approval reference, and action ID.
- Separate protocol version, DB schema version, application version, graph definition version and artifact format version.
- Error envelope: {code, message, retryable, correlation_id, current_revision?, blocking_reasons?}. Messages contain no credentials or full sensitive payloads.

## Implementation-readiness gates

| Gate | What is unfinished | Required closure |
|---|---|---|
| G-01 | Trusted launcher/bootstrap, backend identity proof, browser session/CSRF protocol and worker credential transport | Security-reviewed protocol and impostor/replay/revocation test design; do not build an unauthenticated fallback |
| G-02 | Exact encrypted database/crypto libraries, format, canonical audit encoding and key lifecycle | Windows/Python compatibility and license assessment, authenticated format specification and independent-profile recovery design |
| G-03 | Exact LangGraph checkpoint adapter API/version and hosted AI provider/model | Pin verified interfaces/dependencies and provider pricing/data-handling criteria; no synthetic interface claimed to match an SDK |
| G-04 | Live LinkedIn form adapters and definitive outcome observations | Versioned supported-case fixtures/selectors and outcome rules, followed by authorized qualification |
| G-05 | Installer/updater implementation, signer trust and release distribution | Selected tooling, signature-verification/bootstrap trust, migration/rollback specification and clean-machine plan |

No gate is claimed closed by this draft. Evidence-dependent choices must be resolved before the affected implementation is accepted; security and format contracts must be settled before implementing dependent persistence/authentication code. LLD final approval remains pending. This avoids presenting incomplete authentication or cryptography as a finished recipe.

## Review focus and next work

Review the concrete APIs, schema constraints, state transitions, dispatch fences, UI behavior and update sequence as one package. Close G-01–G-05 through documentation/API assessment and authorized validation, revise this package with the exact choices, then request final implementation-ready LLD approval. HLD approval is preserved separately and does not approve these proposed details.

No development, dependency installation, provider calls or live platform actions were performed to create this package.
