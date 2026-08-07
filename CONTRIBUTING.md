# Contributing to Lead Generation Agent

Thank you for considering a contribution. This guide explains how to set up the
project, the development workflow, coding standards, and what is expected of a
pull request. Please also read the [Developer Guide](DEVELOPER_GUIDE.md) for the
full architecture and extension points.

> By participating, you agree to abide by the
> [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Table of Contents

- [Repository Setup](#repository-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standard)
- [Branch Naming](#branch-naming)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Code Review Expectations](#code-review-expectations)

---

## Repository Setup

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/<your-username>/Lead_Generation_Agent.git
   cd Lead_Generation_Agent
   ```

2. **Create a virtual environment** (requires Python 3.12+):

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

   The `[dev]` extra installs the quality tools (Black, Ruff, pytest).

4. **Install the Playwright browser**:

   ```bash
   playwright install chromium
   ```

5. **Configure the environment** (optional):

   ```bash
   cp .env.example .env
   ```

6. **Verify everything works**:

   ```bash
   pytest -q
   ruff check app tests
   black --check app tests
   ```

   All 483 tests must pass before you start changing code.

---

## Development Workflow

1. Create a feature branch from `main` (see [Branch Naming](#branch-naming)).
2. Make focused changes in a single layer of the application
   (`parser`, `browser`, `providers`, `extractor`, `processing`, `exporter`,
   `pipeline`, `config`, `utils`, `models`, `exceptions`).
3. Add or update tests for your change in the matching `tests/` directory.
4. Update documentation if you changed configuration, behavior, or added an
   extension point (`.env.example`, `README.md`, `RUN_GUIDE.md`,
   `DEVELOPER_GUIDE.md`, `CHANGELOG.md`).
5. Run the quality gates (below) locally.
6. Commit with a clear message and open a pull request.

### Quality Gates (run before every push)

```bash
ruff check app tests     # lint
black --check app tests  # formatting
pytest                   # full suite (483 tests)
```

---

## Coding Standard

The project enforces the following via [Ruff](https://docs.astral.sh/ruff/) and
[Black](https://black.readthedocs.io/) (configured in `pyproject.toml`):

- **Line length:** 100 characters.
- **Ruff rules:** `E` (pycodestyle), `F` (pyflakes), `W` (warnings),
  `I` (isort), `UP` (pyupgrade), `B` (bugbear).
- **Python target:** 3.12+; models use frozen/slotted dataclasses.
- **Type hints:** full annotations on all public signatures; return types always
  declared.
- **Docstrings:** every module and public class/method has a Google-style
  docstring (purpose, args, returns, raises).
- **Naming:** `snake_case` functions/variables, `PascalCase` classes,
  `UPPER_SNAKE` constants, private members prefixed with `_`.
- **Logging:** use the injected logger (`logger = logger or get_logger("...")`).
  `info` for lifecycle, `warning` for recoverable issues, `exception` for
  failures. Never log secrets.
- **Exceptions:** raise typed custom exceptions from the `LeadGenerationError`
  hierarchy; wrap low-level errors with `raise X(...) from exc`.
- **Immutability:** prefer frozen dataclasses; transform via
  `dataclasses.replace` instead of mutating inputs.

Format code with Black before committing:

```bash
black app tests
```

---

## Branch Naming

Use descriptive, hyphen-separated branch names prefixed by category:

| Prefix    | Use for                                   | Example                        |
| --------- | ----------------------------------------- | ------------------------------ |
| `feature/`| New functionality or extension points     | `feature/add-csv-exporter`     |
| `fix/`    | Bug fixes                                 | `fix/browser-close-on-timeout` |
| `docs/`   | Documentation only changes                | `docs/update-readme-badges`    |
| `refactor/`| Non-functional code improvements         | `refactor/simplify-collector`  |
| `ci/`     | Build, tooling, or workflow changes       | `ci/cache-playwright-browsers` |
| `test/`   | Test-only additions or updates            | `test/cover-email-crawler`     |

```bash
git checkout -b feature/add-csv-exporter
```

---

## Commit Message Conventions

- Write **imperative, concise, lowercase** subjects under 72 characters.
- Reference the requirement or area you touched where useful.
- Do not end the subject with a period.

Examples:

```text
add csv exporter behind a shared exporter interface
fix browser leak when provider initialization fails
update .env.example to document new LOG_LEVEL values
docs: link the run guide from the README
ci: cache playwright browsers between runs
```

If the change relates to a tracked issue, append it: `closes #42`.

---

## Pull Request Process

1. Push your branch and open a pull request against `main` using the
   [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
2. Keep the PR small and focused on one concern. Large refactors are easier to
   review in pieces.
3. Fill in the description, describe the testing you ran, and tick the
   checklist items that apply.
4. Reference any related issues or requirement numbers.
5. Ensure the CI workflow (lint, format, tests) passes on your branch. Do not
   ask for a review before CI is green.
6. After review, address feedback in new commits (do not force-push over review
   history unless asked).

---

## Testing Requirements

- **Add tests for every change.** Bug fixes need a regression test; new
  features need tests for the happy path and the failure path.
- Place tests in the matching suite under `tests/`:
  - pure logic → `tests/unit/`,
  - seams between modules → `tests/integration/`,
  - full user workflow → `tests/test_end_to_end.py` / `tests/end_to_end/`.
- Reuse the shared fixtures and fakes (`tests/conftest.py`, `tests/fakes.py`)
  instead of creating new mocks where possible.
- Keep tests **offline** and deterministic: use the fake browser/provider; do
  not depend on the network. Only browser-automation tests launch real
  Chromium.
- The full suite must pass locally before opening a PR:
  `pytest` (expect `483 passed`).
- If you change behavior covered by the requirement matrix, re-run
  `pytest tests/test_requirement_matrix.py -v`.

---

## Code Review Expectations

- The project is reviewed for **correctness, layering, and testability** before
  it is merged.
- Reviewers check: single-responsibility boundaries, injected dependencies
  (no hidden singletons at call sites), typed exceptions from the
  `LeadGenerationError` hierarchy, correct logging levels without secrets,
  unbounded loops prevented (`MAX_LEADS`, timeouts, crawl bounds), and that
  tests assert observable outcomes.
- Changes that degrade the offline testability of the suite will be sent back.
- Keep the discussion constructive; be specific and reference code lines.

---

## Getting Help

- Open a [Question](.github/ISSUE_TEMPLATE/question.yml) issue for anything
  unclear.
- Read `docs/architecture.md` and `DEVELOPER_GUIDE.md` before diving in.
