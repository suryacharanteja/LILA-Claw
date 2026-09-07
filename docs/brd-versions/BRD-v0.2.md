# Business Requirements Document: Intelligent LinkedIn Activity Suite

Version: 0.2 — discovery draft, 6 September 2026

Owner: Product sponsor / user. Prepared from the initial pasted requirements and subsequent vision discussion.

Status: Requirements collection remains open. This document is not an approved scope baseline, solution design, FRD, or authorization to execute LinkedIn actions. No implementation is started by this document.

## 1. Vision and business problem

Create one intelligent browser extension experience dedicated to LinkedIn, controlled primarily from a separate client application. The product helps its operator search and apply for jobs, develop professional relationships, create content, engage with relevant content and communities, complete forms, and follow companies.

Today's repetitive browser work requires repeated data entry, context switching, and manual customization. Simple automation handles predictable fields but struggles with contextual writing and unfamiliar workflows. The desired product combines inexpensive deterministic execution with AI reasoning where customization improves the result.

The complete suite remains the product vision. A staged rollout controls delivery risk without removing requested capabilities from the roadmap.

## 2. Design thinking approach

Every feature must begin with a user need, not a proposed automation technique. During discovery, capture the trigger, current pain, desired outcome, constraints, and how success would be recognized. Map the journey before specifying screens or tools.

Provisional primary persona: one professional operating their own LinkedIn account on a standard personal computer, initially Windows. A dedicated always-on PC is an optional deployment. Job seeker, professional network builder, and content author are different journeys for this operator. Recruiter/business-development usage was present in the original concept but is not yet a confirmed launch persona.

Core jobs to be done:

- Find relevant opportunities and submit truthful, tailored applications with less repetitive effort.
- Maintain useful professional relationships without losing context or sending irrelevant outreach.
- Express the user's own expertise and voice through posts and comments.
- Delegate work locally, see what happened, intervene easily, and later issue commands remotely.

Design principles: visible control; evidence-backed personalization; progressive disclosure; accessible status and stop controls; explainable choices; recoverable failures; minimal repeated questions; economical use of AI; privacy by default.

Validation plan before development: review representative journeys with the sponsor; prototype the main client and compact extension panel; walk through successful and interrupted workflows; validate review effort and understanding of status. Low-fidelity prototypes are a later discovery deliverable, not created in this version.

## 3. Confirmed operating vision

- The sponsor's Windows machine with 64 GB RAM and an 8 GB GPU is one intended 24/7 host, not the minimum hardware requirement.
- The product must also work on standard consumer machines without requiring a dedicated GPU. Exact minimum and recommended specifications will be established through testing. This correction does not yet establish support for every operating system.
- Support both ordinary use while the computer/browser are available and optional always-on operation. Hosted AI enables the standard-machine path; local inference is optional and depends on hardware. Provider, cost, and data-transfer choices remain open.
- Chrome is the initial example; Edge support is also desired.
- The operator grants access to selected browser tabs for LinkedIn work.
- A full client UI provides command entry, administration, configuration, and monitoring.
- The extension executes browser work and provides a smaller secondary interface.
- Local instructions are the first interaction channel.
- Later releases introduce a messaging gateway, potentially Telegram and WhatsApp.
- Further releases introduce scheduled/cron work.
- Predictable actions avoid model calls; contextual tasks use AI.
- Delivery sequence: feasibility and BRD, then solution design, then FRD, then development.

Continuous availability means the system can receive and manage work whenever its dependencies are healthy. It does not mean continuous LinkedIn actions or guaranteed uninterrupted execution.

## 4. Business objectives and measurement

Objectives are to reduce operator effort, improve relevance and customization, preserve truthful profile information, make actions accountable, and recover safely from interruption.

Measure active operator time per completed workflow, answer correction rate, verified completion rate, duplicate side effects, recovery success, model cost per completed workflow, and user-reported trust. Track job responses/interviews and meaningful networking replies as longer-term outcomes; do not attribute causation without evidence.

Numeric targets require a baseline and agreement. Proposed launch gates: no fabricated factual answers in the agreed evaluation set; no duplicate outward actions in interruption tests; all outward actions have an audit record and explicit outcome status; all unsupported cases preserve progress and stop or request input. These are acceptance proposals, not achieved results or universal guarantees.

## 5. Business requirements register

Status C = explicitly requested; P = proposed supporting requirement. Phase assignments are proposals unless expressly described as future by the sponsor.

| ID | Requirement and business outcome | Status | Proposed delivery |
|---|---|---|---|
| BR-01 | Provide a primary client for instructions, preferences, profiles, administration, queue visibility, and activity history. | C | Phase 1 |
| BR-02 | Provide an extension with compact progress, connection status, review prompts, pause, stop, and browser-access controls. | C | Phase 1 |
| BR-03 | Search jobs using user criteria, explain relevance, shortlist, and prevent duplicate processing. | C | Phase 1 |
| BR-04 | Fill job applications with verified facts and tailored narrative responses; support resume selection/customization and review. | C | Phase 1 |
| BR-05 | Support professional discovery, connection requests, outreach, follow-ups, and relationship context, including batch planning. | C | Full scope; staged activation |
| BR-06 | Draft posts in the user's voice and support authorized publishing. | C | Full scope; staged activation |
| BR-07 | Support relevant likes/reactions, contextual comments, and catch-up activity for professional milestones. | C | Full scope; staged activation |
| BR-08 | Support following companies, company/page workflows, and community discovery and outreach. Exact actions require elaboration. | C | Full scope; staged activation |
| BR-09 | Assist with other LinkedIn forms; distinguish known fields from fields needing judgment or user input. | C | Phase 1 known forms; expand later |
| BR-10 | Preserve settings, progress, and history across navigation, browser closure, and process restart. | C | Phase 1 |
| BR-11 | Show daily, weekly, and total analytics, separating attempted, confirmed, failed, and uncertain outcomes. | C/P | Phase 1 |
| BR-12 | Provide light/dark themes and understandable workflows with one clear active execution owner. | C | Phase 1 |
| BR-13 | Protect local personal information, credentials, and activity records; provide export and deletion controls. | C/P | Phase 1 |
| BR-14 | Enable the Windows host to remain available with visible health, restart recovery, and graceful pauses. | C/P | Phase 1 |
| BR-15 | Use deterministic automation for stable actions and AI for contextual customization, with cost visibility. | C | Phase 1 |
| BR-16 | Accept authenticated remote commands and deliver useful results through a messaging gateway. | C | Phase 2 |
| BR-17 | Support scheduled recurring work with timezone, cancellation, missed-run, and overlap behavior. | C | Phase 3 |
| BR-18 | Extend remote channels and scheduling sophistication as validated by actual use. | P | Phase 4 |
| BR-19 | Support withdrawal workflows. Distinguish connection-invitation withdrawal from application withdrawal; do not assume platform availability. | C | Scope clarification needed |
| BR-20 | Bind permissions to account, workflow, tab/domain, and action; preserve meaningful user control across all command channels. | P | Phase 1 |
| BR-21 | Run the core product on standard consumer machines without a dedicated GPU; keep local AI inference optional and define a tested hardware support baseline. | C | Phase 1 |

Gender-based targeting from the original concept is excluded under the accepted earlier recommendation. Professional relevance replaces it. Random delays are not an account-safety guarantee. Unrestricted access to unrelated browser tabs is not necessary to fulfill the stated selected-tab vision.

## 6. Representative user journeys

### Job application

The user defines roles and constraints, reviews the ranked shortlist and matching reasons, delegates supported applications, and sees a tailored answer/resume preview where required. The system pauses on missing facts, verifies completion, and reports outcomes with evidence. Unknown outcomes are reconciled before any retry.

### Networking and content

The user sets professional audience, purpose, tone, and boundaries. The product proposes relevant recipients or content with rationale, supports editing, and executes only within the applicable authorization. The history retains enough context to avoid repetitive outreach and duplicate engagement.

### Local and future remote operation

The local client shows extension connectivity and selected tabs. Commands become trackable work items. A future remote command enters the same permission, queue, review, and reporting flow; messaging does not provide a bypass. Scheduled work uses the same flow and pauses when browser access or required authorization is unavailable.

## 7. Reliability and exceptional conditions

| Condition | Required business behavior |
|---|---|
| Missing, contradictory, or stale applicant information | Request clarification; do not guess or silently reuse conflicting facts. |
| Sensitive or consequential form choices | Use explicit user facts/preferences and applicable review policy. |
| Changed layout, conditional fields, unsupported language | Reassess the page; stop if the target cannot be identified reliably. |
| Duplicate jobs, commands, callbacks, or schedule events | Detect repeats and avoid duplicate external actions. |
| Network loss during submission/publication | Record uncertainty; inspect actual outcome before retrying. |
| Wrong account or tab; user starts manual interaction | Stop or yield ownership; revalidate context before resuming. |
| Invalid resume or upload rejected | Block completion until correct attachment is verified. |
| Logout, challenge, restriction, or platform limit | Pause and explain required user action; no automatic bypass. |
| Browser/worker/service crash; Windows restart | Restore durable work state; recheck prerequisites before executing. |
| PC asleep, logged out, offline, or updating | Report unavailability; do not claim work executed. |
| AI outage, invalid output, excessive cost | Preserve progress; use valid deterministic fallback or pause. |
| Malicious instructions within posts or job descriptions | Treat page content as data, not trusted commands. |
| Stop during an in-flight action | Prevent further dispatch and reconcile the action already sent. |
| External ATS redirect | Use an explicitly supported workflow or hand off; do not claim universal coverage. |
| Data corruption, storage full, failed update | Prevent unsafe continuation; expose recovery and rollback options. |
| Missed or overlapping scheduled run | Apply explicit skip/catch-up and serialization rules. |

The FRD will turn these categories into testable cases. Exhaustive coverage of an evolving external platform is not a credible promise.

## 8. Feasibility assessment

Overall: technically feasible for an initial single-user deployment, subject to platform constraints and validation. Public multi-user commercialization is a separate operating model and is not established by this assessment.

The sponsor's specified memory appears suitable for a modest browser workload and local orchestration; no capacity test has been performed. The core product must also support standard consumer machines, with no dedicated GPU requirement. Prefer bounded tab counts, modest concurrency, and an idle runtime that does not continuously call a model. GPU memory alone cannot establish optional local AI quality, latency, context capacity, or supported model size. CPU, GPU model, disk, target model, tab count, and concurrency remain unknown. Hosted AI provides a candidate standard-machine inference path but introduces data-transfer and recurring-cost decisions. Minimum RAM, supported OS versions, and latency targets must be benchmarked rather than advertised as verified.

The requested client/server experience is feasible. A recommended feasibility refinement is a local coordinating service plus the extension browser worker. The extension remains the execution endpoint in the user's mental model; durable queueing and later scheduling should not depend on its popup or volatile worker memory. This is an architectural candidate for solution design, not a finalized stack. Chrome documents service-worker termination and durable-state requirements [S6].

Selenium is an available deterministic execution option, not a requirement for every fixed field. Extension DOM operations or other browser control can also fill fixed fields without tokens. Evaluate the existing Selenium implementation for reuse; avoid independent controllers simultaneously manipulating the same tab.

24/7 intent requires host power/network reliability, process supervision, browser/session lifecycle handling, updates, backups, and observable health. A single PC is a single point of failure. Background service availability and an available authenticated browser session are separate conditions. Windows lock, logout, reboot, and remote-session behavior require explicit validation.

Platform feasibility remains conditional: LinkedIn prohibits unauthorized automation and certain engagement behavior [S7]. Engineering reliability and user consent do not grant platform permission. The product cannot promise restriction-free operation; distribution and commercial deployment require a platform-access assessment before launch.

## 9. Reference research and reuse decision

The sponsor confirmed that the reference is OpenClaw, not OpenCode or OpenCloud, and supplied https://github.com/suryacharanteja/MacMedha.git [S10]. MacMedha is the intended sponsor reference. Public page and raw README retrieval attempts failed during this quick review; its code, fork relationship, changes, license, and capabilities have not been verified. This access failure does not establish that the repository is private or missing. Earlier research below concerns upstream OpenClaw only.

The official repository found is openclaw/openclaw [S1]. Browser extension relay [S2] and browser automation [S3] are documented components of that project, not yet verified as two independent official repositories. The source repository and documentation were retrieved for research; nothing was installed, cloned, or executed. Attempts to retrieve specific source directories were inconclusive, so exact current component paths and implementation reuse remain unverified.

Useful reference patterns: separate command gateway and browser executor; explicit browser access; authenticated pairing; observable disconnect/reconnect; persistent scheduled work. OpenClaw documents manual extension setup as expected on Windows [S2], and offers Windows-specific runtime guidance [S4]. Its automation documentation describes persistence and a running gateway dependency [S5]. These are reference capabilities, not evidence that our proposed product already supports them.

Reuse requires examination of a pinned version, license and notices, dependencies, security boundaries, Windows behavior, and independent compatibility tests. Do not assume the full project should be embedded or copied. The earlier LinkedIn MCP and unofficial Python API remain optional research candidates, not core dependencies [S8, S9].

## 10. Phases and decision gates

1. Phase 1: local client, extension, reliable execution foundation, and a complete job-search/application journey. Preserve networking/content/company modules in the backlog and stage their activation. Exact first-release breadth awaits prioritization.
2. Phase 2: authenticated messaging gateway, initially one selected channel; remote instructions, status, and required reviews.
3. Phase 3: schedules/cron with persistent history, timezone rules, non-overlap, missed-run handling, and cancellation.
4. Phase 4: optional additional channel and more advanced recurring workflows; precise scope remains open.

Gate A: consolidate forthcoming requirements and baseline BRD with the sponsor. Gate B: prepare solution design and compare architectural options. Gate C: write FRD traced to BR IDs and acceptance cases. Gate D: develop and validate against the agreed gates. No dates, budget, or delivery commitments are inferred.

## 11. Open decisions

- Access to the supplied MacMedha source and identification of the exact browser components to assess for reuse.
- Personal-only use versus future customer accounts, licensing, and account isolation.
- Which full-suite activities must ship in the first release beyond job workflows.
- Client form: local web interface, desktop application, or both.
- Per-action autonomy, approvals, and revocation rules; specify publishing, messaging, and submissions separately.
- Hosted AI, local AI, or hybrid; permitted data transfer and monthly cost budget.
- GPU/CPU model, expected workload, tab count, and supported languages.
- Meaning of communities, pages automation, other forms, and withdrawal.
- Telegram bot/direct chat/channel semantics and WhatsApp integration route.
- Whether remote access includes the full client UI or messaging only.
- Availability targets, maintenance windows, retention, backup, and recovery objectives.

## 12. Sources

Sources accessed 6 September 2026; external projects and policies can change.

- S1: https://github.com/openclaw/openclaw
- S2: https://docs.openclaw.ai/tools/chrome-extension
- S3: https://docs.openclaw.ai/tools/browser
- S4: https://docs.openclaw.ai/platforms/windows
- S5: https://docs.openclaw.ai/automation/cron-jobs
- S6: https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle
- S7: https://www.linkedin.com/legal/user-agreement
- S8: https://github.com/gtm-api/linkedin-mcp
- S9: https://github.com/EseToni/open-linkedin-api
- S10: https://github.com/suryacharanteja/MacMedha (user-supplied; contents not retrieved)

## 13. Change log

v0.1: captured initial suite requirements, client/extension operating vision, Windows host, hybrid execution, later messaging and scheduling; added feasibility assessment, proposed phases, design-thinking approach, and unresolved decisions. Requirements discovery remains open.

v0.2: corrected reference to OpenClaw/MacMedha; recorded repository retrieval limitation; added standard-machine support and optional dedicated-host/local-inference modes. Reviewed the sponsor's separately prepared plan: its component breakdown is a useful solution-design input, while its different phase order remains a proposal rather than a change to the BRD baseline.
