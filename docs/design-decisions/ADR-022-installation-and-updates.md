# ADR-022 — Installation and updates

Version: 1.0  
Status: Approved — Option B  
Date: 7 September 2026  
Source: approved BRD v1.1; DD-007; ADR-001, ADR-002, ADR-021

## Approved decision

Distribute LILA Claw through a bundled Windows installer with controlled application updates. Notify the operator of available updates, present release notes, and apply an authenticated, verified release after confirmation at a safe stopping point.

## Options and rationale

| Option | Benefits | Tradeoffs / disposition |
|---|---|---|
| A: Portable package with manual replacement | Simple for development and early testing | Manual setup and version management; not selected as the normal installation experience |
| B: Installer with controlled updates | Convenient setup and predictable upgrades with fewer interruptions to agent work | Requires installer, update verification, and recovery engineering; approved |
| C: Installer with automatic updates | Least ongoing maintenance | Requires stronger compatibility and recovery controls and changes software without review; not selected |

Option B keeps software changes deliberate while agents continue to operate autonomously under approved permissions. Application-update confirmation is separate from workflow action authorization.

## Approved behavior

- Bundle the Python runtime, backend, worker, supervisor, and compiled React/TypeScript client; end users do not install Python or Node.js separately.
- Provide a shortcut that starts LILA Claw and opens its local web UI. Retain ADR-021's optional startup-at-login setting.
- Check for available updates and show release notes; require operator confirmation before applying an application update.
- Verify release authenticity and integrity before installation.
- Stop new action dispatch, finish or safely pause current work, and back up affected data before updating. Backup handling must preserve existing credential-exclusion rules.
- Check health and reconcile pending work after updating; do not blindly replay uncertain external actions.
- Design recovery around database migration compatibility. Replacing application binaries alone is not a sufficient rollback guarantee.

## Browser extension distribution

The extension has a separate installation and update path. For normal Chrome distribution on Windows, use the Chrome Web Store; self-hosted installation requires enterprise policies. The installer guides installation and pairing. This decision does not authorize publication or enterprise-policy changes.

Backend and extension versions must negotiate compatibility because their updates may arrive separately. Application-update confirmation does not imply control over browser-managed extension updates. Unsupported combinations must prevent affected execution and explain how to recover.

**Native Messaging can remain a future setup helper**, if installation experience justifies it; it is not added to the initial transport by this decision.

## Remaining details and validation

Exact installer and packaging technology, signing and release distribution, update-check cadence, supported Windows versions and CPU architectures, supported browsers, migration and recovery mechanics, and extension release procedures remain open. PyInstaller is feasibility evidence, not a selected packaging implementation.

Validate installation on a clean supported machine without developer runtimes, launch and uninstall behavior, preservation of user data, valid and invalid update signatures, interrupted updates, active-work shutdown, migration failure and recovery, and mismatched backend/extension versions before release.

No installer, updater, publication, or implementation testing was performed under this decision.

## References

- [PyInstaller operating mode](https://www.pyinstaller.org/en/stable/operating-mode.html): bundles the interpreter and dependencies; builds are platform-specific.
- [Chrome extension distribution](https://developer.chrome.com/docs/extensions/how-to/distribute): supported extension distribution mechanisms and Windows restrictions.

## Approval record

Sponsor selected “B” in response to the installation and updates proposal. Recorded in task 01a0783f-92d5-78c1-b4c8-80424c720a17 on 7 September 2026.

Version 1.0 approves this installation and update approach. It does not approve the complete solution design or authorize development or release.
