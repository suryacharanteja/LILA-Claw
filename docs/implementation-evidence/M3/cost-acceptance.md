# M3 cost acceptance evidence

All six approved T-COST categories have passing local evidence with source hashes checked against the last regression. This is component evidence, not M3 exit approval, live-provider qualification or business UAT.

T-COST-01 tests the approved per-run action cap; the monetary budget is separately checked across runs sharing a policy. See exit-review.md for the baseline interpretation.

## T-COST-01 — Per-run action cap

- `tests.domain.test_action_run_limits::test_run_cap_counts_attempts_independently_of_daily_cap[CONFIRMED]` — passed
- `tests.domain.test_action_run_limits::test_run_cap_counts_attempts_independently_of_daily_cap[FAILED]` — passed
- `tests.domain.test_action_run_limits::test_run_cap_counts_attempts_independently_of_daily_cap[UNCERTAIN]` — passed

## T-COST-02 — Cross-run daily cap

- `tests.domain.test_controls::test_daily_cap_and_confirmed_duplicate` — passed
- `tests.domain.test_ai_recovery_matrix::test_concurrent_runs_cannot_reserve_beyond_shared_daily_budget` — passed

## T-COST-03 — Timezone edit

- `tests.domain.test_ai_recovery_matrix::test_timezone_roundtrip_and_late_usage_do_not_reset_or_double_budget` — passed
- `tests.domain.test_boundaries::test_timezone_changes_roundtrip_and_late_release` — passed

## T-COST-04 — Invocation timeout

- `tests.domain.test_ai::test_ai_claim_timeout_late_usage_and_no_double_charge` — passed
- `tests.domain.test_ai::test_provider_transport_contract[timeout]` — passed

## T-COST-05 — Unknown or stale rates

- `tests.domain.test_ai_recovery_matrix::test_unknown_or_invalid_rates_cannot_reserve_budget[rates0]` — passed
- `tests.domain.test_ai_recovery_matrix::test_unknown_or_invalid_rates_cannot_reserve_budget[rates1]` — passed
- `tests.domain.test_ai_recovery_matrix::test_unknown_or_invalid_rates_cannot_reserve_budget[rates2]` — passed
- `tests.domain.test_ai_recovery_matrix::test_unknown_or_invalid_rates_cannot_reserve_budget[rates3]` — passed
- `tests.domain.test_ai::test_ai_stale_prices_and_disabled_provider` — passed

## T-COST-06 — Reservation reconciliation

- `tests.domain.test_worker_recovery::test_restart_releases_unsent_ai_and_retains_claimed_budget` — passed
- `tests.domain.test_ai_recovery_matrix::test_replacement_worker_cannot_claim_or_reconcile_predecessor_invocation` — passed
- `tests.domain.test_action_run_limits::test_failed_attempt_migration_repairs_linked_windows_once` — passed

Exact hashes and test references: [cost-acceptance.json](cost-acceptance.json).

Still open: complete replay-matrix mapping; factual-label review; representative provider evaluation corpus; full request/token-bound qualification; authorized real-provider evaluation; M4 browser integration.
