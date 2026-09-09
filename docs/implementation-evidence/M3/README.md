# M3 — Worker and AI implementation evidence

Status: **In progress — implemented components verified with local fixtures; milestone exit not claimed.**

This increment implements Phase 1 M3 against the approved LLD v0.2. The runtime remains the Python FastAPI coordinator and separate worker. The legacy Flask entry point is unchanged and was not started.

## Implemented and exercised

| Component | Implementation and verification |
|---|---|
| Checkpoints | Coordinator-only SQLCipher persistence; immutable IDs and same-run parents; current worker leases; canonical bounded JSON; bytes and known Interrupt tags; special pending-write indexes; sync/async LangGraph saver; pagination, filters, interrupt/resume and stable action identity. |
| Worker graph | Bounded discovery with batches of 25, owner candidate-count input, two repeated-page termination, coordinator readiness gates, factual preparation, optional drafting, validation, identified actions, waiting and progress. Exercised with an HTTP checkpoint saver and coordinator/browser fixtures. |
| Provider | Fixed GPT-4.1-mini snapshot and Responses endpoint; strict schema, store:false, standard service tier, no tools, redirects or automatic retries; bounded requests/responses and timeouts; refusals, invalid claims, incomplete output and uncertain transport handled. |
| Costs | Integer micro-USD reservations; one-time send claims; current policy/configuration checks; linked timezone budget windows; replay-safe usage reconciliation; late usage conveys no dispatch authority; recovery releases unclaimed work and retains uncertain claims. |
| Credentials | Owner session and CSRF required; DPAPI inside the separate auth database; HMAC command receipt digest; invocation/lease-scoped worker retrieval. Validation errors do not echo input secrets. Fixture canary checked against stored bytes. |
| Grounding | Deterministic answers must equal the selected current verified fact. Narrative segments must quote current fact text, with a closed whitespace connector grammar. Revalidated at draft creation and pre-dispatch. A valid reference cannot legitimize invented text. |
| Documents | Actual separate worker consumes queued PDF/DOCX extraction over CA- and SPKI-verified HTTPS. Text extraction is bounded; image-only PDF requests manual entry. Recognized labels create PROPOSED fact versions; existing heads, including owner corrections, are preserved. Reclaim fences old results and repeated results are idempotent. |
| Runtime correction | Fixed a pre-existing TLS key-pipe race: ERROR_PIPE_CONNECTED is a successful connection when the reader arrives before ConnectNamedPipe. A deterministic regression test forces that ordering. No plaintext key file was introduced. |

The separate runtime worker now consumes document extraction and authenticated task assignments. Task execution uses coordinator-owned checkpoints, criteria-specific namespaces, bounded discovery, verified-fact preparation and optional provider drafting. A real worker/HTTPS test completes a zero-match task; HTTP integration tests resume missing facts, prepare one action without duplication, and exercise drafting with a mocked provider. Pause and changed criteria fence results from an in-flight browser observation; stale completion acknowledgements cannot complete revised criteria. Replacement leases reject the former worker. The concrete browser driver remains an M4 integration obligation: production execution stays blocked without it, and these fixtures do not establish a running autonomous browser journey.

## Verification

Run from the repository root:

```powershell
.venv/Scripts/python.exe scripts/m3_evidence.py
```

The script runs foundation, trust and domain suites separately, TypeScript checking and the web build; checks the 15-file approved LLD snapshot manifest; and records source hashes, environment and individual test results. Read [summary.json](summary.json) and [verification.txt](verification.txt) for the exact latest outcome. All test data and provider responses are local fixtures. The Windows runtime tests use installation-specific trust contexts and do not install a CA into the Windows certificate store.

The first full run exposed the TLS pipe race. It was investigated and corrected, with a forced-order regression test, before the successful verification run. Keeping the write buffer alive is additional overlapped-I/O hardening; it was not the identified cause of the startup failure.

## Outstanding M3 work and qualification

Recovery increment: graph/provider integration now distinguishes invalid output, rejected requests, uncertain invocation reconciliation, token-bound failures and coordinator transport failure from missing provider configuration. Injected provider timeouts and fabricated output create no action. Losing the usage reply after its commit leaves a reconciliation blocker on replay without a second provider request; losing the draft-publication reply after commit resumes from the persisted validated draft and creates exactly one prepared action. These tests use the actual HTTP coordinator and graph with local provider/browser fixtures. A completed invocation whose draft was never persisted remains blocked for reconciliation; automatic paid regeneration is not implemented or authorized by replay.

Completion recovery: expected lifecycle blockers at the final acknowledgement persist WAITING work state instead of escaping as worker failures. HTTP integration tests inject a task pause or unavailable browser readiness after the final graph checkpoint. Both prevent completion, preserve the control gate, and complete from the existing checkpoint after the gate clears, with one discovery call and zero actions. Unexpected lifecycle errors still propagate; this handling does not suppress stale leases or terminal-run fences.

Cost recovery: `test_ai_recovery_matrix.py` races reservations from two runs against a shared policy budget that permits only one reservation; exactly one succeeds. A timezone round trip followed by coordinator recovery and replayed late usage preserves linked-window accounting without negative or duplicate charges. A replacement worker cannot claim or reconcile its predecessor's invocation; the original authenticated owner can reconcile billing after fencing but receives no dispatch authority. All cases use isolated SQLCipher fixtures and deterministic clocks. These cases strengthen T-COST-02/03/06 and stale-generation evidence; they do not establish complete T-COST or M3 acceptance.

Checkpoint conformance increment: injected lost replies after checkpoint and pending-write commits replay without duplicate rows. Replaying those same commands after lease replacement is rejected, so command receipts do not bypass worker fencing. Both sync and async readers return the complete ordered 205-checkpoint history across the 200-record page boundary; a 201-record limit is respected, and criteria namespace prefixes remain isolated while exposing the root graph namespace correctly. Existing immutable checkpoint, metadata filter, parent, interrupt, serializer and stale-lease cases also remain in regression.

Pre-call blockers: oversized context previously raised a local provider validation exception outside the worker's handled failures. It now persists AI_CONTEXT_TOO_LARGE without restarting the worker. HTTP graph tests combine individually valid verified facts into an oversized request, configure an insufficient budget, and provide stale prices; each records its specific blocker and creates neither an AI invocation nor a provider request. Budget/policy/configuration errors retain their actionable reason instead of becoming WORKER_ERROR. These tests do not enable the unqualified live provider.

Action-cap defect found during T-COST-01 review: proven failed attempts were releasing allowance, contrary to FD-005. Failed attempts now consume allowance, including confirmed-to-failed corrections; unclaimed cancellation still releases its reservation. Tests isolate a run cap of one from a daily cap of ten and verify confirmed, failed and uncertain attempts each prevent a second intent without reserving another allowance. Migration 11 repairs previously released failed-action counters across linked timezone windows; its repair test checks repeated execution does not double-count. Duplicate identity remains independent: proof of non-submission can remove the duplicate guard but does not refund the attempted action.

Transient recovery: waiting tasks previously required a new business event even after a temporary transport failure. Coordinator assignment now rechecks narrowly classified worker/browser/transport failures after a five-second monotonic cooldown, under the existing readiness, hold and lease gates. The cooldown is process-local; coordinator restart may recheck immediately, while durable checkpoints, provider claims and action identities still govern replay. An HTTP test fails the initial checkpoint read and recovers with no intervening business event. Separate tests ensure elapsed time does not wake missing-fact or AI-reconciliation blockers. Lost-usage and lost-draft-publication tests still prove no duplicate paid invocation under the new scheduling behavior.

Completion acknowledgement transport: a lost acknowledgement previously escaped the task loop and could restart the worker. It now returns to authoritative assignment polling without replaying the acknowledgement directly. HTTP fault tests drop the acknowledgement before its commit and drop its reply after commit. The first resumes the saved final checkpoint; the second finds no remaining assignment. Each observes one discovery call, one completion event and zero actions. Other HTTP failures still surface; this does not treat an unconfirmed acknowledgement as success.

1. Qualify browser-dependent graph operations with the M4 driver. Task assignment and the HTTP coordinator adapter are connected to the worker process; production still must not advertise autonomous browser execution as ready without a qualified driver.
2. Qualify the model/tokenizer and full request-framing bound before hard-budget provider use. `TOKEN_BOUND_QUALIFIED=False` deliberately prevents live enablement. The 16 KiB request bound and reserved 32,768 input tokens are implemented, but an end-to-end token-bound qualification is not claimed.
3. Review and approve factual fixture truth labels, then perform the separately authorized actual-provider evaluation. The current T-FACT-001..100 parameterized matrix uses the specified 30/20/20/20/10 distribution, but its engineering labels are **not owner/reviewer-approved** and it is not a provider quality evaluation. The [review package](factual-review.md) includes every proposed label, rationale and exact JSON case; repeated template coverage is explicitly disclosed. Regenerate it with `.venv/Scripts/python.exe scripts/m3_factual_review.py`.
4. Broader narrative paraphrasing needs factual qualification. Current automatic acceptance supports exact source-grounded segments; freely paraphrased prose is rejected instead of being treated as verified by citation alone.
5. The [eight-case replay mapping](replay-acceptance.md) now distinguishes passing local recovery/rollback evidence from outstanding browser socket and process-crash qualification. Complete those integration obligations and end-to-end traceability before claiming full replay acceptance. The six T-COST categories have [named local evidence](cost-acceptance.md), including missing/invalid price configurations that create no invocation or reservation. Generate this report after regression with `.venv/Scripts/python.exe scripts/m3_cost_acceptance.py`; it rejects missing, failed, skipped or source-stale evidence. Category coverage does not establish complete milestone conformance.

No real API key was configured, no paid provider request was sent, no LinkedIn action occurred, and Phase 2/3 work was not started. First business UAT is planned for the M5 connected UI/browser increment, followed by integrated release UAT at M8. See [UAT readiness](../../uat-readiness.md).

See the [M3 exit review](exit-review.md) for the remaining acceptance gates and their evidence boundaries.

## Provider documentation checked

The approved snapshot remains `gpt-4.1-mini-2025-04-14`. Official model documentation checked during this build lists Responses/structured-output support and USD 0.40/1M input and 1.60/1M output tokens. These are review values, not automatically enabled account configuration. [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

The adapter uses `text.format` with strict JSON schema and explicitly handles refusal/incomplete output. Schema validity alone is not treated as factual correctness. [OpenAI structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs)

## Storage and contract notes

Approved v1 DDL and protocol snapshots remain unchanged. Additive business migrations 7–10 introduce invocation ownership, extraction claims, account provider configuration and durable task assignments/page/preparation records. Migration 11 repairs failed-attempt allowance accounting. Earlier migration files remain unchanged and their checksums remain verified.

Private AI reservations include the approved invocation/run/lease/generation/configuration/limits fields plus policy ID and request digest needed for scope and replay validation. Results bind invocation and reservation, status, usage and provider response identity. Credentials are fetched through a separate authenticated invocation-bound route and never enter the checkpoint schema.
