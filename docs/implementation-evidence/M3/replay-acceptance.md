# Replay acceptance mapping

Status: **Local recovery evidence available; integrated replay acceptance incomplete.**

These IDs refer to the T-REPLAY matrix in approved LLD-08. Tests use local SQLCipher stores, fixtures and explicit exceptions; they do not claim power-loss durability, a killed production process at every boundary, or actual browser sends. The new tests are in `tests/domain/test_replay_acceptance.py`. Read domain.xml and source-hashes.json for the exact regression evidence.

| ID | Approved fault point | Evidence | Remaining qualification |
|---|---|---|---|
| T-REPLAY-01 | Before intent | `test_recovery_at_local_action_boundaries[before_intent]`; `test_failed_intent_transaction_leaves_no_reservation_or_guard` | Integrated dispatcher failpoint |
| T-REPLAY-02 | After intent | `test_recovery_at_local_action_boundaries[after_intent]`: repeated recovery retains uncertainty and allowance | Process interruption at dispatcher intent commit |
| T-REPLAY-03 | After claim, before send | `test_recovery_at_local_action_boundaries[after_claim]`; old claim cannot be reused | M4 socket boundary proves no blind retransmission |
| T-REPLAY-04 | After send | Provider timeout and lost-reply tests establish the separate AI no-resend rule | Browser socket-write crash test remains open; AI tests are not a substitute |
| T-REPLAY-05 | After receipt | No claim of browser receipt recovery qualification | M4 receipt persistence and process-crash test remains open |
| T-REPLAY-06 | Before outcome commit | `test_failure_before_outcome_commit_rolls_back_then_reconciles_once`: injected transaction failure rolls back outcome/counters, then reconciliation persists once | Integrated observation/dispatcher fault injection |
| T-REPLAY-07 | After outcome commit | `test_recovery_at_local_action_boundaries[after_outcome]`; outcome and completion-ack replay tests | Process-crash integration remains to be exercised |
| T-REPLAY-08 | Stale worker on replacement | Worker lease, checkpoint fencing, AI ownership and replacement graph tests; local recovery cases reject old claims | M4 extension ignores stale generation during active socket work |

The local state tests invoke recovery twice and assert preserved states and counters. The outcome rollback test also verifies the audit chain after recovery. No browser actions or provider requests are made.

M3 review can use these component results, but this table must not be labeled a passed eight-case end-to-end matrix. Named production-disabled failpoints and integrated browser crash execution remain M4/M6/M8 obligations under the existing plan. Factual-label review, full provider request-bound qualification and authorized real-provider evaluation remain separate M3 acceptance gates.
