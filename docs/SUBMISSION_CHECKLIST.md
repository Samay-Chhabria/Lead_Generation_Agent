# Submission Checklist

Use this checklist to verify the project is ready for submission. Each item is
either already verified by an automated test or by the manual step below.

## 1. Requirements (14 / 14 PASS)

- [x] **R1** Accepts a natural-language prompt
- [x] **R2** Business category and location extracted automatically
- [x] **R3** Browser automation (Playwright)
- [x] **R4** Businesses searched on a listing site
- [x] **R5** Name, email, phone, website, location collected
- [x] **R6** Multiple businesses collected (configurable limit)
- [x] **R7** Missing fields handled gracefully (empty strings, never crashes)
- [x] **R8** Excel `.xlsx` export (openpyxl)
- [x] **R9** Required Excel columns present
- [x] **R10** Meaningful filename (`leads_<business_type>_<location>.xlsx`)
- [x] **R11** Execution summary printed
- [x] **R12** Runs without runtime errors; graceful exception handling; logging
- [x] **R13** README with installation, dependencies, running, examples,
      folder structure, troubleshooting, output
- [x] **R14** Clean repository structure; correct files included/excluded

> Auto-verify: `pytest tests/test_requirement_matrix.py -v` → 14/14 PASS.

## 1b. Agent Enhancement (V2+)

- [x] Autonomous agent loop — Planner → AgentExecutor → ToolManager
      (`app/agent/`)
- [x] LLM-first planning with deterministic offline fallback
      (`app/agent/planner.py`)
- [x] 13-tool registry with guarded execution via `ToolManager`
- [x] Failure recovery: navigation retry, consent-dialog dismissal, and
      per-business skip with retry
- [x] Deterministic `ExecutionResult.summary` produced by every run
- [x] Provider extension stubs registered (Bing Maps, Yellow Pages, Yelp)
- [x] Desktop GUI (`app/gui/main.py`, run with `python -m app.gui.main`)
      with live execution timeline, streaming logs, statistics, progress bar,
      error/recovery card, results card, and dark/light themes

## 2. Automated Checks

Run from the repository root and confirm all pass:

```bash
pytest                  # all tests pass (483 tests)
ruff check app tests    # no lint findings
black --check app tests # formatting clean
pip check               # no broken dependencies
```

## 3. Documentation

- [x] `README.md` — overview, features, architecture diagram, installation,
      configuration, running (CLI + GUI), output, testing, troubleshooting,
      known limitations, future work
- [x] `RUN_GUIDE.md` — beginner setup and run walkthrough
- [x] `DEVELOPER_GUIDE.md` — architecture and extension guide
- [x] `PROJECT_STRUCTURE.md` — folder-by-folder reference
- [x] `TESTING.md` — automated + manual testing checklist
- [x] `CHANGELOG.md` — versioned milestones
- [x] `.env.example` — documents every configuration variable
- [x] `docs/REQUIREMENT_COMPLIANCE.md` — 14/14 compliance matrix
- [x] `docs/REQUIREMENT_VERIFICATION.md` — verification strategy and evidence
- [x] `docs/PROJECT_SUMMARY.md` — project overview and architecture
- [x] `docs/SUBMISSION_CHECKLIST.md` — this checklist

## 4. Files to Include

- [x] `README.md`
- [x] `RUN_GUIDE.md`
- [x] `DEVELOPER_GUIDE.md`
- [x] `PROJECT_STRUCTURE.md`
- [x] `TESTING.md`
- [x] `CHANGELOG.md`
- [x] `CONTRIBUTING.md`
- [x] `CODE_OF_CONDUCT.md`
- [x] `LICENSE`
- [x] `requirements.txt`
- [x] `pyproject.toml`
- [x] `.env.example`
- [x] `.gitignore`
- [x] `app/` source code
- [x] `tests/` test suite
- [x] `docs/` documentation

## 5. Files NOT to Include

- [ ] `node_modules/`
- [ ] `venv/`, `.venv/`
- [ ] `__pycache__/`, `*.pyc`
- [ ] Playwright browser binaries
- [ ] Generated Excel files (`outputs/*.xlsx`)
- [ ] Log files (`logs/*.log`)
- [ ] Debug artifacts (`debug/*.html`, `debug/*.png`, `debug/*.json`)
- [ ] `.env` (contains local secrets/overrides — never commit)
- [ ] `.pytest_cache/`, `.ruff_cache/`, `playwright-report/`, `test-results/`

All of these are already covered by `.gitignore`. Verify with:

```bash
git status --short                       # should show no generated/stale files
git ls-files | Select-String '\.env$'    # must return nothing
```

## 6. Packaging

Before zipping the project for submission:

1. Clean generated artifacts:
   ```bash
   git clean -nxd          # preview what would be removed
   git clean -fxd          # remove untracked generated files (venv, caches, outputs)
   ```
   > Note: this also removes `.venv`; recreate it after extraction if needed.
2. Create the archive from the repository root so the top-level folder name is
   preserved (e.g. `Lead_generation_agent.zip`).
3. Open the archive and confirm it contains the **Include** list (section 4)
   and none of the **Exclude** list (section 5).

## 7. Final Smoke Test (on a fresh machine)

1. Create and activate a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - Linux/macOS: `python -m venv .venv` then `source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. Run `python app/main.py`, then type `coffee shops in America` at the prompt.
5. Confirm the console summary prints and
   `outputs/leads_coffee_shops_America.xlsx` (or a timestamped variant) exists.
6. Run the automated checks from section 2 once more.
