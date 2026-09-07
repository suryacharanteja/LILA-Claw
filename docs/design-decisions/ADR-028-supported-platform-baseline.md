# ADR-028 — Supported platform and validation baseline

Version: 1.0  
Status: Approved — Option A  
Date: 7 September 2026  
Source: approved BRD v1.1, BR-14, BR-21; ADR-017, ADR-021, ADR-022

## Approved decision

Target supported Windows 11 Home/Pro releases on Intel/AMD x64 with Chrome Stable for initial support. Claim support only after the relevant validation passes. Edge, ARM64, and other configurations are outside the initial support target; expansion requires separate validation and prioritization.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Windows 11 x64 and Chrome Stable | Smallest test matrix and fits the approved Chrome extension distribution path | Edge and ARM64 support deferred; approved |
| B: Same Windows baseline with Chrome and Edge | Browser choice at launch | Separate browser validation and extension distribution decisions; not selected |
| C: Broader Windows/architecture/browser baseline | Covers more existing machines | More packaging, compatibility, and lifecycle work; not selected |

The focused baseline makes validation of the complete autonomous workflow manageable. Chromium extension portability is not evidence that debugger access, pairing, upload, and recovery work identically in Edge. Windows 10 standard support ended on 14 October 2025; any ESU or special-edition support would require explicit scope.

## Approved validation targets

- Test an 8 GB RAM consumer machine with SSD storage; use 16 GB RAM as the preferred test configuration. These are targets, not measured minimum requirements or performance guarantees.
- Require no dedicated GPU for the initial hosted-AI approach. Optional local inference needs a separate hardware profile.
- Validate clean installation without Python, Node.js, developer tools, or preconfigured dependencies.
- Validate Chrome Stable at release and repeat critical compatibility checks as Stable updates. Record exact tested browser and Windows versions; do not assume all future versions work.
- Exercise startup, pairing, application review/submission, pause, browser disconnect, worker restart, update, and backup restoration.
- Test lock/unlock, sleep/resume, and logout. Preserve the existing user-session availability boundaries rather than promising uninterrupted browser execution.
- Determine required free space from the packaged application, retained artifacts, and backup policy before release.

## Remaining details and validation

Define the exact tested Windows releases/builds, hardware specifications, performance acceptance criteria, browser compatibility/retest process, and storage sizing during FRD and release planning. Use implementation evidence before publishing final minimum requirements. No platform tests, installation, or browser/OS changes were performed for this decision.

## References

- [Microsoft Edge extension porting](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/developer-guide/port-chrome-extension).
- [Windows 10 end of standard support](https://support.microsoft.com/en-us/windows/deployment/updates-lifecycle/windows-10-support-has-ended-on-october-14-2025).

## Approval record

Sponsor selected “A” in response to the focused Windows 11 x64 and Chrome-first support proposal. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

This approval selects a support and validation target. It does not claim successful qualification or approve the complete solution design, development, or release.
