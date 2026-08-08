# Requirement Verification

This document maps each of the 14 assignment requirements to the automated
tests that verify it and describes the testing strategy used across the
repository. Every requirement below is verified by at least one passing test in
the suite.

## Requirement Matrix

| # | Requirement                        | Verification method                                            | Test reference(s)                                            | Status |
|---|------------------------------------|----------------------------------------------------------------|--------------------------------------------------------------|--------|
| R1 | Accepts a natural-language prompt  | `PromptParser` parses a prompt into a `SearchPlan`; full run completes | `tests/test_requirement_matrix.py::test_r1_accepts_natural_language_prompt`, `tests/test_end_to_end.py` | PASS |
| R2 | Business category extracted        | Parser returns business type and location for sample prompts    | `tests/test_requirement_matrix.py::test_r2_business_category_extracted`, `tests/unit/test_prompt_parser.py` | PASS |
| R3 | Browser automation launches        | Real `BrowserManager` launches Chromium, navigates, and closes  | `tests/test_requirement_matrix.py::test_r3_browser_automation_launches`, `tests/integration/test_browser_manager.py` | PASS |
| R4 | Businesses are searched            | Provider lifecycle collects business listings                   | `tests/test_requirement_matrix.py::test_r4_businesses_are_searched`, `tests/integration/test_provider_factory.py` | PASS |
| R5 | Name/email/phone/website/location  | Leads carry all five fields and appear in the exported workbook | `tests/test_requirement_matrix.py::test_r5_contact_fields_collected` | PASS |
| R6 | Multiple businesses collected      | Runs with several leads produce several workbook rows           | `tests/test_requirement_matrix.py::test_r6_multiple_businesses_collected` | PASS |
| R7 | Missing fields handled             | Runs with sparse leads succeed and write blank cells           | `tests/test_requirement_matrix.py::test_r7_missing_fields_handled`, `tests/unit/test_processing_pipeline.py`, `tests/test_end_to_end.py::test_full_run_survives_website_failures` | PASS |
| R8 | Excel workbook generated           | Exported `.xlsx` exists and opens with a `Leads` sheet          | `tests/test_requirement_matrix.py::test_r8_excel_workbook_generated`, `tests/unit/test_excel_export.py` | PASS |
| R9 | Required columns exist             | Header row matches the required `COLUMN_HEADERS`                | `tests/test_requirement_matrix.py::test_r9_required_columns_exist`, `tests/test_end_to_end.py` | PASS |
| R10 | Meaningful filename               | Filename is `leads_<business_type>_<location>.xlsx`, sanitized  | `tests/test_requirement_matrix.py::test_r10_output_filename_is_meaningful`, `tests/unit/test_excel_export.py`, `tests/requirement_tests/test_robustness.py` | PASS |
| R11 | Execution summary printed          | Console output contains the success summary with counts         | `tests/test_requirement_matrix.py::test_r11_execution_summary_printed`, `tests/test_end_to_end.py`, `tests/test_cli.py` | PASS |
| R12 | Runs without runtime errors        | Successful and empty runs return `success`; CLI exit codes are 0/1 | `tests/test_requirement_matrix.py::test_r12_runs_without_runtime_errors`, `tests/test_cli.py`, `tests/end_to_end/test_failure_paths.py` | PASS |
| R13 | README instructions verified       | README documents install/setup/run; `.env.example` lists all vars | `tests/test_requirement_matrix.py::test_r13_readme_instructions_verified` | PASS |
| R14 | Repository structure verified      | Expected directories and files exist                            | `tests/test_requirement_matrix.py::test_r14_repository_structure_verified` | PASS |

Run the matrix in isolation with:

```bash
pytest tests/test_requirement_matrix.py -v
```

## Test Categories

| Category            | Location                              | Purpose                                                                 |
|---------------------|---------------------------------------|-------------------------------------------------------------------------|
| Unit                | `tests/unit/`                         | Parser, models, normalizer, validator, deduplicator, exporter, utils, settings, exceptions, extraction, collection, processing — pure components, fakes only |
| Integration         | `tests/integration/`                  | Provider lifecycle, `SearchPipeline`, `ApplicationPipeline`, browser manager — real browser only in browser tests |
| End-to-end          | `tests/test_end_to_end.py`, `tests/end_to_end/` | Complete user workflow via a fake provider: workbook, summary, browser cleanup, logs, failure paths |
| Requirement         | `tests/test_requirement_matrix.py`, `tests/requirement_tests/` | R1–R14 verification and application-level robustness |
| CLI                | `tests/test_cli.py`                   | Argument forwarding and real-process exit codes |
| Performance         | `tests/unit/test_performance.py`      | Lead-volume timing budgets, repeated runs, resource cleanup |

Shared fixtures and fakes live in `tests/conftest.py` and `tests/fakes.py`.

## Verification Strategy

1. **Requirement tests** assert each requirement against the real component
   that implements it, so a regression in any single module fails the matrix.
2. **Unit tests** verify individual components in isolation with deterministic
   fakes (no network, no browser), covering edge cases such as malformed input,
   timeouts, and missing data.
3. **Integration tests** exercise the seams between modules: prompt → plan →
   provider → collector → extractor → processing → export.
4. **End-to-end tests** run the full application workflow with a fake provider
   and assert the observable outcomes (workbook on disk, summary printed,
   browser released, logs written).
5. **Failure tests** confirm every realistic failure — no internet, provider
   outage, website unavailable, timeout, invalid or empty prompt, permission
   denied on export, browser crash, unexpected exception — is contained and
   either produces an unsuccessful result or continues the run.
6. **Performance tests** keep processing and full runs within generous time
   budgets at 50 and 100 leads and verify repeated runs close the browser and
   do not leak state between runs.
7. **Logging verification** asserts lifecycle and error records are written to
   the configured rotating log file, not only the console.

## Bugs Discovered and Fixed

- **Unexpected exceptions escaped the application pipeline.** `ApplicationPipeline`
  only caught provider/export exceptions, so an unexpected exception (e.g. a raw
  browser crash) propagated and aborted the run instead of producing an
  unsuccessful `ExecutionResult`. The pipeline now contains any exception,
  logs it, and returns a non-successful result while still releasing the
  browser. Verified by
  `tests/end_to_end/test_failure_paths.py::test_unexpected_exception_returns_unsuccessful_instead_of_crashing`
  and `tests/requirement_tests/test_robustness.py::test_failed_run_writes_error_to_configured_log_file`.

## Running the Suite

```bash
pytest                        # full suite (unit + integration + E2E + requirements + performance)
ruff check app tests          # lint
black --check app tests       # formatting check
```
