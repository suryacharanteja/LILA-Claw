# M1 trust qualification and bootstrap decision

Recorded: 8 September 2026.

The user was presented with the temporary CurrentUser Root certificate test and
the narrow browser-bootstrap exception, then instructed: “how to test it, i cant
test it manually right ? if you feel it is fine, we will go for next”.

This is recorded as delegation of the disclosed technical decisions to the
implementation agent, not as completed manual UAT. The agent recommended and
proceeded with both, within their previously stated boundaries.

1. Authorize the prepared localhost-only CA to be temporarily installed in
   CurrentUser Root for isolated Chrome qualification and removed afterward.
   This does not authorize persistent trust installation for unrelated certificates.
2. Permit the one-use, 32-byte, 60-second bootstrap capability in the URL fragment
   passed to Windows browser activation, including possible process arguments.
   This narrowly overrides LLD-01's blanket argument restriction for the LLD-06
   launch flow. It does not permit provider keys, worker credentials, session
   secrets, query-string tokens or logging of capability URLs. Same-user process
   inspection remains a residual risk within the approved local threat boundary.

New installations enable this bootstrap-only launch behavior. The per-installation
opt-out remains available. The approved LLD snapshots are preserved; this record
is the controlling implementation clarification for this conflict.

The owner relies on engineering verification for this foundational milestone.
Manual business UAT begins with usable business workflows and is not waived for
the Phase 1 release. M1 acceptance still requires the recorded qualification result.
