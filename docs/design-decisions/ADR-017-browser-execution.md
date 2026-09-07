# ADR-017 — Browser execution strategy

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-02, BR-04, BR-09, BR-20, BR-22, BR-23; ADR-002, ADR-010, ADR-016

## Approved decision

Use Chrome DevTools Protocol (CDP) through the TypeScript extension's chrome.debugger API, behind controlled browser tools. The extension remains the browser execution owner and connects to the FastAPI coordinator over the approved authenticated local WebSocket.

The worker requests bounded operations such as inspect page, fill field, and submit approved application. It does not receive unrestricted authority to issue arbitrary CDP commands. Backend and extension checks must enforce account, selected-tab, workflow, and action scope.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Content scripts only | Direct page-element reading and modification; useful for known forms | Some interactions and observations need additional mechanisms; not selected as sole executor |
| B: Extension-based CDP | Structured inspection, input, and browser events within the approved extension architecture | Debugger permission and attachment lifecycle complexity; approved |
| C: Separate Playwright/Selenium controller | Established automation-browser approach | Different browser/session setup and execution ownership; not selected for the primary path |

CDP provides a broader foundation for agent-driven work while retaining the intended existing-browser experience. Content scripts may be useful helpers, but no separate helper implementation is selected here. Do not introduce independent controllers manipulating the same tab. This decision does not select a Playwright library, require a remote-debugging port, or authorize arbitrary browser access.

## Execution and verification flow

1. Inspect the currently authorized tab and identify the supported form/action.
2. Return structured observations to the worker.
3. Fill supported fields with verified facts and approved narrative answers.
4. Reinspect values and page validation errors.
5. Recheck action authorization immediately before outward dispatch.
6. Observe the resulting state and record confirmed, failed, or uncertain outcomes.

A successful input command or click is not proof of business completion. Uncertain outcomes must be reconciled before retry. Transport acknowledgement, model confidence, or debugger attachment never grants outward-action authority.

## Boundaries and remaining validation

CDP does not guarantee reliable handling of changing pages, universal ATS coverage, file uploads, or successful submissions. Validate file upload and intended attachment identity, frame handling, attachment loss, permission behavior, account/tab changes, and outcome detection. Security challenges require appropriate user handling.

Detailed tool schemas, CDP command allowlists, page models, locator strategy, attachment ownership, navigation scope checks, stale-observation handling, browser version support, and verification evidence remain for HLD/LLD and FRD acceptance. Inspect current state after reconnect rather than replaying stale actions. Verify Edge compatibility before claiming support.

No extension has been changed, no browser permission granted, and no live action or implementation test is claimed by this approval.

## References

- [Chrome debugger API](https://developer.chrome.com/docs/extensions/reference/api/debugger): CDP access through the extension, permissions, supported domains, and target handling.
- [Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts): alternative page interaction mechanism.
- [OpenClaw extension](https://docs.openclaw.ai/tools/chrome-extension): reference use of chrome.debugger; does not establish verified MacMedha reuse.

Sources reviewed during the design discussion on 7 September 2026. Architectural fit is a project assessment, not a completed reliability benchmark.

## Approval record

Sponsor stated “option B: approved.” following the proposal for extension-based CDP with controlled browser tools and explicit outcome verification. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 records this decision only; the complete solution design and development remain unapproved.
