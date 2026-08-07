# Run Guide

A beginner-friendly walkthrough for setting up and running the **Lead Generation
Agent**. The agent reads a natural-language request ("software companies in
Karachi"), plans the work, launches a Playwright browser, searches a business
listing site, extracts leads, and exports an Excel workbook.

There are two ways to use it:

- **Desktop GUI** (`python -m app.gui.main`) — a window with live timeline, logs,
  statistics, and results.
- **Interactive CLI** (`python app/main.py`) — type your request at the prompt in
  the terminal.

---

## 1. Prerequisites

- **Python 3.12+** (the project is developed on 3.14; see `.python-version`).
- **Git** (to clone the repository).
- **Node.js** is *not* required — Playwright is installed as a Python wheel and
  downloads its own Chromium build.

---

## 2. Get the Code and Create a Virtual Environment

```bash
git clone <your-repository-url>
cd Lead_generation_agent

python -m venv .venv
```

Activate it:

- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```bat
  .venv\Scripts\activate.bat
  ```
- **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs the runtime dependencies:

- `playwright` — browser automation
- `PySide6` — the desktop GUI
- `openpyxl` — Excel (.xlsx) export
- `python-dotenv` — reads `.env`
- `rich` — console summary and colored logging

The LLM gateway uses only the Python standard library; no OpenAI/per-vendor SDK
is needed.

---

## 4. Install the Playwright Browser

```bash
playwright install chromium
```

If you prefer, also install the system dependencies (mainly needed on Linux):

```bash
playwright install-deps chromium
```

> Playwright browsers are stored outside the project and are git-ignored, so
> they never end up in a submission.

---

## 5. Configure `.env`

Copy the template and edit it:

```bash
cp .env.example .env
```

Open `.env` and set at least:

```dotenv
# Required for AI planning. Leave blank to run in Offline Mode
# (deterministic planning, no LLM calls).
FREELLM_API_KEY=<your-freellm-api-key>

# The FreeLLM Router endpoint you are running (default below).
FREELLM_BASE_URL=http://localhost:3001/v1

# Must stay "auto" — the router picks the model server-side.
LLM_MODEL=auto
```

The most useful knobs:

| Setting | Default | Meaning |
| --- | --- | --- |
| `ENABLE_LLM` | `true` | `true` = AI Agent Mode (needs a key), `false` = Offline Mode |
| `LEAD_MAX_RESULTS` | `5` | Businesses to collect per run (see volume rule below) |
| `PLAYWRIGHT_HEADLESS` | `false` | Run the browser in the background (`true`) or visible (`false`) |
| `BROWSER_SLOW_MO` | `300` | Artificial delay (ms) between browser actions |
| `GUI_THEME` | `dark` | Desktop GUI theme: `dark` or `light` |
| `OUTPUT_DIR` | `outputs` | Where Excel workbooks are written |
| `LOG_DIR` | `logs` | Where rotating logs are written |
| `LOG_LEVEL` | `INFO` | Log verbosity |

> `.env` is git-ignored and never committed. `.env.example` ships with a blank
> key, so a fresh clone runs in Offline Mode out of the box.

---

## 6. Start the FreeLLM API (AI Mode Only)

In **AI Agent Mode** the application plans with the **FreeLLM Router** — a single
OpenAI-compatible endpoint. Point `FREELLM_BASE_URL` at your running router
instance (default `http://localhost:3001/v1`), set `FREELLM_API_KEY`, and make
sure the router is reachable before starting the app.

If you do **not** start a router, leave the key blank or set `ENABLE_LLM=false`:
the agent falls back to the deterministic parser and everything else (browser,
search, extraction, Excel export) keeps working offline.

---

## 7. Run the Desktop GUI

```bash
python -m app.gui.main
```

The window opens. Type a request in the prompt bar (e.g. `plumbers in New York`)
and press **Search** (or `Ctrl+Enter`).

You will see, live:

- **Agent Plan** — what the agent decided to do (business type, location,
  provider, limits, planned tool steps).
- **Execution Timeline** — current step highlighted, finished steps green,
  failed steps red.
- **Live Logs** — color-coded execution events.
- **Statistics** — businesses found/processed, emails, websites, phones, runtime.
- **Progress bar** — `Business 2 / 5`-style counter.
- **Error Handling card** — if a step fails, with retry attempts.
- **Results card** — counts, execution time, output workbook, and
  **Open Excel / Open Folder / Run Again** buttons.

Switch themes with the **Dark / Light** toggle in the header.

---

## 8. Run the Interactive CLI

```bash
python app/main.py
```

You will see:

```text
Lead Generation Agent Ready
Please enter your search:
```

Type a request and press Enter, for example:

```text
Please enter your search: software companies in Karachi
```

A successful run prints a boxed summary and writes the workbook to `outputs/`.

---

## 9. Example Queries

The request must contain `in`, `near`, or `around` to separate the business type
from the location:

```text
coffee shops in Karachi
dentists in Lahore
plumbers in New York
software companies in Dubai
hospitals in Islamabad
restaurants near Clifton Karachi
find 3 coffee shops in Karachi
collect 50 software companies in Lahore
top 10 restaurants in Islamabad
```

**Result volume rule:** a run collects **5** businesses by default and never more
than **10** unless you ask for a different count in the prompt ("find 3...",
"collect 50...", "top 10...") or raise `LEAD_MAX_RESULTS` in `.env`.

---

## 10. Where the Excel Files Appear

- **Folder:** `OUTPUT_DIR` (default `outputs/`), created automatically on first
  run.
- **Filename:** `leads_<business_type>_<location>.xlsx`
  (e.g. `leads_software_companies_Karachi.xlsx`). Spaces become underscores,
  illegal characters are stripped, and a timestamp is appended if the name is
  already taken.
- Each workbook has a `Leads` sheet with the columns **Business Name, Email,
  Phone Number, Website, Location, Search Query, Date Collected**.
- Missing fields are stored as empty strings — a business without a website or
  email never breaks the run.

Other artifacts:

- `logs/` — rotating application logs (set `LOG_LEVEL=DEBUG` for more detail).
- `debug/` — screenshots and HTML dumps on failure, useful when reporting bugs.

---

## 11. Common Issues

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Executable doesn't exist ... run playwright install` | Chromium not downloaded | Run `playwright install chromium` |
| Planning falls back to Offline Mode | No `FREELLM_API_KEY` / router not running | Start the FreeLLM Router or set the key; or leave it and stay offline |
| Browser window appears but nothing happens | CAPTCHA or consent dialog on the listing site | Set `PLAYWRIGHT_HEADLESS=false`, watch the browser; recovery retries automatically |
| Empty `outputs/` after a run | Provider returned no results or extraction failed | Check `logs/` and set `LOG_LEVEL=DEBUG` |
| GUI won't open | `PySide6` not installed | `pip install -r requirements.txt` (or `pip install PySide6`) |
| Prompt rejected ("no location") | Missing `in`/`near`/`around` | Rewrite as e.g. "software companies in Karachi" |
| Workbook filename collision | An older export has the same name | A timestamp is appended automatically; no file is overwritten |

---

## 12. Debugging

- **More logging:** set `LOG_LEVEL=DEBUG` in `.env` and re-run; the app keeps
  `logs/` up to date and prints colored lines in the terminal.
- **Visible browser:** set `PLAYWRIGHT_HEADLESS=false` to watch every step.
- **Slow motion:** raise `BROWSER_SLOW_MO` (e.g. `1500`) to slow the automation
  down and follow what it is doing.
- **Keep outputs:** use a separate `OUTPUT_DIR` per experiment
  (e.g. `OUTPUT_DIR=outputs_test`) so exports never collide.
- **Failed runs:** screenshots and HTML dumps are written to `debug/` so you can
  inspect what the browser saw.

---

## 13. Verification Checklist

```bash
python app/main.py              # interactive CLI
python -m app.gui.main          # desktop GUI
pytest                          # 483 tests pass
ruff check app tests            # no lint findings
black --check app tests         # formatting clean
```
