# TESTING.md

How the Lead Generation Agent is tested — the automated suite plus a manual
testing checklist. Run everything from the repository root with the virtual
environment active.

## Automated Tests

### Full suite (483 tests)

```bash
pytest
```

Expected: `483 passed` in ~25–50 seconds. No internet is required; only the
browser-manager and R3 tests launch real Chromium (headless).

### Targeted suites

| What | Command | Expected |
| --- | --- | --- |
| Unit | `pytest tests/unit` | 298 passed |
| Integration | `pytest tests/integration` | 60 passed |
| CLI | `pytest tests/test_cli.py` | 6 passed |
| End-to-end | `pytest tests/test_end_to_end.py tests/end_to_end` | 14 passed |
| Requirement matrix | `pytest tests/test_requirement_matrix.py -v` | 14 passed (R1–R14) |
| Robustness | `pytest tests/requirement_tests` | 5 passed |
| Agent / GUI / LLM | `pytest tests/test_agent_executor.py tests/test_agent_memory_state.py tests/test_agent_tools.py tests/test_planner.py tests/test_tool_registry.py tests/test_llm.py` | 86 passed |
| Performance | `pytest tests/unit/test_performance.py -v` | passes (dedup 10k leads under budget) |

### Quality gates

```bash
ruff check app tests        # no lint findings
black --check app tests     # formatting clean
pip check                   # no broken dependencies
python -m compileall -q app # byte-compiles all modules
```

## Manual Testing Checklist

Use this checklist after installing and configuring the project (see
[RUN_GUIDE.md](RUN_GUIDE.md)).

### 1. Setup verification

- [ ] `python --version` → 3.12 or newer
- [ ] `pip check` → `No broken requirements found.`
- [ ] `playwright install chromium` completes without error
- [ ] `python -m pytest -q` → `483 passed`

### 2. CLI — happy path

- [ ] `python app/main.py` shows `Lead Generation Agent Ready` and
      `Please enter your search:`
- [ ] Typing `software companies in Karachi` and pressing Enter starts the run
- [ ] Banner prints `Lead Generation Agent v2.0.0 is ready to use.`
- [ ] The browser launches (visible when `HEADLESS=false`; headless otherwise)
- [ ] Console log lines show planning → search → extraction → export stages
- [ ] The boxed **execution summary** prints at the end (query, counts, file, time)
- [ ] Exit code is `0` on success
- [ ] A workbook `outputs/leads_software_companies_Karachi.xlsx` exists
- [ ] The workbook contains a `Leads` sheet with the 9 expected columns and data

### 3. CLI — interactive mode

- [ ] `python app/main.py` (no argument) shows `Please enter your search:`
- [ ] Typing `dentists in Lahore` and pressing Enter runs the same workflow
- [ ] `Ctrl+C` cancels cleanly without a traceback

### 4. CLI — invalid and edge-case input

- [ ] `python app/main.py`, then type `Karachi` (no location separator) → clear
      error `Could not determine a location for prompt '...'`, exit code `1`
- [ ] `python app/main.py`, then press Enter with an empty prompt → graceful
      error, no traceback
- [ ] A prompt with an empty business type → clear parser error
- [ ] A prompt with no location keyword (`in`/`near`/`around`) → clear parser error
- [ ] Unsupported `SEARCH_PROVIDER` in `.env` → startup validation error listing
      the allowed values

### 5. Agent planning (LLM)

- [ ] With the default `mock` provider, planning succeeds offline for every valid
      prompt and produces the expected `TaskPlan` steps
- [ ] With `LLM_PROVIDER=freellm` and a valid `FREELLM_API_KEY` (router reachable),
      planning runs end-to-end; an invalid/unreachable LLM falls back to the
      deterministic parser without crashing
- [ ] With `LLM_MODEL` set to anything other than `auto`, startup fails with a
      clear validation error (the FreeLLM Router performs all model selection)

### 6. Desktop GUI

- [ ] `python -m app.gui.main` opens the window (title **Lead Generation Agent**)
- [ ] Typing `plumbers in New York` and pressing Search shows the **Agent Plan**
      panel first
- [ ] During a run: the **Execution Timeline** highlights the active step,
      **Live Logs** stream color-coded events, and **Statistics** update live
- [ ] The **Current Business** card shows the business being processed and the
      extracted fields
- [ ] The **Progress bar** tracks the per-business counter (e.g. `Business 2 / 5`)
- [ ] The **Error Handling** card appears on a failure and shows the retry count
- [ ] After the run: the **Results** card shows counts, execution time, and the
      output workbook with **Open Excel / Open Folder / Run Again** buttons
- [ ] The **Open Excel** button opens the downloaded `.xlsx` in the default app
- [ ] The **Dark / Light** theme toggle switches the window styling
- [ ] An unplannable prompt (e.g. missing location) shows a graceful error, not a
      crash

### 7. Browser behavior

- [ ] With `HEADLESS=false`, the Google Maps page opens visibly and the query is
      submitted
- [ ] Results are scrolled to reach the configured `MAX_LEADS` (raise it to 50
      and confirm more businesses are collected)
- [ ] A business without a website still produces a row with an empty website
- [ ] A business without an email still produces a row with an empty email
- [ ] A failing business page is skipped after retry and the run continues

### 8. Excel output

- [ ] Headers are exactly: Business Name, Email, Phone Number, Website, Location,
      Provider, Search Query, Collected At, Source URL
- [ ] Header row is bold and frozen; columns are auto-sized
- [ ] Running the same query twice does not overwrite the first workbook (a
      timestamp suffix is added)
- [ ] Zero collected leads still produce a workbook (with no rows) and a
      successful summary — never a crash

### 9. Logging and debug artifacts

- [ ] `logs/application.log` exists and records each stage with timestamps
- [ ] Setting `LOG_LEVEL=DEBUG` adds per-step detail (selector attempts, consent
      checks, screenshot saves)
- [ ] On a failed extraction, a `debug/` screenshot + HTML dump is saved

### 10. Failure recovery

- [ ] With no internet / provider unreachable, the run fails gracefully with a
      clear error and a non-zero exit code (no traceback)
- [ ] A navigation failure is retried once before being reported
- [ ] A Google consent dialog, when present, is dismissed automatically
- [ ] An export failure (e.g. unwritable `OUTPUT_DIR`) is reported cleanly

## Reporting a failure

If any manual step fails: capture the full `logs/application.log`, the
`debug/` artifacts from the run, the console output, and the exact command.
Open an issue with the "Bug report" template
(`.github/ISSUE_TEMPLATE/bug_report.yml`).
