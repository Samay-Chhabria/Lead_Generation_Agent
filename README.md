# Lead Generation Agent

An AI-powered agent that accepts a natural-language prompt (such as
*"software companies in Karachi"*), searches business listing websites with
browser automation, extracts business leads (name, email, phone, website,
location), and exports them to a formatted Excel workbook. All 14 assignment
requirements are implemented and covered by an automated test suite.

---

## How It Works

Given a prompt, the application:

1. **Parses** the prompt into a structured search plan (business type +
   location) using the `PromptParser`.
2. **Searches** the configured provider (default: Google Maps) through
   Playwright browser automation and collects business listings.
3. **Extracts** each business's name, email, phone number, website, and
   location, including crawling the company website to discover an email.
4. **Processes** the raw leads: normalizing values, validating records, and
   removing duplicates.
5. **Exports** the final leads to an `.xlsx` workbook with a meaningful
   filename (`leads_<business_type>_<location>.xlsx`) in the output directory.
6. **Summarizes** the run with a console summary showing counts, the output
   file, and execution time.

A failure at any stage (unavailable website, provider outage, write-protected
output directory) is contained: already-collected data is never lost and the
application never crashes with a runtime error.

---

## Architecture Overview

The application follows a layered, single-responsibility design:

```
main.py → LeadGenerationApplication → LeadGenerationAgent
                                          │
             ┌──────────┬────────────┬────┴─────┬──────────┬──────────┐
             ▼          ▼            ▼          ▼          ▼          ▼
        Prompt      Browser       Provider    Extractor  Processing Exporter
        Parser      Manager      (search)    (leads)    (pipeline)  (Excel)
             └──────────────────────────────┬───────────┘
                                            ▼
                                        Summary
```

- **`main.py`** — entry point only; creates the application and runs it.
- **`LeadGenerationApplication`** — loads configuration, initializes logging,
  prepares directories, starts the agent, and shuts down cleanly.
- **`LeadGenerationAgent`** — console-facing orchestrator that reads the prompt
  and runs the full workflow.
- **`app/parser`** — converts natural-language prompts into `SearchPlan`s.
- **`app/browser`** — Playwright lifecycle management (launch, navigate, close).
- **`app/providers`** — search providers and the result collector.
- **`app/extractor`** — business detail and website email extraction.
- **`app/processing`** — lead normalization, validation, and deduplication.
- **`app/exporter`** — Excel workbook construction and output file management.
- **`app/models`** — `Lead`, `SearchPlan`, `ExecutionResult`, and related types.
- **`app/config`** — environment-driven settings, constants, and logging.

Everything is configured through environment variables (`.env`) so no values
are hardcoded, and logging writes to both the console and a rotating file.

---

## Folder Structure

```
lead-generation-agent/
├── app/
│   ├── main.py                    # Application entry point
│   ├── application/               # Application lifecycle orchestration
│   ├── agent/                     # Console-facing agent facade
│   ├── parser/                    # Natural-language prompt parsing
│   ├── browser/                   # Playwright lifecycle
│   ├── providers/                 # Search providers and result collection
│   ├── extractor/                 # Business and email extraction
│   ├── processing/                # Normalization, validation, deduplication
│   ├── exporter/                  # Excel (.xlsx) export
│   ├── models/                    # Lead, SearchPlan, ExecutionResult
│   ├── config/                    # settings, constants, logging
│   ├── utils/                     # helpers, execution summary
│   └── exceptions/                # custom exception hierarchy
├── tests/                         # pytest test suite (unit, integration,
│                                  # end-to-end, requirement, performance)
├── docs/                          # architecture and planning docs
├── outputs/                       # generated Excel files
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

Install the Playwright browser used for automation:

```bash
playwright install chromium
```

Optional development tooling (Black, Ruff, pytest):

```bash
pip install -e ".[dev]"
```

---

## Setup

Copy the environment template and adjust values if needed:

```bash
cp .env.example .env
```

| Variable          | Description                          | Default    |
| ----------------- | ------------------------------------ | ---------- |
| `HEADLESS`        | Run the browser headless             | `true`     |
| `TIMEOUT`         | Default timeout in milliseconds      | `30000`    |
| `MAX_LEADS`       | Maximum leads to collect             | `25`       |
| `SEARCH_PROVIDER` | Default search provider              | `google`   |
| `BROWSER_TYPE`    | Browser engine (`chromium`, `firefox`, `webkit`) | `chromium` |
| `OUTPUT_DIR`      | Directory for generated files        | `outputs`  |
| `LOG_DIR`         | Directory for log files              | `logs`     |
| `LOG_LEVEL`       | Logging verbosity                    | `INFO`     |

Supported `SEARCH_PROVIDER` values: `google`, `google_maps`, `bing_maps`,
`yellow_pages`, `yelp`.

Configuration is validated on startup. Invalid values — a non-positive
`TIMEOUT`/`MAX_LEADS`, an unsupported `SEARCH_PROVIDER`, or an unknown
`LOG_LEVEL` — abort the application with a clear error message. Output and log
directories are created automatically if they do not exist.

---

## Running

Pass a prompt as a command-line argument:

```bash
python app/main.py "software companies in Karachi"
```

Without an argument, the application prompts for the search interactively:

```bash
python app/main.py
```

Expected output:

```
INFO  Application starting...
INFO  Loading configuration...
INFO  Logging initialized.
Lead Generation Agent v0.1.0 is ready to use.

Search Plan
========================================
Original Prompt: software companies in Karachi
Business Type: software companies
Location: Karachi
Provider: google
Maximum Leads: 25

========================================
Lead Generation Completed Successfully
========================================
Search Query: software companies in Karachi
Business Type: software companies
Location: Karachi
Provider: Google
Businesses Found: 8
Documents Removed: 1
Leads Exported: 7
Output File: C:\...\outputs\leads_software_companies_Karachi.xlsx
Execution Time: 12.3 seconds
========================================
INFO  Application shutting down...
```

The generated workbook opens in Excel with a `Leads` sheet containing the
columns Business Name, Email, Phone Number, Website, Location, Provider,
Search Query, Collected At, and Source URL. Logs are written to
`logs/application.log` (rotated at 5 MB).

---

## Testing & Quality

```bash
pytest                 # run the full test suite
ruff check app tests   # lint
black --check app tests  # formatting check
```

The test suite is organized into unit, integration, end-to-end, requirement,
and performance suites. End-to-end tests inject a fake provider so they never
touch the network or launch a real browser; only the browser-automation tests
and the requirement matrix's Requirement 3 check launch real Chromium. See
`docs/REQUIREMENT_VERIFICATION.md` for the requirement-by-requirement
verification matrix.
