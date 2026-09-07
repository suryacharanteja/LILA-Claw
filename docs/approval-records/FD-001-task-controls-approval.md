# FD-001 — Task controls approval

Date: 7 September 2026  
Decision: Approved  
Approver: Product sponsor / user

Sponsor replied “YES” to the proposed Pause / Stop / Resume / Restart semantics in task 01a0783f-92d5-78c1-b4c8-80424c720a17.

- Pause task prevents further dispatch, preserves queued work/progress, and reconciles in-flight actions. Resume rechecks permissions and readiness.
- Stop task ends the current run and cancels undispatched actions while preserving history. Restart creates a new run after duplicate and unresolved-action checks.
- Pause all pauses active tasks and holds new execution until explicitly resumed.
- Quit prevents new dispatch and gracefully shuts down background processes, preserving recovery state.
- Closing the client alone does not pause or stop agents.
- Show Requested until coordinator acknowledgment. Unreachable backend is not successful acknowledgment.
- Submitted actions cannot be undone; reconcile confirmed, failed, or uncertain outcomes.
- Paused/stopped work does not restart automatically after crash or reboot.
- Resume rechecks facts, permissions, budgets, browser availability, and unresolved outcomes.
- Extension exposes task controls and clearly labeled Pause all; later Telegram commands use the same semantics.

This approves FD-001 only. The complete FRD remains a draft, and HLD/LLD and development/release gates remain in effect.
