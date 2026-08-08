# Requirement Compliance

This document is the authoritative compliance record for the Lead Generation
Agent. It maps each of the 14 assignment requirements to the module(s) that
implement it, explains how it is satisfied, and cites the automated test
evidence. **Status: all 14 requirements PASS** and are verified by the suite.

For the deeper verification strategy, test categories, and the history of bugs
found during verification, see `docs/REQUIREMENT_VERIFICATION.md`.

## Compliance Matrix

| # | Requirement                | Status | Implemented In | Explanation | Evidence |
|---|----------------------------|--------|----------------|-------------|----------|
| R1 | Accepts a natural-language prompt | PASS | `app/parser/prompt_parser.py`, `app/agent/planner.py`, `app/main.py` | The user supplies a prompt interactively (or programmatically via `run(prompt)`); `PromptParser.parse` (and the agent planner) converts it into a `SearchPlan`/`TaskPlan` without any manual field entry. | `tests/test_requirement_matrix.py::test_r1_accepts_natural_language_prompt`, `tests/unit/test_prompt_parser.py`, `tests/test_end_to_end.py` |
| R2 | Business category extracted | PASS | `app/parser/prompt_parser.py`, `app/models/search_plan.py` | The parser splits the prompt into `business_type` and `location` (e.g. "software companies in Karachi" → business type `software companies`, location `Karachi`). | `tests/test_requirement_matrix.py::test_r2_business_category_extracted`, `tests/unit/test_prompt_parser.py` |
| R3 | Browser automation         | PASS | `app/browser/` (`browser_factory.py`, `browser_session.py`, `browser_manager.py`, `page_manager.py`) | A real Playwright browser is launched, navigated, and closed through a lifecycle manager; headless/headed mode and browser engine are configurable. | `tests/test_requirement_matrix.py::test_r3_browser_automation_launches`, `tests/integration/test_browser_manager.py` |
| R4 | Businesses are searched     | PASS | `app/providers/google_maps_provider.py`, `app/providers/result_collector.py` | The provider opens the listing site, submits the derived query, scrolls the results feed, and collects business listings up to `MAX_LEADS`. | `tests/test_requirement_matrix.py::test_r4_businesses_are_searched`, `tests/integration/test_provider_factory.py` |
| R5 | Name/email/phone/website/location collected | PASS | `app/extractor/business_detail_extractor.py`, `app/extractor/contact_page_crawler.py` | Each business page yields a `Lead` with business name, email, phone, website, and location; website emails are additionally discovered by crawling the business site. | `tests/test_requirement_matrix.py::test_r5_contact_fields_collected`, `tests/unit/test_business_extraction.py`, `tests/unit/test_email_discovery.py` |
| R6 | Multiple businesses collected | PASS | `app/providers/result_collector.py`, `app/config/settings.py` | Collection is driven by `MAX_LEADS` (configurable, e.g. 10/25/50/100) and continues scrolling until the limit or the end of results. | `tests/test_requirement_matrix.py::test_r6_multiple_businesses_collected`, `tests/unit/test_result_collection.py` |
| R7 | Missing fields handled      | PASS | `app/extractor/business_detail_extractor.py`, `app/processing/` (`lead_normalizer.py`, `lead_validator.py`, `lead_deduplicator.py`, `processing_pipeline.py`) | Missing values become empty strings and are stored as blank cells; leads that fail validation are skipped while the rest continue; one failed business/website never aborts the run. | `tests/test_requirement_matrix.py::test_r7_missing_fields_handled`, `tests/unit/test_processing_pipeline.py`, `tests/test_end_to_end.py::test_full_run_survives_website_failures`, `tests/requirement_tests/test_robustness.py` |
| R8 | Excel workbook generated    | PASS | `app/exporter/` (`excel_exporter.py`, `workbook_builder.py`, `file_manager.py`) | Processed leads are written with openpyxl to a `.xlsx` workbook containing a `Leads` sheet. | `tests/test_requirement_matrix.py::test_r8_excel_workbook_generated`, `tests/unit/test_excel_export.py` |
| R9 | Required columns exist      | PASS | `app/exporter/workbook_builder.py` | The `Leads` sheet header contains Business Name, Email, Phone Number, Website, Location, Provider, Search Query, Collected At, and Source URL. | `tests/test_requirement_matrix.py::test_r9_required_columns_exist`, `tests/unit/test_excel_export.py` |
| R10 | Meaningful filename         | PASS | `app/exporter/file_manager.py` | Filenames follow `leads_<business_type>_<location>.xlsx`, are filesystem-safe, and never overwrite previous exports (timestamp suffix). | `tests/test_requirement_matrix.py::test_r10_output_filename_is_meaningful`, `tests/unit/test_excel_export.py`, `tests/requirement_tests/test_robustness.py` |
| R11 | Execution summary printed   | PASS | `app/utils/execution_summary.py`, `app/pipeline/application_pipeline.py` | Every run ends with a boxed console summary showing the query, counts, output file, and elapsed time. | `tests/test_requirement_matrix.py::test_r11_execution_summary_printed`, `tests/test_end_to_end.py`, `tests/test_cli.py` |
| R12 | Runs without runtime errors | PASS | `app/pipeline/application_pipeline.py`, `app/application/application.py`, `app/exceptions/` | All failures (invalid prompt, provider outage, browser crash, export failure) are contained and produce a non-successful result or continue the run; CLI exit codes are 0/1. | `tests/test_requirement_matrix.py::test_r12_runs_without_runtime_errors`, `tests/test_cli.py`, `tests/end_to_end/test_failure_paths.py` |
| R13 | README instructions verified | PASS | `README.md`, `.env.example` | The README documents installation, setup, running, examples, folder structure, troubleshooting, output, and testing; `.env.example` lists every configuration variable. | `tests/test_requirement_matrix.py::test_r13_readme_instructions_verified` |
| R14 | Repository structure verified | PASS | Repository layout | Submission excludes `node_modules`, `venv`, `__pycache__`, Playwright browsers, and generated Excel files; it includes README, `requirements.txt`, `.env.example`, `.gitignore`, and source. | `tests/test_requirement_matrix.py::test_r14_repository_structure_verified` |

## Autonomous Agent Enhancement Checklist

Beyond the 14 assignment requirements, the application was extended into a real
autonomous agent. Each enhancement is implemented, exercised by the suite, and
verified by the checklist below.

| Objective | Status | Evidence | Files Modified |
|-----------|--------|----------|----------------|
| Plan the task before executing | PASS | Planner produces a `TaskPlan`; GUI shows the plan before a run | `app/agent/planner.py`, `app/agent/lead_generation_agent.py`, `app/models/execution_plan.py` |
| Select tools automatically (LLM-first, parser fallback) | PASS | `_plan_from_llm` + deterministic fallback; mock/offline always work | `app/agent/planner.py`, `app/llm/`, `tests/test_planner.py` |
| Execute steps through a tool manager | PASS | `ToolManager.execute` guards every call; unknown/raising tools return failed results | `app/agent/tool_manager.py`, `tests/test_agent_tools.py` |
| Recover from failures | PASS | Navigation retry + consent dismissal; listing-open retry; per-business skip | `app/browser/page_manager.py`, `app/extractor/business_navigator.py`, `app/tools/business_details_tool.py`, `tests/unit/test_recovery.py` |
| Validate and process collected leads | PASS | Rating filter, normalization, validation, deduplication | `app/agent/executor.py`, `app/processing/` |
| Export the deliverable | PASS | Excel workbook written via the exporter or the pipeline tool | `app/tools/export_tool.py`, `app/tools/pipeline_tool.py`, `app/exporter/` |
| Summarize the run | PASS | `SummaryTool` fills `ExecutionResult.summary`; shown by CLI + GUI | `app/tools/summary_tool.py`, `app/agent/executor.py`, `app/gui/main.py` |
| Keep all existing functionality green | PASS | 483 tests pass; CLI and GUI entry points unchanged | `app/`, `tests/` |

### How to Re-verify

```bash
# 1. Run the requirement matrix (R1-R14) in isolation
pytest tests/test_requirement_matrix.py -v

# 2. Run the entire suite
pytest

# 3. Lint and formatting
ruff check app tests
black --check app tests
```

## Status Summary

- **14 / 14 requirements PASS.**
- Every requirement is verified by at least one automated test that exercises
  the real implementing component.
- The full test suite runs without network or live-browser access except for
  the browser-automation tests and the Requirement 3 check, which launch real
  Chromium.
