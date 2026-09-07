# ADR-005 — AI provider strategy

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-15, BR-21, BR-22

## Approved decision

Use a provider-independent AI layer, initially implementing and validating one hosted provider while allowing optional local inference. Do not implement every provider upfront. Specific providers, models, subscriptions, and data-transfer permissions are not selected or authorized by this decision.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: One hosted provider only | Simplest initial integration | Tighter coupling and provider/internet dependence; not selected as the architectural boundary |
| B: Provider-independent interface | Supports standard PCs, future provider changes, and optional local inference | Common interface and per-provider capability/evaluation checks required; approved |
| C: Local models only | Inference remains on the host without hosted inference dependency | Quality and responsiveness depend on hardware; unsuitable as the sole path for the standard-machine requirement; not selected |

The rationale is flexibility without requiring a dedicated GPU or building integrations speculatively. Local inference remains optional and subject to hardware and task validation.

## Operating requirements

- Provide a common interface for tasks such as drafting answers, extracting information, and explaining job matches.
- Start with one validated hosted adapter. Each subsequently supported provider/model must pass relevant task-specific evaluations and capability checks before enablement.
- Make data-destination choices explicit. An outage must not silently route private data to a different provider or endpoint.
- Track usage and estimated cost against configured budgets. Exact metering and budget enforcement remain detailed design work.
- Use deterministic execution where appropriate under the BRD. Provider selection does not give model output authority to execute actions.
- AI may draft wording but must not invent applicant facts. Evidence validation is a separate upcoming decision and remains required for every provider.

## Remaining decisions and verification

Provider/model selection, local runtime, SDK, interface schemas, timeout/retry policy, capability discovery, evaluation fixtures, numerical quality targets, and cost accounting are open. No provider subscription, endpoint connection, model download, or external data transfer is authorized by this record. No benchmark or implementation is claimed.

Validate adapter behavior, unsupported capabilities, malformed output, provider outage, budget handling, explicit destination selection, and prevention of silent cross-provider fallback during later implementation.

## Approval record

Sponsor stated “optionB: approved” after the proposal for a provider-independent layer starting with one hosted provider and permitting optional local inference. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records the integration strategy only, not the complete solution design or development authorization.
