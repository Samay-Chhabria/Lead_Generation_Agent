# Lead Generation Agent

# Implementation Specification

Version 1.0

---

# Main Entry Point

File

app/main.py

Responsibilities

• Start application

• Read user prompt

• Initialize LeadGenerationAgent

• Execute workflow

Nothing else belongs here.

---

# LeadGenerationAgent

File

agent/lead_generation_agent.py

Public Methods

run()

Private Methods

_parse_prompt()

_launch_browser()

_search_businesses()

_extract_leads()

_validate()

_export()

_print_summary()

Responsibilities

Acts as the project orchestrator.

Never contains extraction logic.

Never contains browser logic.

Only coordinates modules.

---

# PromptParser

File

parser/prompt_parser.py

Input

coffee shops in America

Output

ParsedQuery

Methods

parse()

validate()

Responsibilities

Extract

Business Category

Location

Throw ParserException if prompt invalid.

---

# BrowserManager

File

browser/browser_manager.py

Methods

launch()

new_page()

close()

Responsibilities

Start Playwright

Manage browser

Return page

Close browser

---

# SearchProvider

Abstract Interface

Methods

search()

collect_business_urls()

Supported Providers

Google Maps

Bing Maps

Yellow Pages

Responsibilities

Every provider implements same API.

---

# SearchManager

Methods

search_businesses()

scroll_until_complete()

collect_results()

Responsibilities

Return business URLs.

---

# LeadExtractor

Methods

extract()

_extract_email()

_extract_phone()

_extract_website()

_extract_location()

Return

Lead

---

# Validator

Methods

validate()

clean()

deduplicate()

Responsibilities

Normalize values.

Remove duplicates.

---

# ExcelExporter

Methods

export()

_generate_filename()

Responsibilities

Create workbook.

Write rows.

Autosize columns.

Return path.

---

# SummaryPrinter

Methods

print_summary()

Responsibilities

Pretty console output.

---

# Data Models

Lead

ParsedQuery

SearchResult

Configuration

Settings

---

# Utility Classes

Retry

Timer

Logger

Helpers

---

# Exceptions

ParserException

BrowserException

ExtractionException

ValidationException

---

# End-to-End Flow

User

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

↓

Finish