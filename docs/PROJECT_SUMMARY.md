# Project Summary

## Overview

The **Lead Generation Agent** is an AI-powered application that converts a
natural-language business search request into a structured Excel lead list.
A user types something like *"software companies in Karachi"*, and the agent
automatically:

1. parses the request into a business type and location,
2. launches a real browser through Playwright,
3. searches business listing websites (Google Maps implemented out of the box),
4. visits each business listing and extracts the name, email, phone number,
   website, and location,
5. crawls each business's own website to discover an email when the listing
   has none,
6. normalizes, validates, and deduplicates the collected leads,
7. exports the final list to a formatted `.xlsx` workbook with a meaningful
   filename, and
8. prints a console summary of the run.

## Problem Solved

Manually researching and compiling a lead list is slow and error-prone. This
agent replaces that manual effort with a repeatable, configurable pipeline:
given only a prompt, it produces a clean, deduplicated Excel file of
businesses with their contact details — handling missing data, unavailable
websites, provider outages, and export failures without crashing.

## Key Features

- **Natural-language input** with deterministic, dependency-free parsing.
- **Real browser automation** (Playwright/Chromium) — no API keys required.
- **Modular provider architecture** with Google Maps implemented and
  Bing Maps / Yellow Pages / Yelp reserved as swappable slots.
- **Five contact fields** per business plus **website email enrichment**
  (homepage → contact/about page crawl).
- **Configurable lead volume** (`MAX_LEADS`).
- **Robust processing**: normalization, validation, and deduplication with
  graceful handling of missing or malformed data.
- **Professional Excel export**: formatted `Leads` sheet, frozen header,
  auto-sized columns, collision-safe meaningful filenames.
- **Execution summary** and **rotating file + console logging**.
- **Full test coverage**: 303 tests across unit, integration, end-to-end,
  requirement, and performance suites.

## Architecture

Layered, single-responsibility design with injectable, independently testable
components:

| Layer            | Module(s)                                          | Responsibility                              |
|------------------|----------------------------------------------------|---------------------------------------------|
| Entry point      | `app/main.py`                                      | Bootstrap and prompt forwarding             |
| Application      | `app/application/`                                 | Lifecycle, config loading, logging, exit code |
| Agent            | `app/agent/`                                       | Console facade, prompt collection           |
| Pipeline         | `app/pipeline/`                                    | Orchestration: parse → search → process → export → summarize |
| Parser           | `app/parser/`                                      | Prompt → `SearchPlan`                       |
| Browser          | `app/browser/`                                     | Playwright factory/session/manager/page     |
| Providers        | `app/providers/`                                   | Search providers, registry, factory, result collector |
| Extractor        | `app/extractor/`                                   | Business detail extraction, website email discovery |
| Processing       | `app/processing/`                                  | Normalize → validate → deduplicate          |
| Exporter         | `app/exporter/`                                    | Workbook construction, filename/output management |
| Models           | `app/models/`                                      | `Lead`, `SearchPlan`, `BusinessReference`, `ExecutionResult`, … |
| Config           | `app/config/`                                      | Settings, constants, logging configuration  |
| Utils            | `app/utils/`                                       | Helpers, execution summary, retry/timer     |
| Exceptions       | `app/exceptions/`                                  | Single hierarchy rooted at `LeadGenerationError` |

## Tech Stack

- **Python 3.12+**
- **Playwright** — browser automation
- **openpyxl** — Excel workbook generation
- **python-dotenv** — environment configuration
- **Rich** — console output (summary, colored logging)
- **pytest** — test framework
- **Ruff** / **Black** — linting and formatting

## Development History

| Milestone | Commit | Scope |
|-----------|--------|-------|
| Initial scaffold | `05d5f73` | Project structure, settings, parser, browser, providers, models |
| Data processing | `4f38052` | Normalization, validation, deduplication (Requirement 7) |
| Excel export | `d9f7766` | Workbook builder, filename management (Requirements 8/9/10) |
| End-to-end pipeline | `a68bfd0` | Search pipeline, application pipeline, summary (Requirements 1/11/12) |
| Comprehensive testing | `f0b6c04` | Requirement matrix, failure-path and robustness suites, all 14 requirements verified |
| Production readiness | *this milestone* | Repository cleanup, professional README, compliance/summary/checklist docs |

## Test Suite

- **Unit** (`tests/unit/`) — pure components in isolation with deterministic
  fakes (parser, models, processing, exporter, browser, providers, extractor).
- **Integration** (`tests/integration/`) — seams between modules: provider
  lifecycle, pipelines, browser manager (real Chromium only in browser tests).
- **End-to-end** (`tests/test_end_to_end.py`, `tests/end_to_end/`) — full user
  workflow via a fake provider plus failure-path coverage.
- **Requirement** (`tests/test_requirement_matrix.py`,
  `tests/requirement_tests/`) — the 14-requirement matrix and app-level
  robustness.
- **CLI** (`tests/test_cli.py`) — argument forwarding and process exit codes.
- **Performance** (`tests/unit/test_performance.py`) — timing budgets and
  resource-cleanup checks at scale.

**303 tests**, covering all 14 requirements (PASS), realistic failure paths,
and performance budgets. See `docs/REQUIREMENT_COMPLIANCE.md` for the full
matrix.

## Requirements Status

All 14 assignment requirements are implemented and verified — **14/14 PASS**.
See `docs/REQUIREMENT_COMPLIANCE.md`.

## Repository Metrics

- Source: 61 Python files, ~3,300 lines in `app/`
- Tests: 32 Python files, ~3,400 lines in `tests/`
- 303 automated tests, all passing
- Lint (Ruff) and format (Black) checks: clean

## Limitations

- Google Maps is the only fully implemented provider; the remaining provider
  slots are placeholders.
- Scraping depends on live Google Maps markup; layout changes or CAPTCHAs may
  require selector updates.
- Email discovery is structural (pattern-based) validation, not DNS/MX
  verification.
- Prompt parsing handles single-location prompts with `in`/`near`/`around`;
  complex or multi-location prompts are not supported yet.

## Future Work

- Implement Bing Maps, Yellow Pages, and Yelp providers.
- Parallel/async scraping across providers.
- Proxy rotation and CAPTCHA handling.
- CSV/Google Sheets export and CRM integrations.
- AI-based lead scoring and enrichment (company size, LinkedIn, social links).
- Stronger email verification (DNS/MX).
- Richer prompt parsing (spaCy NER or an LLM).
