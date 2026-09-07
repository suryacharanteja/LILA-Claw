# ADR-030 — Phase 1 supported-form scope

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-03, BR-04, BR-09; ADR-012, ADR-016, ADR-017, ADR-024

## Approved decision

Phase 1 targets complete supported LinkedIn application flows plus a defined catalog of other LinkedIn forms. Initially, the additional-form catalog is limited to simple job-search/filter forms supporting job discovery. Broader coverage is added after validation and release review.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Application forms only | Focused delivery | Would require explicit deferral of BR-09's other known forms; not selected |
| B: Applications plus selected known forms | Preserves the known-forms-first approach with testable boundaries | Requires catalog definition and validation; approved |
| C: General-purpose form agent | Broad potential coverage across LinkedIn and external sites | Greater variability and harder-to-prove reliability; not selected |

## Approved catalog boundary and behavior

- Application flows cover contact details, work and education history, screening questions, resume selection/upload, and final review where the specific flow has been validated.
- The initial additional-form catalog covers simple LinkedIn job-search/filter forms. Additional forms require validation and release review.
- Fill factual fields from verified information. Generate narrative answers from approved facts and request input for missing or contradictory information.
- For unsupported cases, preserve progress, explain what needs attention, and request manual completion. Do not guess unfamiliar form or field meanings.
- Detect external employer-site handoffs and present them to the user. Automated completion is outside the initial catalog until the relevant site, permissions, and flow are validated.
- Submission follows existing explicit-approval or scoped standing-permission policies. Catalog inclusion does not itself grant execution authority.

Supported means a documented journey with tested fields, transitions, and outcome checks. Similar appearance does not establish support. This approval selects scope for validation; it does not claim any particular live form has passed tests.

## Traceability and remaining work

This elaborates BR-03, BR-04, and BR-09 without changing their approved wording or the BRD phase sequence. Broader networking/content/company scope remains committed under its existing staged delivery decisions.

Specify exact catalog entries, supported variants, unknown-field detection, resume handling, handoff/manual-completion behavior, authorization checks, and acceptance cases in FRD and subsequent design. Retain all other Phase 1 requirements and distinguish manual handoff from a confirmed application outcome.

No browser actions, implementation, or form validation tests were performed for this decision.

## Approval record

Sponsor selected “B” in response to the proposal for supported LinkedIn application flows plus selected known forms, with the initial additional catalog limited to job-search/filter forms and broader coverage added after validation. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approves the Phase 1 form boundary, not the complete solution design or development/release authorization.
