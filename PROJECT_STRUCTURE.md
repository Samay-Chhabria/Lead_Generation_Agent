# PROJECT_STRUCTURE.md

A folder-by-folder reference for the **Lead Generation Agent**. See
[README.md](README.md) for the end-user guide and
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for the architecture and extension
notes.

## Top Level

```
Lead_Generation_Agent/
├── app/                          # All application source code
├── tests/                        # 483 tests (unit/integration/E2E/requirement)
├── docs/                         # Architecture, compliance, summary, guides
├── outputs/                      # Generated Excel workbooks (git-ignored)
├── logs/                         # Rotating application logs (git-ignored)
├── debug/                        # Screenshots + HTML dumps (git-ignored)
├── .github/                      # CI workflow, issue templates, PR template
├── .env.example                  # Environment variable template
├── .gitignore
├── .python-version               # Python version hint
├── pyproject.toml                # Packaging, tooling (Black/Ruff/pytest) config
├── requirements.txt              # Dependencies
├── README.md                     # End-user guide
├── RUN_GUIDE.md                  # Beginner run guide
├── DEVELOPER_GUIDE.md            # Architecture & extension guide
├── PROJECT_STRUCTURE.md          # This file
├── TESTING.md                    # Manual testing checklist
├── CHANGELOG.md                  # Version history
├── CONTRIBUTING.md               # Contribution guide
├── CODE_OF_CONDUCT.md
└── LICENSE                       # MIT
```

## `app/`

| Path | Purpose |
| --- | --- |
| `main.py` | Entry point; starts the interactive CLI prompt. |
| `agent/` | Autonomous agent loop. |
| `application/` | Process-level lifecycle: config, logging, exit codes. |
| `browser/` | Playwright lifecycle management plus failure recovery. |
| `config/` | Environment-driven settings, constants, logging configuration. |
| `exceptions/` | Single exception hierarchy rooted at `LeadGenerationError`. |
| `exporter/` | Excel workbook construction and output file handling. |
| `extractor/` | Business detail extraction and website email discovery. |
| `gui/` | The PySide6 desktop GUI (pure presentation). |
| `llm/` | Unified LLM gateway (Free LLM Router) plus the offline mock. |
| `models/` | Data models. |
| `parser/` | Deterministic prompt → `SearchPlan` parsing. |
| `pipeline/` | Legacy orchestration, still exposed as the `pipeline` tool. |
| `processing/` | Normalization, validation, deduplication. |
| `providers/` | Search providers, registry, factory. |
| `tools/` | The 13-tool registry and wrappers. |
| `utils/` | Helpers, execution summary renderer, retry, timer. |

### `app/agent/`

| File | Purpose |
| --- | --- |
| `lead_generation_agent.py` | Console-facing facade; prints the banner, collects the prompt, exposes `plan` / `to_execution_plan` / `run`. |
| `planner.py` | Builds a `TaskPlan` from a prompt (LLM-first via `_plan_from_llm`, deterministic parser fallback). |
| `executor.py` | The agent loop: reason → run → fold, over the planned steps. |
| `tool_manager.py` | Guarded tool execution (`ToolManager.execute`); unknown/raising tools become failed `ToolResult`s. |
| `memory.py` | `AgentMemory` — what the agent has seen and done during a run. |
| `state.py` | `AgentState` — planner output and selected tools. |

### `app/tools/`

The registry (`registry.py`) wires up **13 tools**. Spec-named wrappers
delegate to the proven pipeline/extractor/export modules.

| Tool | Purpose |
| --- | --- |
| `search_tool` | Runs a search and returns business references. |
| `navigation_tool` | Opens a business listing page. |
| `business_collection_tool` | Collects business references from a search. |
| `business_extraction_tool` | Extracts details from a listing page. |
| `business_details_tool` | Per-business extraction with retry/skip. |
| `email_tool` | Extracts an email from a page. |
| `phone_tool` | Extracts a phone number from a page. |
| `website_tool` | Crawls a business website for an email. |
| `export_tool` | Exports processed leads to Excel. |
| `exporter_tool` | Legacy export tool (registry alias). |
| `summary_tool` | Produces the deterministic `ExecutionResult.summary`. |
| `pipeline_tool` | The full legacy pipeline as a single tool. |

Plus `google_maps_tool.py` (Google Maps wrapper, registered as a provider
alias) and `base.py` (tool protocol/base classes).

### `app/llm/`

| File | Purpose |
| --- | --- |
| `base.py` | `BaseLLM` / `LLMProvider` interface, plus `LLMStatusError` and `LLMNetworkError`. |
| `providers/freellmrouter.py` | **Unified LLM gateway** (OpenAI-compatible Free LLM Router); the only client the application uses. Always sends `model="auto"`; the router picks the model. |
| `factory.py` | `create_llm_provider` — auto-switches AI Agent Mode / Offline Mode. |
| `mock_provider.py` | Offline deterministic fallback; no API key required. |
| `_http.py` | Shared stdlib HTTP helper (no third-party dependency). |

### `app/providers/`

| File | Purpose |
| --- | --- |
| `base_provider.py` | `BaseProvider` contract. |
| `google_maps_provider.py` | The implemented Google Maps browser provider (owns `DEBUG_DIR = debug/`). |
| `bing_maps_provider.py`, `yellow_pages_provider.py`, `yelp_provider.py` | Registered extension stubs. |
| `provider_registry.py` | Name → class registry. |
| `provider_factory.py` | Creates a provider instance from settings. |
| `result_collector.py` | Scans/scrolls the results feed. |
| `provider_result.py` | Provider result payload. |
| `search_provider.py` | `SearchProvider` protocol. |

### `app/gui/`

| File | Purpose |
| --- | --- |
| `main.py` | Desktop GUI entry point (run with `python -m app.gui.main`). |
| `main_window.py` | Main window: prompt bar, Agent Plan, timeline, logs, stats, progress, error card, results. |
| `controllers/agent_controller.py` | Qt controller that runs the agent on a `QThread` and re-emits logger events as signals. |
| `widgets/` | Panels: `plan_panel`, `timeline_panel`, `live_logs_panel`, `stats_panel`, `progress_panel`, `business_card`, `error_card`, `cards`, `results_panel`. |
| `themes/` | `dark`/`light` QSS themes and token palette. |
| `icons/` | Programmatic icon/emoji glyphs used by the desktop UI. |
| `resources/tokens.py` | Shared design tokens (colors, fonts, spacing). |

## `tests/`

| Path | Suite | Count |
| --- | --- | --- |
| `tests/unit/` | Pure components with fakes; includes `test_recovery.py` (navigation/consent recovery) and `test_performance.py`. | 298 |
| `tests/integration/` | Module seams; browser tests launch real Chromium. | 60 |
| `tests/test_cli.py` | CLI subprocess tests. | 6 |
| `tests/test_end_to_end.py` + `tests/end_to_end/` | Full workflow with a fake provider + failure paths. | 14 |
| `tests/test_requirement_matrix.py` | One test per assignment requirement R1–R14. | 14 |
| `tests/requirement_tests/` | Robustness suite. | 5 |
| `tests/test_agent_*.py`, `test_planner.py`, `test_tool_registry.py`, `test_llm.py` | Agent era: planner, executor, tools, memory, LLM. | 86 |
| **Total** | | **483** |

| File | Purpose |
| --- | --- |
| `conftest.py` | Shared fixtures (settings, fakes, `run_cli`). |
| `fakes.py` | `FakePage`/`FakeLocator`/`FakeElement`, `FakeBrowser`, `FixedLeadsProvider`. |

## `docs/`

| File | Purpose |
| --- | --- |
| `architecture.md` | Design notes and diagrams. |
| `context.md` | Original assignment brief and requirements. |
| `REQUIREMENT_COMPLIANCE.md` | 14/14 compliance matrix (incl. agent enhancements). |
| `REQUIREMENT_VERIFICATION.md` | Verification strategy and evidence. |
| `PROJECT_SUMMARY.md` | Project overview and architecture. |
| `SUBMISSION_CHECKLIST.md` | Pre-submission verification checklist. |

## Generated (git-ignored)

| Folder | Contents |
| --- | --- |
| `outputs/` | `leads_<business_type>_<location>.xlsx` workbooks. |
| `logs/` | `application.log` (rotated at 5 MB × 3). |
| `debug/` | `*.png` screenshots, `*.html` dumps, `provider_export.json`. |
