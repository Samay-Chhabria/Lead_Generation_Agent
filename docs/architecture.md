# Lead Generation Agent Architecture

Version: 2.0 (current implementation)

---

## 1. Overview

The Lead Generation Agent turns a single natural-language prompt into a clean,
deduplicated Excel lead list. It plans the task, drives a real browser
(Playwright) through a business listing site, extracts contact details, cleans
and deduplicates the data, exports a formatted `.xlsx` workbook, and summarizes
the run.

Example prompt:

    software companies in Karachi

The flow is a real agent loop:

    plan -> select tools -> execute -> recover -> validate -> export -> summarize

---

## 2. Layer Map

The application is layered and every layer is injectable and independently
testable. Nothing above a layer knows how the layer below is implemented.

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
| `app/tools/` | The 13-tool registry: search, navigation, collection, extraction, details, crawl, email, phone, export, pipeline, summary. |
| `app/parser/` | Deterministic prompt-to-`SearchPlan` parsing (used by the pipeline tool). |
| `app/llm/` | Unified LLM gateway (Free LLM Router) plus the offline mock fallback. |
| `app/browser/` | Playwright lifecycle management plus failure recovery. |
| `app/providers/` | Search providers, registry, factory, result collector, result selection. |
| `app/extractor/` | Business detail extraction and website email discovery. |
| `app/processing/` | Normalization, validation, deduplication. |
| `app/exporter/` | Excel workbook construction and output file handling. |
| `app/models/` | `Lead`, `SearchPlan`, `BusinessReference`, `ExecutionResult`, `ExecutionPlan`, `ParsedQuery`. |
| `app/config/` | Environment-driven settings, constants, and logging. |
| `app/utils/` | Helpers, execution summary renderer, retry, timer. |
| `app/exceptions/` | Single exception hierarchy rooted at `LeadGenerationError`. |

---

## 3. Agent -> Planner -> Tools

The console-facing orchestrator is `LeadGenerationAgent`
(`app/agent/lead_generation_agent.py`). It never contains extraction or browser
logic; it only coordinates and presents.

1. The user gives a natural-language task, e.g. "Find dentists near Clifton
   Karachi with emails." — no hand-written query needed.
2. The `Planner` parses the intent (business type, location, wanted data) and
   builds an ordered plan of tool calls, optionally consulting the configured
   LLM for tool selection.
3. The `AgentExecutor` runs each tool (search, details, crawl, extract, export)
   in order, logs its internal reasoning, and folds the results into a final
   `ExecutionResult`.

### Planner

`app/agent/planner.py`

- Produces a `TaskPlan` containing the parsed intent and the ordered tool
  sequence.
- LLM-first when AI Agent Mode is active (the model picks the tool chain);
  deterministic parser fallback always works, so planning never crashes without
  an LLM.
- Always ends the sequence with the `lead_exporter` tool so a run always
  produces a deliverable.
- Rejects prompts that lack a `in`/`near`/`around` location separator with a
  clear `PlanningError`.

### Executor

`app/agent/executor.py`

- Implements the agent loop: for each planned step it reasons, runs the tool
  through the guarded `ToolManager`, and folds the tool result into a running
  `ExecutionResult`.
- Tracks per-tool success/failure in agent memory so later steps can react.
- Defers the final export step until after processing so the workbook contains
  the deduplicated, normalized leads.

### Tool registry

`app/tools/registry.py`

- `ToolRegistry` resolves tools by name and rejects duplicate registration with
  `DuplicateToolError`.
- `build_default_registry()` registers all 13 built-in tools: `GoogleMapsSearchTool`,
  `SearchTool`, `BusinessCollectionTool`, `WebsiteCrawlerTool`, `EmailExtractorTool`,
  `PhoneExtractorTool`, `BusinessDetailsTool`, `BusinessExtractionTool`,
  `NavigationTool`, `ExportTool`, `LeadExporterTool`, `PipelineTool`,
  `SummaryTool`.
- `ExportTool` ("export") is an intentional backward-compatible alias for
  `LeadExporterTool` ("lead_exporter"); the executor's alias map translates it.

---

## 4. Search Providers

`app/providers/`

- `ProviderFactory` builds a search provider from `SEARCH_PROVIDER` and returns
  a `SearchResult` for a parsed query.
- `ProviderRegistry` maps provider names to factory callables; registering the
  same name twice raises.
- `GoogleMapsProvider` is the implemented provider. It drives the shared
  Playwright browser: navigates, searches, scrolls the results feed, collects
  business references, and navigates into each business page for detail
  extraction.
- `BingMapsProvider`, `YellowPagesProvider`, and `YelpProvider` are registered
  extension slots that return no results today; they exist so the modular
  provider contract is demonstrated and future sources drop in without changes
  elsewhere.
- `ResultCollector` aggregates business references; `ResultSelection` ranks and
  trims candidates (by rating, review count, website, verified marker, and
  position) before extraction.

### Result volume rules

- Default: collect **5** businesses.
- The agent's `GoogleMapsSearchTool._resolve_limit` honors an explicit count in
  the prompt and caps the configured default at **10** when no count is given;
  a run never exceeds 10 without an explicit request.
- The pipeline (`resolve_result_limit`) passes the configured `LEAD_MAX_RESULTS`
  through unchanged — the operator's configured volume is treated as intent.

---

## 5. Browser Automation

`app/browser/`

- `BrowserManager` is the facade. It owns the Playwright lifecycle: launch,
  page management, and close.
- `BrowserFactory` builds the Playwright browser instance from settings
  (`BROWSER_TYPE`, `PLAYWRIGHT_HEADLESS`, `PLAYWRIGHT_TIMEOUT`,
  `BROWSER_SLOW_MO`).
- `BrowserSession` and `PageManager` wrap a single page: navigation, waiting for
  load state, closing, and recovery helpers.
- The browser is launched lazily (tools that never need a page never launch it)
  and closed in a `finally` block so it always closes even when a run fails.

---

## 6. Extraction

`app/extractor/`

- `BusinessNavigator` opens each collected business page.
- `BusinessDetailExtractor` extracts the five contact fields (name, email,
  phone, website, location) from the listing page, probing selectors safely;
  missing fields become empty strings, never exceptions.
- `ContactPageCrawler`, `WebsiteNavigator`, and `EmailDiscoveryEngine` enrich
  leads with an email found on the business's own website (homepage, then
  contact/about pages) when the listing has none.

---

## 7. Processing and Export

`app/processing/`

- `LeadNormalizer` normalizes URLs and phone numbers.
- `LeadValidator` validates emails (regex) and phone numbers; invalid records
  are skipped rather than crashing the run.
- `LeadDeduplicator` removes duplicate businesses.
- `ProcessingPipeline` runs normalize -> validate -> deduplicate.

`app/exporter/`

- `WorkbookBuilder` builds a formatted openpyxl workbook (bold frozen header,
  auto-sized columns, `Leads` sheet).
- `FileManager` produces collision-safe filenames
  (`leads_<business_type>_<location>.xlsx`, timestamped when the file exists).
- `ExcelExporter` orchestrates both and returns the output path.

---

## 8. Unified LLM Gateway

The application is model-agnostic: exactly one gateway, Free LLM Router, an
OpenAI-compatible endpoint unlocked by one API key. Every request is sent with
`model="auto"` and the **router** selects the model; the application keeps no
model list and no fallback chain.

- `BaseLLM` (`app/llm/base.py`) — the text-in/text-out interface, plus
  `LLMStatusError`, `LLMNetworkError`, and the `generate()` entry point.
- `FreeLLMRouterProvider` (`app/llm/providers/freellmrouter.py`) — the only
  real client; uses stdlib `urllib` (`app/llm/_http.py`), so no vendor SDK is
  required. It always sends `model="auto"`, extracts the reported model from
  the response `model` field, and retries **only** transient network failures
  (connection/DNS/timeout, up to 2 attempts with a short backoff). HTTP errors
  (e.g. 429) and model-level failures are left to the router to resolve — the
  app never rotates, skips, or tracks models.
- `create_llm_provider` (`app/llm/factory.py`) — the single resolution point:
  - AI Agent Mode -> a `FreeLLMRouterProvider` wired to the execution logger.
  - Offline Mode -> `MockProvider` (deterministic, offline).

Mode selection is automatic:

- `ENABLE_LLM=true` **and** `FREELLM_API_KEY` set -> **AI Agent Mode**.
- `ENABLE_LLM=false` or an empty key -> **Offline Mode** (deterministic parser,
  no network calls, everything else identical).

---

## 9. Configuration

`app/config/settings.py` exposes one immutable `Settings` object built from
environment variables (optionally loaded from `.env`). Everything is validated
at startup (`Settings.validate`) and referenced directories are created
automatically (`Settings.prepare`).

Key variables: `PLAYWRIGHT_HEADLESS`, `PLAYWRIGHT_TIMEOUT`, `BROWSER_TYPE`,
`BROWSER_SLOW_MO`, `LEAD_MAX_RESULTS` (alias `MAX_LEADS`), `SEARCH_PROVIDER`,
`OUTPUT_DIR`, `LOG_DIR`, `LOG_LEVEL`, `ENABLE_LLM`, `FREELLM_API_KEY`,
`FREELLM_BASE_URL`, and `LLM_MODEL` (fixed to `auto`). Legacy aliases
(`HEADLESS`, `TIMEOUT`, `MAX_LEADS`, `LLM_API_KEY`, `LLM_BASE_URL`,
`FREE_LLM_ROUTER_*`) are honored.

---

## 10. Error Handling Strategy

- Navigation is retried once; consent dialogs are dismissed automatically.
- A business that cannot be opened is skipped; the rest are still processed.
- Missing fields become empty strings; invalid records are dropped.
- One failure never aborts a run. Unexpected top-level failures are logged and
  translated into a non-zero exit code by `LeadGenerationApplication`.

---

## 11. Logging

- All records mirror to `logs/application.log` (rotated at 5 MB, 3 backups).
- Console output uses Rich (execution summary, agent status).
- `LOG_LEVEL=DEBUG` enables per-step reasoning, selector attempts, consent
  checks, and screenshot saves.
- Debug artifacts (screenshots and HTML dumps) are written to `debug/` and
  git-ignored.

---

## 12. Testing

- 483 tests: unit, integration, end-to-end, requirement matrix, plus
  performance and recovery tests.
- Layered fakes (`tests/fakes.py`) replace the browser and providers so unit
  tests run without a live browser.
- Linting (ruff), formatting (black), and the full suite run in CI
  (`.github/workflows/python.yml`).

---

## 13. Extensibility

- New search sources: implement `SearchProvider`, register it in
  `ProviderRegistry`, and set `SEARCH_PROVIDER` to its name.
- New tools: implement `Tool` and register it in `build_default_registry`.
- New models: none — the router selects the model via `LLM_MODEL=auto`; new
  router models are used automatically with no code or config changes.
- The desktop GUI (`app/gui/main.py`) is a thin presentation layer; all logic
  lives in the agent.
