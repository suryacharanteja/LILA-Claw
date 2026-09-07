# ADR-001: Local web client and language boundaries

Status: Approved by product sponsor  
Version: 1.0  
Decision date: 6 September 2026  
Product: LILA Claw  
Source requirements: BRD-LIS-001 v1.0.1, BR-01, BR-02, BR-10, BR-14, BR-15, BR-21

## Context

The product needs a full local client, a compact LinkedIn browser extension, and durable coordination. The existing repository contains Python job-processing, AI, configuration, and document capabilities. Standard consumer machines must be supported without a dedicated GPU.

The sponsor questioned whether two languages introduce runtime complexity, where the client runs, how it connects to Python, and whether this is an established architecture.

## Approved decision

- Build the primary client with React and TypeScript as a local web application opened in the user's browser.
- Build the browser extension and its compact interface with TypeScript, compiled to JavaScript.
- Use Python for the local backend: workflow coordination, AI integration, persistence access, authorization, and recovery.
- Serve the compiled client files and the local HTTP API from the same backend origin. The frontend accesses backend capabilities through structured API requests; it does not access the database directly.
- Bind the client API to the loopback interface. Apply authenticated sessions, request validation, and request-forgery protection; local binding alone is insufficient protection.
- Package the Python runtime with the installed product. Users should not need a separately installed Python or Node.js runtime. Node.js is a development/build dependency for the frontend.
- Provide a desktop launcher that starts the backend and opens the client. Closing the client tab does not itself terminate the backend. Provide an explicit application quit operation.
- The extension owns LinkedIn browser interaction. The backend coordinates it through a separately specified bridge.

## Options considered

| Option | Benefits | Costs / conclusion |
|---|---|---|
| Python backend + TypeScript interfaces | Reuses relevant Python capabilities; typed browser interfaces; clear responsibility boundaries | Two development toolchains and a versioned protocol; selected |
| TypeScript throughout | One primary development language and potentially shared contracts | Requires replacing or porting Python capabilities; browser/backend separation still exists |
| Plain JavaScript interfaces | Avoids a TypeScript compilation step | Less static checking of messages and state; not selected |
| Desktop shell around the frontend | Dedicated application window and desktop integration | Additional packaging and update responsibilities; deferred |

TypeScript does not inherently improve runtime speed over JavaScript. Both sides must validate messages at runtime. Reuse of Python code remains conditional on code review and behavior verification.

## Consequences and validation

Maintain a versioned API contract, compatible release packaging, explicit connection status, and recovery behavior. Validate on a clean Windows machine: installation without developer runtimes, launch, quit, occupied port, browser/backend restart, incompatible versions, authentication, and interrupted execution without duplicate actions.

The architecture is established; this product's installation, performance, and reliability have not yet been demonstrated. Browser availability and an authenticated LinkedIn session remain prerequisites for execution.

## Decisions not covered by this approval

Backend framework and production server; exact extension bridge transport; storage engine and schemas; installer/update tooling; AI provider; detailed API schemas; authentication bootstrap; support matrix; numeric performance targets; remote channels; final UI layouts. Periodic status fetching is an initial proposal, not a binding transport decision.

## Evidence

Sponsor statement: “design decision : approved” followed by “go ahead and document this,” in the current task, 6 September 2026. This approves the architecture described in the preceding discussion, not the entire unfinished solution design or implementation.

Official references reviewed on 6 September 2026:

- [Flask: serving a single-page application and API](https://flask.palletsprojects.com/en/stable/patterns/singlepageapplications/).
- [Flask: production deployment, including local deployment](https://flask.palletsprojects.com/en/stable/deploying/). A production server is required for the installed application.
- [Chrome: Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging). This establishes an available bridge option; transport selection remains open.

## Change control

Preserve this decision's history. A later material change requires a superseding ADR with rationale, impacts, and sponsor disposition. ADR approval does not imply completed implementation or validation.
