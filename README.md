# Lead Generation Agent

> Turn a single natural-language prompt — **"software companies in Karachi"** —
> into a clean, deduplicated Excel lead list, automatically.

The **Lead Generation Agent** is an AI-powered application that understands a
plain-English business search request, plans the work, drives a real browser
(Playwright) through business listing websites, extracts contact details for
each business, cleans and deduplicates the data, and exports everything to a
formatted `.xlsx` workbook — then summarizes what it did. It is built as a real
agent: **plan → tool selection → execute → recover → validate → export →
summarize**.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Setup](#setup)
  - [Virtual Environment Setup](#virtual-environment-setup)
  - [Install Dependencies](#install-dependencies)
  - [Playwright Installation](#playwright-installation)
  - [Environment Configuration](#environment-configuration)
- [Running](#running)
  - [Running the CLI](#running-the-cli)
  - [Running the Desktop GUI](#running-the-desktop-gui)
  - [Example Search Prompts](#example-search-prompts)
- [Generated Excel Files](#generated-excel-files)
- [Logging](#logging)
- [Debug Folder](#debug-folder)
- [Screenshots](#screenshots)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)
- [License](#license)
- [Author](#author)

## Project Overview

The user provides only a prompt, e.g.:

```text
coffee shops in Karachi
```

The agent automatically:

1. **Plans** the task — extracts the business type (`coffee shops`) and
   location (`Karachi`) deterministically, optionally asking the configured LLM
   to pick the tool sequence (offline fallback always works).
2. **Launches a real browser** (Playwright/Chromium) and searches a business
   listing website (Google Maps).
3. **Collects** business listings up to the configured limit (`MAX_LEADS`,
   default **5**; never more than **10** without an explicit count in the
   prompt), scrolling the results feed as needed and stopping early once enough
   strong candidates are found.
4. **Extracts** the name, email, phone number, website, and location from each
   business page, and crawls each business's own website to discover an email
   when the listing has none.
5. **Recovers** from failures — navigation is retried once, consent dialogs are
   dismissed automatically, and a business that cannot be opened is skipped so
   the rest are still processed.
6. **Validates and processes** the leads — filters by any requested minimum
   rating, normalizes, validates, and deduplicates.
7. **Exports** the final leads to a formatted `.xlsx` workbook with a
   meaningful filename.
8. **Summarizes** the run with a human-readable summary and a console report.

## Features

- **Autonomous agent loop** — `Planner` → `AgentExecutor` → `ToolManager` with
  internal reasoning, tool selection, and failure recovery.
- **Natural-language input** — no hand-written queries; business type and
  location are parsed automatically.
- **One unified LLM gateway** — the agent talks only to **Free LLM Router**, a
  single OpenAI-compatible endpoint unlocked by one API key. No per-vendor SDKs
  or providers exist in the active path.
- **Zero model management** — every request is sent with `model="auto"` and the
  router picks the best model itself. The app keeps **no model list, no fallback
  chain, and no model configuration** to maintain — there is nothing to reorder
  or update when new models appear.
- **Automatic Offline ↔ AI mode switching** — `ENABLE_LLM=true` + a
  `FREELLM_API_KEY` enables **AI Agent Mode** (the LLM understands the request,
  builds a plan, picks tools, observes results, and keeps going until done).
  `ENABLE_LLM=false` or an empty key drops to deterministic **Offline Mode**:
  the parser, browser automation, and Excel export all keep working with no
  network calls and no runtime errors.
- **13-tool registry** — search, navigation, business collection/extraction,
  website crawling, email/phone extraction, export, summary, and the legacy
  pipeline-as-a-tool, resolved by name and executed through a guarded
  `ToolManager`.
- **Real browser automation** — Playwright drives real Chromium; no API keys or
  paid listing APIs are needed.
- **Five contact fields per business** — name, email, phone, website, location
  — plus **website email enrichment** (homepage → contact/about pages).
- **Configurable volume** — collect 10, 25, 50, or 100+ leads via `MAX_LEADS`.
- **Intelligent result selection** — the default is **5** businesses and a run
  never collects more than **10** without an explicit request; say *"find 3
  coffee shops"*, *"collect 50 software companies"*, or *"top 10 restaurants"* to
  control the volume. Collected candidates are ranked by rating, review count,
  website, verified marker, and position before extraction, and scrolling stops
  early once enough strong results are found.
- **Robust data handling** — missing fields become empty strings, unusable
  records are skipped, duplicates are removed; one failure never aborts a run.
- **Failure recovery** — navigation retry, consent-dialog dismissal, and
  per-business skip with retry.
- **Professional Excel export** — formatted `.xlsx` with a bold frozen header,
  auto-sized columns, and meaningful collision-safe filenames.
- **Two interfaces** — an interactive CLI and a **PySide6 desktop GUI** with a
  live execution timeline, streaming logs, statistics, a progress bar, and a
  completion screen.
- **Modular providers** — Google Maps is implemented; Bing Maps, Yellow Pages,
  and Yelp ship as registered extension stubs.
- **Fully tested** — 483 tests (unit, integration, end-to-end, requirement,
  performance) covering all 14 assignment requirements.

## Architecture

The application follows a layered, single-responsibility design. Every layer is
injectable and independently testable.

```
            User prompt (interactive)
                             |
                             v
                       app/main.py  (entry point only)
                             |
                             v
        LeadGenerationApplication  (config + logging + lifecycle)
                             |
                             v
        LeadGenerationAgent  (console facade: plan -> run -> summarize)
                             |
             +---------------+---------------+
             |                               |
             v                               v
      Planner (prompt -> TaskPlan)      LLM gateway (Free LLM Router)
      LLM-first, parser fallback        ENABLE_LLM + API key -> AI mode
             |                          else deterministic offline mode
             v
       AgentExecutor (agent loop: reason -> run -> fold -> recover)
             |
             v
        ToolManager (guarded tool execution)
             |
             v
      Tools: search | navigation | collection | extraction |
             |  website crawl | email/phone | export | summary
             |
             v
      SearchPipeline / PipelineTool
        |        |
        |        +--> ProcessingPipeline (normalize + validate + dedupe)
        |                        |
        v                        v
   ProviderFactory           ExcelExporter -> outputs/*.xlsx
        |
        v
   GoogleMapsProvider (real Playwright browser via BrowserManager)
        |
        +--> ResultCollector (business references)
        +--> BusinessNavigator -> BusinessDetailExtractor
                              (name, email, phone, website, location)
        +--> ContactPageCrawler -> WebsiteNavigator + EmailDiscoveryEngine
```

| Layer | Responsibility |
| --- | --- |
| `app/main.py` | Entry point only; starts the interactive prompt. |
| `app/application/` | Application lifecycle: configuration, logging, clean startup and shutdown. |
| `app/agent/` | Agent facade, planner, executor (agent loop), tool manager, memory, and state. |
| `app/tools/` | 13 tools: search, navigation, collection, extraction, details, crawl, email, phone, export, pipeline, summary. |
| `app/parser/` | Deterministic prompt-to-`SearchPlan` parsing (used by the pipeline tool). |
| `app/gui/` | The PySide6 desktop GUI. It subscribes only to the `AgentExecutionLogger` event bus — no business logic. |
| `app/llm/` | Unified LLM gateway (Free LLM Router) plus the offline mock fallback. |
| `app/browser/` | Playwright lifecycle management plus failure recovery. |
| `app/providers/` | Search providers, registry, factory, result collector. |
| `app/extractor/` | Business detail extraction and website email discovery. |
| `app/processing/` | Normalization, validation, deduplication. |
| `app/exporter/` | Excel workbook construction and output file handling. |
| `app/models/` | `Lead`, `SearchPlan`, `BusinessReference`, `ExecutionResult`, `TaskPlan`, `ExecutionPlan`. |
| `app/config/` | Environment-driven settings, constants, and logging. |
| `app/utils/` | Helpers, execution summary renderer, retry, timer. |
| `app/exceptions/` | Single exception hierarchy rooted at `LeadGenerationError`. |

## Folder Structure

```
Lead_Generation_Agent/
├── app/                          # Application source code
│   ├── main.py                   # Entry point
│   ├── agent/                    # Planner, executor, tool manager, memory, state
│   ├── application/              # Lifecycle: config, logging, exit code
│   ├── gui/                      # Desktop GUI (PySide6)
│   ├── tools/                    # 13-tool registry and wrappers
│   ├── llm/                      # Unified LLM gateway (Free LLM Router) + offline mock
│   ├── parser/                   # Prompt → SearchPlan
│   ├── browser/                  # Playwright lifecycle management + recovery
│   ├── providers/                # Search providers, registry, factory
│   ├── extractor/                # Business detail + email extraction
│   ├── processing/               # Normalize, validate, deduplicate
│   ├── exporter/                 # Excel (.xlsx) export
│   ├── models/                   # Data models
│   ├── config/                   # Settings, constants, logging config
│   ├── utils/                    # Helpers, execution summary, retry, timer
│   └── exceptions/               # Custom exception hierarchy
├── tests/                        # 483 tests (unit/integration/E2E/requirement)
├── docs/                         # Architecture, compliance, summary, guides
├── outputs/                      # Generated Excel workbooks (git-ignored)
├── logs/                         # Rotating application logs (git-ignored)
├── debug/                        # Screenshots + HTML dumps (git-ignored)
├── .env.example                  # Environment variable template
├── .gitignore
├── .python-version               # Python version hint
├── pyproject.toml                # Packaging, tooling, pytest config
├── requirements.txt              # Dependencies
├── README.md                     # This file
├── RUN_GUIDE.md                  # Beginner run guide
├── DEVELOPER_GUIDE.md            # Architecture & extension guide
├── PROJECT_STRUCTURE.md          # Folder-by-folder reference
├── TESTING.md                    # Manual testing checklist
├── CHANGELOG.md                  # Version history
├── CONTRIBUTING.md               # Contribution guide
├── CODE_OF_CONDUCT.md
└── LICENSE                       # MIT
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a folder-by-folder
reference, and [RUN_GUIDE.md](RUN_GUIDE.md) for a beginner-friendly setup
walkthrough.

## Installation

### Prerequisites

- **Python 3.12 or newer** (enforced by `pyproject.toml`).
- **Git** (to clone the repository).
- An internet connection (for installing dependencies, downloading the Playwright
  browser binary, and searching live business listing sites).

### Clone the Repository

```bash
git clone https://github.com/Samay-Chhabria/Lead_Generation_Agent.git
cd Lead_Generation_Agent
```

## Setup

### Virtual Environment Setup

Create and activate an isolated Python environment:

```bash
python -m venv .venv
```

| Operating system | Activation command |
| ---------------- | ------------------ |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows CMD | `.venv\Scripts\activate.bat` |
| Linux / macOS | `source .venv/bin/activate` |

> If PowerShell blocks activation, run once:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Install Dependencies

With the virtual environment active:```bash
pip install -r requirements.txt
```

Runtime dependencies: `playwright`, `python-dotenv`, `openpyxl`, `rich`,
`PySide6`. Developer tooling (Black, Ruff, pytest):

```bash
pip install -e ".[dev]"
```

### Playwright Installation

The Playwright Python package contains the automation *library* only — the
browser binary must be downloaded separately:

```bash
playwright install chromium
```

Or install all supported engines (Chromium, Firefox, WebKit):

```bash
playwright install
```

Verify:

```bash
playwright --version
playwright install --list
```

> If `playwright` is not recognized, run it through Python:
> `python -m playwright install chromium`

### Environment Configuration

Copy the template and adjust values if needed:

```bash
cp .env.example .env
```

The application loads `.env` automatically at startup (`python-dotenv`). It is
git-ignored — never commit it.

| Variable | Default | Allowed values | Purpose |
| --- | --- | --- | --- |
| `PLAYWRIGHT_HEADLESS` | `true` | `true`/`false` | Run the browser without a visible window (alias `HEADLESS`). |
| `PLAYWRIGHT_TIMEOUT` | `30000` | positive integer (ms) | Maximum wait for page loads and results (alias `TIMEOUT`). |
| `LEAD_MAX_RESULTS` | `5` | positive integer | Default maximum businesses to collect (alias `MAX_LEADS`). The default is 5; without an explicit request the run never exceeds 10. |
| `SEARCH_PROVIDER` | `google` | see below | Which search provider the pipeline uses. |
| `BROWSER_TYPE` | `chromium` | `chromium`, `firefox`, `webkit` | Browser engine. |
| `BROWSER_SLOW_MO` | `300` | non-negative integer (ms) | Artificial delay between browser actions (visual debugging); `0` disables it only when running headless. |
| `OUTPUT_DIR` | `outputs` | any path | Where Excel workbooks are saved. |
| `LOG_DIR` | `logs` | any path | Where the rotating log is written. |
| `LOG_LEVEL` | `INFO` | `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG` | Logging verbosity (use `DEBUG` for detailed diagnostics). |
| `LLM_PROVIDER` | `freellm` | `freellm` | LLM gateway (only one exists; legacy names `freellmrouter`/`free_llm_router` still normalize to it). |
| `LLM_MODEL` | `auto` | must be `auto` | Fixed to `auto` — the router selects the model on every request. |
| `ENABLE_LLM` | `true` | `true`/`false` | Master switch for AI Agent Mode. |
| `FREELLM_API_KEY` | *(empty)* | key string | Your Free LLM Router API key. Empty ⇒ Offline Mode. (Legacy alias: `LLM_API_KEY`.) |
| `FREELLM_BASE_URL` | `http://localhost:3001/v1` | URL | The router's OpenAI-compatible endpoint. (Legacy alias: `LLM_BASE_URL`.) |

**Supported `SEARCH_PROVIDER` values:** `google`, `google_maps` (both map to
the implemented Google Maps provider) and the reserved extension slots
`bing_maps`, `yellow_pages`, `yelp`.

Configuration is validated at startup; invalid values abort with a clear error.
`OUTPUT_DIR` and `LOG_DIR` are created automatically if they do not exist.

### AI Agent Mode vs Offline Mode

The application is model-agnostic and decides its mode automatically at startup:

| Condition | Mode | What happens |
| --- | --- | --- |
| `ENABLE_LLM=true` **and** `FREELLM_API_KEY` set | **AI Agent Mode** | The LLM understands your request, reasons about the task, builds an execution plan, chooses tools, observes tool outputs, and iterates until the task is done. Browser automation is just one tool among many. |
| `ENABLE_LLM=false` | **Offline Mode** | The deterministic parser extracts business type + location, and the default tool sequence runs. LLM reasoning is skipped. |
| `FREELLM_API_KEY` empty | **Offline Mode** | Same deterministic behaviour; no network calls, no runtime errors. |

In both modes the CLI, GUI, browser automation, Excel export, and pipeline
behave exactly the same — only the planning intelligence differs.

### Getting a Free LLM Router API key

1. Follow the [Free LLM Router](https://github.com/freellm/free-llm-router)
   docs to run or reach your router instance (it exposes a single
   OpenAI-compatible endpoint).
2. Obtain your API key from the router (a self-hosted router, or the service
   you chose). One key unlocks whichever models your router instance exposes —
   the exact list depends on the router, and new models are picked up
   automatically with `model="auto"`.
3. Paste the key into `.env`:
   ```dotenv
   ENABLE_LLM=true
   LLM_PROVIDER=freellm
   FREELLM_API_KEY=your-key-here
   FREELLM_BASE_URL=http://localhost:3001/v1
   LLM_MODEL=auto
   ```
4. Restart the application. The console/desktop GUI shows `ai` mode when active.

### Model selection (`model="auto"`)

The application implements **no model list and no fallback chain**. Every LLM
request is sent to the router with `model="auto"`, and the **router** decides
which model to use — it is the single place where models are chosen, so there
is nothing to configure or maintain on the application side. New models added
to your router are picked up automatically with no code or config changes.

The only two variables that matter are `FREELLM_BASE_URL` (where the router
lives) and `FREELLM_API_KEY` (authentication). `LLM_MODEL` is fixed to `auto`;
any other value is rejected at startup.

If the router cannot be reached (connection error, DNS failure, or timeout) the
request is retried up to 2 times with a short backoff, then the error is
reported. Model-related failures are handled entirely by the router — the
application never rotates, skips, or tracks models on its own.

The GUI, console logs, and Excel output report the model the router actually
used (via the response's `model` field), or `Auto (Router Selected)` when it is
not reported.

> No secrets belong in `.env.example` — it ships with a blank API key, which
> puts the application in Offline Mode out of the box.

## Running

### Running the CLI

Run the application and type your search when prompted:

```bash
python app/main.py
```

The banner prints `Lead Generation Agent Ready` followed by
`Please enter your search:`. Type a natural-language request such as
`software companies in Karachi` and press Enter. A successful run ends with a
boxed console summary, and the workbook appears in `outputs/`.

### Running the Desktop GUI

A full desktop application (`app/gui/main.py`) shows the agent running live. It
is a pure presentation layer too: it subscribes to the same
`AgentExecutionLogger` event bus as the terminal renderer, runs the agent on a
worker thread, and renders every event on the main thread — none of the
planning, search, extraction, or export logic lives in the GUI.

```bash
python -m app.gui.main
```

The window provides:

- A **prompt bar** with a Search button (and `Ctrl+Enter`).
- An **Agent Plan** panel — business type, location, provider, maximum results,
  website crawling, export, and the planned tool steps.
- An **Execution Timeline** — the canonical steps (understanding, planning,
  launching the browser, searching, extracting, crawling, exporting, finished)
  highlighted while active, green when done, red when failed, gray when pending.
- **Live Logs** — every execution event streamed with color-coded lines.
- **Statistics** — businesses found/processed, emails, websites, phone numbers,
  and the current runtime.
- A **Current Business** card — the business being processed and the live
  fields being extracted (website / phone / email).
- A **Progress bar** with the per-business counter (`Business 2 / 5`).
- An **Error Handling** card — the failing step, status, reason, retry attempts
  (`Retrying... Attempt 2/3`) and recovery confirmation.
- A **Results** card — success/failure, counts, execution time, the output
  workbook, and **Open Excel / Open Folder / Run Again** buttons.
- **Dark / light themes**, toggled from the header (default from
  `GUI_THEME` in `.env`).

The theme can be preselected with `GUI_THEME=light` in `.env`, and everything
else (browser, provider, limits, LLM mode) is configured exactly as for the CLI.

### Example Search Prompts

Run `python app/main.py`, then type one of these at the `Please enter your
search:` prompt:

```text
coffee shops in Karachi
software companies in Lahore
hospitals in Islamabad
restaurants near Clifton Karachi
real estate agencies in Dubai
digital marketing agencies in London
book stores in New York
plumbers in New York
dentists in Lahore
find 3 coffee shops in Karachi
collect 50 software companies in Lahore
top 10 restaurants in Islamabad
```

**Query format rule:** the prompt must contain one of the words `in`, `near`,
or `around` to separate the business type from the location; otherwise the
parser rejects it with a clear message.

**Result volume rule:** by default a run collects **5** businesses and never
more than **10** unless you explicitly ask for a different number. Include a
count in the prompt ("find 3...", "collect 50...", "top 10...") to control how
many leads are delivered, or raise the global `MAX_LEADS` setting.

## Generated Excel Files

- **Output folder:** `OUTPUT_DIR` (default `outputs/`), created automatically.
- **Filename format:** `leads_<business_type>_<location>.xlsx`
  (e.g. `leads_software_companies_Karachi.xlsx`). Spaces become underscores,
  illegal filename characters are stripped, and a timestamp is appended if the
  file already exists — previous exports are never overwritten.
- **Workbook:** a single `Leads` sheet with a bold, frozen header and
  auto-sized columns.
- **Columns:** Business Name, Email, Phone Number, Website, Location, Provider,
  Search Query, Collected At, Source URL.

## Logging

- **Location:** all records are mirrored to `LOG_DIR/application.log` (default
  `logs/application.log`), rotated at 5 MB with 3 backups.
- **Levels:** `CRITICAL`, `ERROR`, `WARNING`, `INFO` (default), `DEBUG`.
- **Enable DEBUG mode:** set `LOG_LEVEL=DEBUG` in `.env`. Debug records include
  per-step reasoning, selector attempts, consent-dialog checks, and screenshot
  saves.

## Debug Folder

- **Location:** `debug/` (relative to the working directory).
- **Contents:** full-page **screenshots** (`navigation.png`,
  `before_search.png`, `after_search.png`, `results.png`, `before_scroll.png`,
  `after_scroll.png`, `extraction_failure.png`, `selector_failure.png`) and
  **HTML dumps** (`page.html`, `results_failure.html`,
  `selector_failure.html`, `extraction_failure.html`), plus
  `provider_export.json` with the collected references.
- Screenshots and HTML are captured automatically around key browser steps and
  on failures, which is the first place to look when a live search goes wrong.

## Screenshots

> Screenshots are placeholders — add `docs/screenshots/console_summary.png`,
> `docs/screenshots/gui_dashboard.png`, and
> `docs/screenshots/workbook.png` here.

| Console summary | GUI dashboard | Excel workbook |
| --- | --- | --- |
| *placeholder* | *placeholder* | *placeholder* |

## Testing

```bash
pytest                  # run the full suite (483 tests)
ruff check app tests    # lint
black --check app tests # formatting check
pip check               # no broken dependencies
```

See [TESTING.md](TESTING.md) for a manual testing checklist, and
`docs/REQUIREMENT_COMPLIANCE.md` for the 14-requirement compliance matrix.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Executable doesn't exist ...chromium` | Playwright browser not installed | `playwright install chromium` |
| Browser launch fails at startup | Missing OS libraries / browser binary mismatch | `playwright install chromium`; `pip install -U playwright` |
| `ModuleNotFoundError: No module named 'app'` | Running from the wrong directory | Run every command from the project root |
| `SEARCH_PROVIDER must be one of ...` | Invalid provider in `.env` | Use `google` or another supported value |
| `Could not determine a location for prompt` | Prompt has no `in`/`near`/`around` | Use e.g. `"software companies in Karachi"` |
| No leads collected | Provider returned nothing or was blocked | Check `logs/application.log`; raise `TIMEOUT`; retry later |
| Run times out | Page loads slower than `TIMEOUT` | Increase `TIMEOUT`; reduce `MAX_LEADS` |
| Many blank emails/phones | Businesses do not publish them | Expected behavior — stored as empty strings |
| Excel file locked / cannot be saved | Workbook open in Excel / no write access | Close the workbook; check `OUTPUT_DIR` permissions |
| Environment variables not picked up | `.env` missing or misnamed | Copy `.env.example` to `.env` and restart |
| `Agent mode: offline` though I set a key | `ENABLE_LLM` not `true`, or key empty | Set `ENABLE_LLM=true` and paste the key into `FREELLM_API_KEY` |
| Model did not change | Edited a model name somewhere else | The router chooses the model (`LLM_MODEL=auto`); point `FREELLM_BASE_URL` at the router you intend to use, then restart |
| `pip` is not recognized | Environment not active | Activate the virtual environment (see setup) |

The log file `logs/application.log` records every stage with timestamps and
exception traces — it is the first stop for any unexplained behavior.

## Known Limitations

- **Only Google Maps is implemented** — `bing_maps`, `yellow_pages`, and
  `yelp` are registered extension slots that return no results today.
- **Live Google Maps markup** — extraction depends on the current page
  structure; layout changes or CAPTCHAs may require selector updates.
- **Structural email validation only** — emails are matched with a regex, not
  DNS/MX verification, so an address may still bounce.
- **Single-location prompts** — parsing handles one location using
  `in`/`near`/`around`; complex or multi-location prompts are rejected.
- **Serial extraction** — businesses are processed one at a time; no parallel
  scraping.
- **One run = one workbook** — results are not accumulated across runs.

## Future Improvements

- Implement the reserved Bing Maps, Yellow Pages, and Yelp providers (the
  registry slots are already wired up).
- Parallel/async scraping across multiple providers.
- Proxy rotation and CAPTCHA handling for resilient, large-scale scraping.
- CSV / Google Sheets export and CRM integrations.
- AI-powered lead scoring and enrichment (company size, LinkedIn, social links).
- Stronger email verification (DNS/MX checks).
- Web-search-backed planning so the LLM can ground tool selection in live data.

## License

Released under the [MIT License](LICENSE).

## Author

**Lead Generation Agent Team** — built during the AI Season session-4 workshop.
See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and the
[Code of Conduct](CODE_OF_CONDUCT.md).
