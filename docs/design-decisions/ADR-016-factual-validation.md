# ADR-016 — Factual validation of AI-generated answers

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Resolves: DD-016  
Source: approved BRD v1.1, BR-04, BR-15, BR-22, BR-25; ADR-005

## Approved decision

Use a verified fact store, source-linked drafting, and validation before execution. Answer factual fields deterministically where possible. Require supporting evidence for generated factual claims instead of relying on model instructions or confidence alone.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Provide documents and instruct the AI to be accurate | Simple document-grounded drafting | Instructions alone do not reliably prevent invention or misinterpretation; insufficient as the validation system |
| B: Verified facts and controlled drafting | Structured values, source/version traceability, and checks before dispatch | Requires profile verification, versioning, and validation logic; approved |
| C: Second AI reviews every answer | Additional opportunity to detect inconsistencies | Cost/latency and correlated mistakes; not selected as the primary authority |

An additional model reviewer may be considered later; it is not required or separately approved by this decision.

## Approved workflow

1. Extract candidate facts from supplied resumes and other information. Extraction alone does not make a fact approved.
2. Operator verifies facts during setup. Retain their source and version.
3. Use approved facts or explicit preferences for factual fields such as employment dates, qualifications, location, notice period, sponsorship, and salary expectations. Do not infer sensitive choices from job requirements.
4. AI customizes narrative wording using supported claims only.
5. Before dispatch, validate required fields, source references, consistency, document versions, and applicable permissions.

Verified facts can be reused without repeated questions. New, contradictory, or stale information creates an exception. Approval cannot substitute for a missing fact, and model confidence cannot grant execution authority.

For example, three approved years of Python experience must not become five to match a listing. This illustrates preservation of facts, not a universal experience-calculation rule.

## Limits and exception behavior

Source links alone do not prove semantic support. Deterministic checks can verify structured values, but unrestricted prose is harder to validate. If support cannot be established, remove the unsupported claim, use a constrained factual formulation, or request clarification. Do not omit required information or change the meaning of an answer merely to pass validation.

This is a control strategy, not a guarantee that all generated prose is factually correct. Detailed acceptance criteria and evaluation must establish the supported cases and fail-safe behavior.

## Remaining design and validation

Define fact schemas, evidence granularity, explicit user declarations/preferences, stale-data rules, contradiction resolution, claim extraction, permissible transformations, and narrative-validation criteria in subsequent design/FRD work. Provider choice remains open under ADR-005.

Validate fabricated qualifications, numerical/date changes, conflicting documents, stale facts, unsupported claims, missing required answers, and material source/version changes before dispatch. No implementation or evaluation results are claimed.

## Approval record

Sponsor stated “opton B: approved” after the proposal for verified facts, source-linked drafting, and validation before execution. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this decision only; the complete solution design and development remain unapproved.
