# ADR-024 — Selective reuse and staged delivery

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; DD-009; approved architecture decisions

## Approved decision

Build the approved architectural foundation and selectively adapt existing components after validation. Preserve the approved BRD requirements and delivery phases. This decision selects a delivery approach; it does not authorize development before the agreed document gates.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Refactor the existing application | Preserves more working code initially | Requires migration of Flask, Selenium execution, and CSV history into the approved architecture; not selected as the overall approach |
| B: New foundation with selective validated reuse | Preserves useful work while maintaining approved component boundaries | Requires component assessment and integration testing; approved |
| C: Complete rewrite | Freedom from existing implementation constraints | Discards potentially useful logic and requires rediscovering behavior; not selected |

## Evidence and reuse boundaries

Local inspection found Flask and CSV history in app.py, Selenium dependencies in requirements.txt, an existing LangGraph answer graph in modules/ai/connections.py, resume generation in modules/resumes/generator.py, configuration validation in modules/validator.py, and existing tests. This is structural evidence, not proof of correctness or suitability.

Build the coordinator, worker, clients, extension, and storage around the approved decisions. The existing Flask interface, Selenium execution path, and CSV operational history require substantial replacement or migration to those boundaries. Do not retain competing browser controllers or bypass coordinator authority to accommodate old code.

Resume generation, configuration validation, provider integration, prompts, and tests are reuse candidates, not automatically accepted components. Assess correctness, dependencies, licensing, security, factual grounding, and compatibility with approved interfaces before adoption; adapt and test as needed. Preserve useful behavior as evidence even when implementation is replaced.

MacMedha remains a reference until its source and licensing can be verified. It is not a required dependency or an approved code import.

## Delivery increments within Phase 1

1. Establish admin/lightweight client modes, pairing, coordinator, worker, persistence, and permissions.
2. Connect job search, shortlist, verified facts, resume handling, and application review.
3. Validate authorized execution, outcome tracking, interruption recovery, and installation.

These increments organize implementation around a complete job-application journey. They do not reduce Phase 1 scope or replace its acceptance criteria. All other Phase 1 obligations, including analytics, privacy controls, activity records, and version history, require acceptance coverage.

Keep Telegram in Phase 2, scheduling in Phase 3, and additional channels/advanced recurring workflows in Phase 4. Broader networking, content, and company modules remain committed scope subject to platform feasibility; release assignments remain to be agreed through the existing process.

## Remaining work and validation

Prepare a component-level reuse assessment, requirements-to-release mapping, feasibility evidence, and migration approach for existing data where applicable. Detailed implementation sequence and acceptance tests follow in FRD, HLD, and module/release LLD. No code was changed or executed, dependencies adopted, or implementation tests run for this approval.

## Approval record

Sponsor selected “B” in response to the proposal “new foundation with selective, validated reuse”. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approves the reuse and staged-delivery approach, not the complete solution design or development/release authorization.
