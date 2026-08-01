# Lead Generation Agent - Project Structure

Version: 1.0

---

# Repository Structure

lead-generation-agent/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── lead_generation_agent.py
│   │   └── workflow.py
│   │
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── prompt_parser.py
│   │   └── parser_utils.py
│   │
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── browser_manager.py
│   │   ├── page_manager.py
│   │   └── browser_config.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base_provider.py
│   │   ├── google_maps_provider.py
│   │   ├── bing_maps_provider.py
│   │   └── yellow_pages_provider.py
│   │
│   ├── search/
│   │   ├── __init__.py
│   │   ├── search_manager.py
│   │   └── result_collector.py
│   │
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── lead_extractor.py
│   │   ├── email_extractor.py
│   │   ├── phone_extractor.py
│   │   ├── website_extractor.py
│   │   └── location_extractor.py
│   │
│   ├── validator/
│   │   ├── __init__.py
│   │   ├── validator.py
│   │   ├── email_validator.py
│   │   ├── phone_validator.py
│   │   ├── deduplicator.py
│   │   └── cleaner.py
│   │
│   ├── exporter/
│   │   ├── __init__.py
│   │   ├── excel_exporter.py
│   │   └── filename_generator.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── lead.py
│   │   ├── parsed_query.py
│   │   └── search_result.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   ├── constants.py
│   │   └── logging_config.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── timer.py
│   │   ├── helpers.py
│   │   ├── retry.py
│   │   └── file_utils.py
│   │
│   └── exceptions/
│       ├── __init__.py
│       ├── browser_exception.py
│       ├── extraction_exception.py
│       └── parser_exception.py
│
├── outputs/
│
├── logs/
│
├── tests/
│   ├── test_parser.py
│   ├── test_browser.py
│   ├── test_search.py
│   ├── test_extractor.py
│   ├── test_validator.py
│   ├── test_exporter.py
│   └── test_integration.py
│
├── docs/
│   ├── context.md
│   ├── plan.md
│   ├── architecture.md
│   └── PROJECT_STRUCTURE.md
│
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
└── LICENSE

---

# Folder Responsibilities

## app/

Contains all application source code.

Nothing outside this folder should contain business logic.

---

## agent/

Responsible for orchestrating the complete workflow.

Classes

LeadGenerationAgent

Workflow

Responsibilities

• Receive prompt

• Coordinate modules

• Handle execution

• Produce summary

---

## parser/

Responsible for Natural Language Understanding.

Input

software companies in Karachi

Output

Business Type

software companies

Location

Karachi

Future

Support multilingual parsing.

---

## browser/

Responsible for Playwright lifecycle.

Responsibilities

Launch browser

Open page

Manage tabs

Close browser

Retry browser failures

No scraping logic belongs here.

---

## providers/

Responsible for interacting with specific business listing websites.

Every provider implements the same interface.

Example

GoogleMapsProvider

BingMapsProvider

YellowPagesProvider

Adding another provider should require no changes elsewhere.

---

## search/

Responsible for searching businesses and collecting business page URLs.

Responsibilities

Search

Scroll

Pagination

Collect links

Stop after configured limit

---

## extractor/

Responsible for extracting structured data from business pages.

Responsibilities

Business Name

Email

Phone

Website

Location

Can be extended with

LinkedIn

Instagram

Facebook

Business Hours

Reviews

Ratings

---

## validator/

Responsible for cleaning and validating data.

Tasks

Email validation

Phone normalization

Deduplication

Blank replacement

URL normalization

---

## exporter/

Responsible for writing output files.

Current

Excel

Future

CSV

JSON

Google Sheets

Database

CRM

---

## models/

Contains all shared data models.

Lead

ParsedQuery

SearchResult

No logic.

Only data.

---

## config/

Application configuration.

Environment variables

Constants

Timeouts

Browser settings

Output directory

Search limits

---

## utils/

Reusable helper functions.

Timer

Retry

Helpers

Path utilities

String utilities

---

## exceptions/

Custom exceptions only.

No generic exceptions.

---

## outputs/

Generated Excel files.

Never committed to Git.

---

## logs/

Application logs.

Daily log files.

Ignored by Git.

---

## tests/

Contains all unit and integration tests.

Every module must have tests.

---

# Main Classes

LeadGenerationAgent

PromptParser

BrowserManager

SearchManager

SearchProvider

GoogleMapsProvider

LeadExtractor

Validator

ExcelExporter

SummaryPrinter

Timer

RetryHandler

---

# Dependency Flow

main.py

↓

LeadGenerationAgent

↓

PromptParser

↓

BrowserManager

↓

SearchProvider

↓

SearchManager

↓

LeadExtractor

↓

Validator

↓

ExcelExporter

↓

SummaryPrinter

No module should call upward.

Dependencies only flow downward.

---

# Data Flow

User Prompt

↓

ParsedQuery

↓

Search Results

↓

Business URLs

↓

Raw Leads

↓

Validated Leads

↓

Excel File

↓

Summary

---

# Import Rules

Allowed

Agent → Parser

Agent → Browser

Agent → Search

Agent → Extractor

Agent → Validator

Agent → Exporter

Not Allowed

Exporter importing Browser

Parser importing Extractor

Validator importing Browser

Search importing Exporter

Maintain low coupling.

---

# Naming Convention

Classes

PascalCase

Functions

snake_case

Files

snake_case

Constants

UPPER_CASE

Variables

snake_case

---

# Future Extension Points

Add new provider

Implement BaseProvider

Done.

Add CSV export

Create CSVExporter.

Done.

Add database storage

Create DatabaseExporter.

Done.

Add AI categorization

Create AIParser.

Done.

Minimal modifications required.

---

# Definition of a Healthy Module

Every module should satisfy:

✔ One responsibility

✔ Easily testable

✔ Reusable

✔ Independent

✔ Documented

✔ Type hinted

✔ Logged

✔ Small enough to understand quickly