# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Project Milestones

| Version | Date | Milestone | Theme |
| --- | --- | --- | --- |
| V1 | 2026-08-04 | **Browser Automation** — prompt parsing, Playwright scraping, extraction, Excel export, console summary | `1.0.0` |
| V2 | 2026-08-04 | **Robustness** — graceful failure handling, logging, execution summaries, packaging | *internal* |
| V3 | 2026-08-04 | **Modularity** — provider registry, extractor layers, website email enrichment | *internal* |
| V4 | 2026-08-04 | **Verification** — 14-requirement compliance matrix, E2E, performance suites | *internal* |
| V5 | 2026-08-05 | **AI Agent** — planner, executor, tool manager, LLM tool selection, failure recovery, PySide6 desktop GUI | `2.0.0` |

> Milestones V2–V4 are internal increments shipped within `1.0.0`; V1 and V5
> correspond to the tagged/versioned releases below.

## [2.0.0] - 2026-08-05 — V5: AI Agent

### Added

- Autonomous agent loop (`app/agent/`): `Planner` → `AgentExecutor` →
  `ToolManager`, giving the app a real plan → tool selection → execute →
  recover → validate → export → summarize flow on top of the existing pipeline.
- LLM-first planning (`app/agent/planner.py`): the LLM gateway (Free LLM Router)
  proposes the tool sequence via JSON; invalid or missing output falls back to
  the deterministic parser, so planning always works offline.
- Tool registry (`app/tools/`) with 13 tools: search, navigation, business
  collection, business extraction, website crawl, email/phone extraction,
  export, summary, and the legacy pipeline exposed as the `pipeline` tool.
- Spec-named wrapper tools that delegate to the existing proven modules
  (`search_tool.py`, `business_collection_tool.py`,
  `business_extraction_tool.py`, `export_tool.py`, `summary_tool.py`,
  `navigation_tool.py`, `pipeline_tool.py`).
- `ToolManager` (`app/agent/tool_manager.py`) — guarded tool execution that
  turns a raising or unknown tool into a failed `ToolResult` instead of killing
  the agent loop.
- Failure recovery: navigation retry + consent-dialog dismissal
  (`app/browser/page_manager.py`), listing open retry
  (`app/extractor/business_navigator.py`), and per-business skip with retry
  (`app/tools/business_details_tool.py`).
- `ExecutionPlan` model and `SummaryTool` — the executor now always produces a
  deterministic human-readable `ExecutionResult.summary`.
- Provider extension stubs: `BingMapsProvider`, `YellowPagesProvider`,
  `YelpProvider` registered in the provider registry (`app/providers/`).
- PySide6 desktop GUI (`app/gui/`) — a modern native window that calls the
  existing agent pipeline without duplicating business logic. It offers a
  natural-language prompt bar, an Agent Plan panel, a live execution timeline,
  streaming color-coded logs, live statistics, a per-business progress bar, an
  error/recovery card, a results card with an Excel download (Open Excel / Open
  Folder / Run Again), and dark/light themes.
- `app/gui/controllers/agent_controller.py` — runs the agent on a `QThread`,
  re-emits the executor's logging events as Qt signals, and suppresses stdlib
  logging on the worker thread so the GUI is the single output surface.
- GitHub Community Health files: issue templates (bug, feature request,
  documentation, question), pull request template, and contributing guide.
- GitHub Actions CI workflow (`.github/workflows/python.yml`) that runs lint,
  format, and the full test suite on push and pull requests.
- `CODE_OF_CONDUCT.md` (Contributor Covenant) and `LICENSE` (MIT).

### Changed

- `LeadGenerationAgent` exposes `plan(prompt)` and `to_execution_plan(plan)` so
  the GUI can show a plan before a run starts; `run(prompt, plan=...)` accepts a
  precomputed plan to avoid planning twice.
- Unified LLM gateway: the active path talks only to **Free LLM Router** (one
  OpenAI-compatible endpoint, one API key, stdlib-only client). Every request is
  sent with `model="auto"` and the router performs all model selection,
  rotation, fallback, and rate-limit recovery server-side. The application
  implements no client-side model list or fallback chain; only transient
  network failures (connection refused, DNS failure, socket timeout) are
  retried locally (up to 2 times). The legacy per-vendor providers were
  removed.
- Intelligent result selection: collected candidates are ranked (rating, review
  count, website, verified marker, position) before extraction and scrolling
  stops early once enough strong results are found. The default output is
  **5** leads and a run never exceeds **10** without an explicit count in the
  prompt; the configured `LEAD_MAX_RESULTS` default passes through the pipeline
  unchanged.
- Application version bumped to `2.0.0` (banner now reads
  `Lead Generation Agent v2.0.0`).
- The test suite now covers **483 tests** (unit 298, integration 60,
  end-to-end 14, requirement matrix 14, plus CLI, robustness, and
  agent/GUI/LLM suites), adding coverage for the agent loop, tool wrappers,
  `ToolManager`, planner fallback, the FreeLLM Router gateway, result
  selection, failure recovery, the summary field, and the GUI controller.
- Documentation synchronized with the new architecture: README (agent
  workflow, ASCII diagram, GUI, provider stubs, result volume rules),
  RUN_GUIDE, DEVELOPER_GUIDE, PROJECT_STRUCTURE, TESTING, and the requirement
  compliance matrix.
- Added the `PySide6` runtime dependency for the desktop GUI.

### Housekeeping (final cleanup pass)

- Removed verified-dead code: unused env-name constants
  (`DEFAULT_PAGE_URL`, `ENABLE_LLM_ENV`, `FREE_LLM_ROUTER_API_KEY_ENV`,
  `FREE_LLM_ROUTER_BASE_URL_ENV`, `DEFAULT_MODEL_ENV`), the unused
  `_env_str_any` helper, unused selector tables (`PHONE_SELECTORS`,
  `EMAIL_SELECTORS`), the unused `NAVIGATION_WAIT_MS` constant, the unused
  `ACTIVE_PROVIDER_NAME`, and the redundant `ensure_browser` alias.
- Cleaned leftover debug screenshots/HTML dumps and stale logs (kept the
  git-ignored `.gitkeep` placeholders).
- Black-formatted the codebase and verified ruff lint/import checks pass.
- `docs/architecture.md` rewritten to describe the current implementation.
- `.env.example` and README environment tables completed
  (`BROWSER_SLOW_MO`, `LLM_PROVIDER`, `LLM_MODEL`); `.gitignore` now covers
  `exports/` and all `*.xlsx` artifacts.
- Removed the Streamlit dashboard (`app/gui/streamlit_app.py`,
  `app/gui/log_stream.py`) and its tests, plus the `streamlit` and `pandas`
  dependencies — the PySide6 desktop GUI is now the single GUI.
- The CLI is interactive-only: `app/main.py` no longer accepts a positional
  query argument, so the prompt is always read from the console.

### Known limitations

See [README.md → Known Limitations](README.md#known-limitations) for the
current, intentionally documented limitations of the implementation.

## [1.0.0] - 2026-08-04 — V1: Browser Automation

### Added

- Natural-language prompt handling: interactive console input (run
  `python app/main.py`, then type the query), parsed into a structured
  `SearchPlan`.
- Deterministic prompt parser (`app/parser/prompt_parser.py`) that extracts the
  business type and location using the `in`/`near`/`around` separators.
- Browser automation layer (`app/browser/`) built on Playwright: factory,
  session, page manager, and a public `BrowserManager` facade with guaranteed
  resource cleanup.
- Modular search provider architecture (`app/providers/`): `BaseProvider`
  contract, `ProviderRegistry`, `ProviderFactory`, and a result collector;
  Google Maps implemented, with Bing Maps / Yellow Pages / Yelp reserved.
- Business detail extraction (`app/extractor/`): business name, email, phone,
  website, and location from each listing page.
- Website email enrichment (`app/extractor/`): crawls a business's own website
  (homepage then contact/about pages) to discover an email address, bounded by
  depth and page limits.
- Data processing pipeline (`app/processing/`): normalization, validation, and
  deduplication with graceful handling of missing or malformed data.
- Excel export (`app/exporter/`): formatted `.xlsx` workbook with a `Leads`
  sheet, bold frozen header, auto-sized columns, and meaningful collision-safe
  filenames (`leads_<business_type>_<location>.xlsx`).
- Execution summary (`app/utils/execution_summary.py`): boxed console report of
  the query, counts, output file, and elapsed time.
- Configuration (`app/config/`): environment-driven, validated `Settings`,
  centralized constants, and idempotent console + rotating-file logging.
- Unified exception hierarchy (`app/exceptions/`) rooted at
  `LeadGenerationError`.
- Automated test suite: 303 tests across unit, integration, end-to-end,
  requirement, CLI, and performance suites, including a 14-requirement
  verification matrix.
- Documentation: README, run guide, developer guide, architecture notes, and a
  requirement compliance/verification record.

### Changed

- Stabilized the end-to-end pipeline (`app/pipeline/`) so a failure in any
  stage (provider, extraction, export) never discards data already collected,
  and the browser is always released.

### Fixed

- Contained all failure paths (invalid prompt, provider outage, browser crash,
  export failure) so the application never terminates with an unhandled runtime
  error and the CLI exits with a meaningful code.
- Prevented silent overwrites of previously exported workbooks by timestamping
  filename collisions.

### Known limitations

- Only Google Maps is fully implemented; `bing_maps`, `yellow_pages`, and
  `yelp` are accepted provider slots that do not perform real searches yet.
- Extraction depends on the live Google Maps page markup; layout changes or
  CAPTCHAs may require selector updates.
- Email validation is structural (regex-based) only; there are no DNS/MX checks.
- The prompt parser supports a single location per prompt using
  `in`/`near`/`around`.
- Extraction and enrichment are sequential; there is no parallel scraping.

[2.0.0]: https://github.com/Samay-Chhabria/Lead_Generation_Agent/releases/tag/v2.0.0
[1.0.0]: https://github.com/Samay-Chhabria/Lead_Generation_Agent/releases/tag/v1.0.0
