# M3 exit review

Engineering status: **In progress**. This review does not approve milestone exit.

| Gate | Current evidence | Remaining work |
|---|---|---|
| Checkpoint persistence and replay | HTTP saver conformance and [eight-case replay mapping](replay-acceptance.md), including local state recovery and transaction rollback tests | Integrated process/socket/receipt failpoints remain; local recovery calls are not full browser-effect crash qualification |
| Graph integration | Separate worker over HTTPS; bounded discovery; missing facts; prepared actions; provider fixture; pause/criteria/completion recovery | Real browser journey belongs to M4 integration; production remains unavailable without its adapter |
| Cost controls | All six T-COST categories now map to named, source-verified passing tests in [cost acceptance](cost-acceptance.md); missing/invalid rates create no reservation | Local category mapping complete; live request-bound/provider qualification and overall milestone acceptance remain separate |
| Factual labels | 100 strict-validator engineering cases exported with exact inputs/outputs and proposed results | Owner/reviewer inspection of [factual-review.md](factual-review.md); repeated templates are insufficient evidence of general provider quality |
| Provider request bounds | Request size/output cap enforced; live enablement blocked by TOKEN_BOUND_QUALIFIED=False | Qualify full framing/token bound for the selected model before enabling hard-budget calls; do not infer a proof from a byte cap alone |
| Provider evaluation | Mocked provider paths, invalid output/refusal/timeout tests | Representative corpus, approved truth labels, configured credentials and explicit authorization for the actual evaluation; no external calls performed |
| Narrative coverage | Exact verified text plus whitespace accepted; unsupported additions rejected | Qualify broader paraphrasing before claiming general grounded drafting support |

The existing 261-test full regression, TypeScript check and web build passed before this documentation increment. Review exports do not add new runtime capability. Approved baselines remain unchanged. M5 remains the first planned integrated business UAT handoff; M8 includes release UAT. Phase 2/3 remain outside current implementation.

## Cost requirement clarification from approved baselines

FD-005 in FRD-functional-decisions-review.md defines per-run and daily **action** caps and a separate applicable AI budget; it does not define a second per-run monetary field. LLD-03 requires conservative provider reservations, retention for uncertain billing, and no authority from late usage. The implementation uses the configured policy's monetary budget window shared across its runs. Do not invent an independent run monetary limit or claim that a shared-budget test proves the action run-cap case. T-COST-01 still requires exact action-ledger evidence in the final traceability audit.

The subsequent pre-call recovery increment handles oversized validated-fact context and preserves explicit monetary/configuration blockers. Its HTTP graph cases establish zero invocations and zero provider calls for oversized context, insufficient budget and stale prices. Read summary.json for the latest regression count; the earlier 261-test result above records the review package baseline.

T-COST-01 now has direct evidence in test_action_run_limits.py: confirmed, failed and uncertain attempts exhaust a run cap independently of the higher daily cap. This exposed and corrected failed-attempt refunds; lifecycle correction expectations now retain the attempt count. Migration 11 repairs earlier refunded failures and its fixture verifies linked-window accounting and idempotency. Final complete traceability review remains pending.
