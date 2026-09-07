# BRD v1.1 — Historical supporting context

Source: approved requirements baseline v1.0.1. Content below is retained verbatim from the 6 September 2026 review. It is background research, not a new technical decision or reverified feasibility finding.

## Feasibility assessment

Overall: technically feasible for an initial single-user deployment, subject to platform constraints and validation. Public multi-user commercialization is a separate operating model and is not established by this assessment.

The sponsor's specified memory appears suitable for a modest browser workload and local orchestration; no capacity test has been performed. The core product must also support standard consumer machines, with no dedicated GPU requirement. Prefer bounded tab counts, modest concurrency, and an idle runtime that does not continuously call a model. GPU memory alone cannot establish optional local AI quality, latency, context capacity, or supported model size. CPU, GPU model, disk, target model, tab count, and concurrency remain unknown. Hosted AI provides a candidate standard-machine inference path but introduces data-transfer and recurring-cost decisions. Minimum RAM, supported OS versions, and latency targets must be benchmarked rather than advertised as verified.

The requested client/server experience is feasible. A recommended feasibility refinement is a local coordinating service plus the extension browser worker. The extension remains the execution endpoint in the user's mental model; durable queueing and later scheduling should not depend on its popup or volatile worker memory. This is an architectural candidate for solution design, not a finalized stack. Chrome documents service-worker termination and durable-state requirements [S6].

The solution design shall evaluate a primary client, authenticated local gateway, browser executor, workflow management, intelligence, deterministic authorization/validation, and persistent storage as logical responsibilities. These need not be separate services. Prefer a small operational footprint suitable for standard machines. Whether the gateway is a Windows service or a supervised user process is a design decision; it must not assume a background service owns an interactive logged-in browser session.

Model-generated confidence and risk labels are advisory. Evidence must be checked against approved facts, and execution permissions calculated outside the model. Selecting salary, sponsorship, or consent values deterministically is valid only when the relevant user facts and preferences are explicit; predictable UI controls do not make the decision itself safe to infer.

Selenium is an available deterministic execution option, not a requirement for every fixed field. Extension DOM operations or other browser control can also fill fixed fields without tokens. Evaluate the existing Selenium implementation for reuse; avoid independent controllers simultaneously manipulating the same tab.

24/7 intent requires host power/network reliability, process supervision, browser/session lifecycle handling, updates, backups, and observable health. A single PC is a single point of failure. Background service availability and an available authenticated browser session are separate conditions. Windows lock, logout, reboot, and remote-session behavior require explicit validation.

Platform feasibility remains conditional: LinkedIn prohibits unauthorized automation and certain engagement behavior [S7]. Engineering reliability and user consent do not grant platform permission. The product cannot promise restriction-free operation; distribution and commercial deployment require a platform-access assessment before launch.

## Reference research and reuse

The sponsor confirmed that the reference is OpenClaw, not OpenCode or OpenCloud, and supplied https://github.com/suryacharanteja/MacMedha.git [S10]. MacMedha is the intended sponsor reference. Public page and raw README retrieval attempts failed during this quick review; its code, fork relationship, changes, license, and capabilities have not been verified. This access failure does not establish that the repository is private or missing. Earlier research below concerns upstream OpenClaw only.

The official repository found is openclaw/openclaw [S1]. Browser extension relay [S2] and browser automation [S3] are documented components of that project, not yet verified as two independent official repositories. The source repository and documentation were retrieved for research; nothing was installed, cloned, or executed. Attempts to retrieve specific source directories were inconclusive, so exact current component paths and implementation reuse remain unverified.

Useful reference patterns: separate command gateway and browser executor; explicit browser access; authenticated pairing; observable disconnect/reconnect; persistent scheduled work. OpenClaw documents manual extension setup as expected on Windows [S2], and offers Windows-specific runtime guidance [S4]. Its automation documentation describes persistence and a running gateway dependency [S5]. These are reference capabilities, not evidence that our proposed product already supports them.

Reuse requires examination of a pinned version, license and notices, dependencies, security boundaries, Windows behavior, and independent compatibility tests. Do not assume the full project should be embedded or copied. The earlier LinkedIn MCP and unofficial Python API remain optional research candidates, not core dependencies [S8, S9].

## Historical sources

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
