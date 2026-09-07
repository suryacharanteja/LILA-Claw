# LLD-04 — Client and browser execution

Version: 0.1  
Status: Proposed; G-04 live adapter gate open  
Parent: [LLD review package](../LLD-LILA-Claw.md)

## Client routes and view models

| Route | View model / actions |
|---|---|
| /setup | Readiness blockers, pairing, confirmed facts/documents, provider configuration and optional policy setup |
| /tasks | Task/run list, global hold, create and filter controls |
| /tasks/{id} | Revision, criteria, state/blockers, candidate list, usage, pause/stop/resume/restart and event history |
| /reviews/{id} | Exact job/account/payload/document versions, unresolved fields, approval basis, approve/reject |
| /profile | Verified/proposed/stale facts and provenance; versioned corrections |
| /documents | Import/readiness/version/selection, reviewed customization and explicit export |
| /history | Outcome provenance, attempts, corrections, retention coverage and filters |
| /analytics | Timezone, weekly boundary, separate attempt/outcome time bases and totals |
| /admin | Connections/revocation, policies, cost settings, health, backup/restore, privacy, updates |

Admin/lightweight modes share routes/models where applicable; lightweight hides advanced navigation but backend enforces every command independently. Mode switching is not credential elevation.

Client query model: snapshot_revision, last_event_cursor, connection_state, pending_commands keyed by command_id. Never optimistically display Paused/Stopped/Approved before durable acknowledgment. A pending action button can show Requested while preventing accidental repeated clicks; retry uses the same command_id. On revision conflict, refresh and show what changed rather than overwrite silently.

Store no long-lived secrets or sensitive profile copies in browser localStorage. Exact session transport is G-01. File previews request authorized short-lived access and do not expose unrestricted filesystem paths. UI text distinguishes missing data, unsupported flow, expired authority, provider failure and unknown outcome.

## Interaction details

Task creation: criteria editor marks each requirement must-have/preference; displays unknown-data policy and active authority before Start. Resume checks show current blockers. Stop confirmation identifies the run and queued work to cancel; already-submitted work is visibly not reversible. Pause all is always clearly labeled as global.

Review model includes action_version, job/account identifiers, document_version, prepared answer list with factual provenance, unresolved items and approval expiry. Batch review shows explicit membership. Editing any submitted content creates a new version; never mutate an approved review in place.

Manual handoff provides the approved Continue manually / Mark submitted / Mark not submitted / Leave unresolved choices. Owner-reported submission blocks duplicates but remains labeled user-reported. Mark not submitted after uncertain automated work still triggers reconciliation; it cannot alone unlock retry.

Keyboard navigation, visible focus, programmatic control labels, non-color status cues, system/light/dark selection and 200% zoom follow FD-007. Use focus return after dialogs and concise assistive status announcements. Layout mockups may vary without changing the specified controls and semantics.

## Extension protocol and tool allowlist

Envelope: {protocol_version, action_id, command_kind, run_id, generation, account_scope, tab_id, allowed_origin, payload_version, expires_at, tool, arguments}. Authenticated socket identity is established separately under G-01. Reject expired commands, unsupported versions/tools, mismatched context and arbitrary URLs outside scope.

| Tool | Typed arguments | Required observations |
|---|---|---|
| inspect_context | tab_id | Current origin, supported account context, adapter/page identity; no unrelated-tab data |
| discover_jobs | validated query/filter inputs | Stable IDs/URLs and available fields with provenance |
| inspect_form | adapter_id, expected_step | Field identifiers/types/options, required flags and version fingerprint |
| fill_fields | adapter_id, fingerprint, typed field values | Field-level results and fresh state; changed fingerprint blocks guessed filling |
| attach_document | document capability, expected upload field | Upload state/errors and selected document identity; no arbitrary worker filesystem path |
| advance_step | validated control identifier and expected step | Resulting known step or unsupported/uncertain state |
| submit_application | exact approved payload version and expected review fingerprint | Adapter-defined confirmation/failure evidence; receipt alone not success |
| inspect_outcome | existing action_id and supported context | Observed confirmation, failure or inability to determine |

Coordinator chooses a bounded tool; the extension maps it to validated CDP operations. No generic eval, arbitrary script, unrestricted CDP method, or freeform model selector endpoint is exposed. Tool allowlists are not proof of correct adapter behavior; validation still applies.

Document capability identifies one coordinator-prepared temporary upload artifact, bound to action/tab/expiry. The final CDP upload mechanism, file access checks and cleanup lifecycle must be validated under G-04/G-02; do not send provider credentials or broad filesystem access to the extension.

## Adapter structure

Adapter descriptor: id, version, supported_origin, page_signature, steps, field_map, permitted_transitions, outcome_rules, fixture_set_version. DOM locators/signatures are reviewed adapter data/code, not generated unvalidated by a model at runtime. Unknown layout/account/form meaning triggers manual handoff. Do not treat a disappearing modal or generic success toast as submission confirmation unless the validated rule establishes it for that flow.

Every inspection/fill/transition checks that the selected tab and expected account remain in scope. Domain/account changes invalidate the pending flow. User edits during preparation trigger a new fingerprint and coordinator revalidation before submission. Extension disconnect/context loss blocks new commands and leaves possibly executed actions for reconciliation.

Duplicate receipt of action_id returns known local receipt/result when available. Extension service-worker restart can lose transient context, so coordinator action state is authoritative and mutating commands are not blindly replayed. After reconnect exchange capabilities and unresolved action IDs, then inspect outcomes where supported.

G-04 requires actual reviewed fixtures, selectors/signatures, iframe/upload behavior and confirmation rules per initial form variant. No live adapter or proven LinkedIn capability is supplied by this document. Unsupported external employer pages remain handoff-only.

Acceptance: all primary routes, both modes, keyboard/theme/zoom, stale review, event resync, wrong tab/account/domain, forged document capability, repeated action ID, worker restart, changed form, failed upload, uncertain outcome and supported manual return. Test fixtures must contain no real credentials or unauthorized user data.
