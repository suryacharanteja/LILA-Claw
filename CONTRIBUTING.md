# Contributing

Thanks for your interest in contributing to **LILA Claw**! All
contributions are welcome, no matter how small or large.

## 1. Follow the existing code guidelines

This project documents its code style, naming conventions, configuration-variable
rules, and the **attestation format** for contributions. Read the project
specification and design documents in [`docs/`](docs/) before making changes,
and follow the approved implementation plan and work-item register. In
particular:

- **Code guidelines** — the legacy client (`runAiBot.py`, `modules/`) uses the
  function naming/docstrings/type hints, variable naming, and
  configuration-variable rules documented in the repository history.
- **Architecture** — all new work targets the LILA Claw architecture under
  [`src/lila/`](src/lila/): the FastAPI coordinator, LangGraph worker, Chrome
  extension, and React web client. Follow the approved LLD contracts and
  interfaces; do not bypass the coordinator, trust boundaries, or authority
  policies.
- **Attestation** — contributions to the legacy code need an attestation
  marker in the code, in the form:

  ```python
  ##> ------ <Your full name> : <github id> OR <email> - <Type of change> ------
      # your code
  ##<
  ```

  Keeping accurate attestation markers helps us maintain the contributor
  records in [`docs/contributor-consent/contributors.md`](docs/contributor-consent/contributors.md).

## 2. Where to send pull requests

Per the repository history, **pull requests should target the `community-version`
branch**, not `main`. PRs to other branches (especially `main`) are declined by
default. Once your change is tested, it is merged into `main` in the next cycle.
See the implementation plan for the milestone and verification gates any change
must pass.

## 3. Quick checklist before opening a PR

- [ ] My PR targets the `community-version` branch.
- [ ] I followed the architecture and code guidelines above.
- [ ] I added an attestation marker for my change where applicable.
- [ ] My contribution is my own work, or I have the right to submit it.
- [ ] I ran the relevant test suites (`.venv\Scripts\python -m pytest`,
      `npm run typecheck`, `npm run build`) and they pass.
- [ ] For changes touching contracts, schemas, or migrations: the generated
      models are regenerated and the JSON Schema validation still passes.

## 4. Licensing of contributions

This project is licensed under the **MIT License** (see [`LICENSE`](LICENSE)). By
opening a pull request, you agree that your contribution is your own work (or that
you have the right to submit it) and that it is provided under the MIT License --
that is, inbound contributions are under the same license as the project (inbound =
outbound).

Thank you for helping improve the project!