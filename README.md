# Lead Generation Agent

An AI-powered agent that will eventually accept a natural-language prompt
(such as *"coffee shops in America"*), search business listing websites with
browser automation, extract business leads, and export them to an Excel
workbook.

> **Status: Milestone 1 — Project Foundation (hardened).**
> This repository currently contains the application skeleton: validated
> configuration, a reusable logging system, data models, and utilities. Lead
> generation features are **not** implemented yet. See
> [Future milestones](#future-milestones).

---

## Architecture Overview

The application follows a layered, single-responsibility design:

```
main.py → LeadGenerationApplication → LeadGenerationAgent
                                          │
                ┌──────────┬──────────────┼──────────────┬─────────────┐
                ▼          ▼              ▼              ▼             ▼
           Prompt      Browser      Providers      Extractor     Exporter
           Parser      Manager      (search)       (leads)      (Excel)
                └──────────┬──────────────┘
                           ▼
                     Validator
```

- **`main.py`** — entry point only; creates the application and runs it.
- **`LeadGenerationApplication`** — loads configuration, initializes logging,
  prepares directories, starts the agent, and shuts down cleanly.
- **`LeadGenerationAgent`** — future orchestrator of the full pipeline.
- **Modules under `app/`** (parser, browser, providers, extractor, validator,
  exporter) are scaffolds that will be filled in by later milestones.

Everything is configured through environment variables (`.env`) so no values
are hardcoded, and logging writes to both the console and a rotating file.

---

## Folder Structure

```
lead-generation-agent/
├── app/
│   ├── main.py                    # Application entry point
│   ├── application/
│   │   └── application.py         # Lifecycle orchestration
│   ├── agent/
│   │   └── lead_generation_agent.py
│   ├── parser/                    # Prompt parsing (Milestone 2)
│   ├── browser/                   # Playwright lifecycle (Milestone 3)
│   ├── providers/                 # Search providers (Milestone 4)
│   ├── extractor/                 # Lead extraction (Milestone 5)
│   ├── validator/                 # Lead validation (Milestone 6)
│   ├── exporter/                  # Excel export (Milestone 7)
│   ├── models/                    # Lead, ParsedQuery, SearchPlan
│   ├── config/                    # settings, constants, logging
│   ├── utils/                     # timer, retry, helpers
│   └── exceptions/                # custom exception hierarchy
├── tests/                         # pytest test suite
├── docs/                          # architecture and planning docs
├── outputs/                       # generated Excel files (future)
├── logs/                          # application log files
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

Requires **Python 3.12 or newer**.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Optional development tooling (Black, Ruff, pytest):

```bash
pip install -e ".[dev]"
```

> Playwright is listed as a dependency for future milestones but browsers are
> **not** needed yet; do not run `playwright install` until Milestone 3.

---

## Setup

Copy the environment template and adjust values if needed:

```bash
cp .env.example .env
```

| Variable         | Description                          | Default   |
| ---------------- | ------------------------------------ | --------- |
| `HEADLESS`       | Run the browser headless (future)    | `true`    |
| `TIMEOUT`        | Default timeout in milliseconds      | `30000`   |
| `MAX_LEADS`      | Maximum leads to collect (future)    | `25`      |
| `SEARCH_PROVIDER`| Default search provider (future)     | `google`  |
| `OUTPUT_DIR`     | Directory for generated files        | `outputs` |
| `LOG_DIR`        | Directory for log files              | `logs`    |
| `LOG_LEVEL`      | Logging verbosity                    | `INFO`    |

Supported `SEARCH_PROVIDER` values: `google`, `google_maps`, `bing_maps`,
`yellow_pages`, `yelp`.

Configuration is validated on startup. Invalid values — a non-positive
`TIMEOUT`/`MAX_LEADS`, an unsupported `SEARCH_PROVIDER`, or an unknown
`LOG_LEVEL` — abort the application with a clear error message. Output and log
directories are created automatically if they do not exist.

---

## Running

```bash
python app/main.py
```

Expected output:

```
INFO  Application starting...
INFO  Loading configuration...
INFO  Logging initialized.
INFO  Lead Generation Agent Ready.
Lead Generation Agent v0.1.0 is ready to use.
INFO  Application shutting down...
```

Logs are also written to `logs/application.log` (rotated at 5 MB).

---

## Testing & Quality

```bash
pytest                 # run the test suite
ruff check .           # lint
black --check .        # formatting check
```

---

## Future Milestones

| Milestone | Feature                                   |
| --------- | ----------------------------------------- |
| 2         | Prompt parser (business type + location)  |
| 3         | Playwright browser automation             |
| 4         | Search providers and result collection    |
| 5         | Lead extraction (name, email, phone, ...) |
| 6         | Lead validation and deduplication         |
| 7         | Excel (.xlsx) export                      |
| 8+        | Execution summary, integration, docs      |
