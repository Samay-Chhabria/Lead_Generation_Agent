# Lead Generation Agent Architecture

Version: 1.0

---

# 1. Overview

The Lead Generation Agent is an AI-powered automation system that accepts a natural language query from the user, interprets the desired business category and location, searches an online business directory using browser automation, extracts lead information, validates the collected data, and exports the results into an Excel spreadsheet.

The entire process is fully automated and requires only a single natural language prompt from the user.

Example:

Input

"software companies in Karachi"

Output

outputs/leads_software_companies_karachi.xlsx

containing

• Business Name
• Email
• Phone Number
• Website
• Location

---

# 2. Goals

The system should

✓ Accept natural language

✓ Automatically understand the search

✓ Use browser automation

✓ Collect multiple businesses

✓ Extract structured data

✓ Handle missing information

✓ Export Excel

✓ Print execution summary

✓ Never crash because of missing fields

✓ Be modular

✓ Be extensible

✓ Be easy to maintain

---

# 3. High Level Architecture

                    User
                      │
                      ▼
            LeadGenerationAgent
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
 Prompt Parser   Browser Manager   Configuration
      │
      ▼
 Search Manager
      │
      ▼
 Business Collector
      │
      ▼
 Lead Extractor
      │
      ▼
 Data Validator
      │
      ▼
 Excel Exporter
      │
      ▼
 Execution Summary

---

# 4. Agent Responsibilities

The LeadGenerationAgent acts as the central orchestrator.

Responsibilities

• Receive prompt
• Parse prompt
• Start browser
• Execute search
• Collect businesses
• Extract leads
• Validate leads
• Export Excel
• Print summary
• Handle failures

No business logic should exist inside main.py.

main.py should only initialize the agent.

---

# 5. System Workflow

User enters prompt

↓

Prompt Parser

↓

Extract

Business Category

Location

↓

Launch Browser

↓

Open Business Listing Website

↓

Search

↓

Collect Business URLs

↓

Visit Every Business

↓

Extract Information

↓

Validate

↓

Store Lead Objects

↓

Export Excel

↓

Print Summary

↓

Close Browser

---

# 6. Module Responsibilities

## Prompt Parser

Input

coffee shops in America

Output

Business Type

coffee shops

Location

America

Responsibilities

• Parse prompt

• Validate prompt

• Handle malformed input

Future

Support multilingual prompts

--------------------------------------------

## Browser Manager

Responsibilities

Launch Chromium

Configure Playwright

Manage pages

Handle timeouts

Close browser

No scraping logic belongs here.

--------------------------------------------

## Search Manager

Responsibilities

Navigate to website

Search businesses

Wait for results

Scroll

Collect business links

Support future search engines.

--------------------------------------------

## Business Collector

Responsibilities

Collect all business pages

Avoid duplicates

Support configurable limit

Example

10

20

50

100

--------------------------------------------

## Lead Extractor

Responsibilities

Visit business page

Extract

Business Name

Email

Phone

Website

Location

Never throw exception because a field is missing.

--------------------------------------------

## Validator

Responsibilities

Validate emails

Normalize URLs

Normalize phone numbers

Remove duplicates

Replace missing values

--------------------------------------------

## Excel Exporter

Responsibilities

Create workbook

Create sheet

Write headers

Write rows

Auto-size columns

Save workbook

Return output path

--------------------------------------------

## Summary Printer

Responsibilities

Print

Search Query

Businesses Found

Saved File

Execution Time

---

# 7. Data Flow

Prompt

↓

Parsed Query

↓

Search Results

↓

Business Links

↓

Raw Lead Data

↓

Validated Lead Data

↓

Excel

Every stage has only one responsibility.

---

# 8. Data Model

Lead

Business Name

Email

Phone Number

Website

Location

Search Query

Collected At

Implementation

Prefer dataclass or Pydantic model.

---

# 9. Browser Automation Workflow

Start Browser

↓

Open Website

↓

Search

↓

Wait

↓

Scroll

↓

Collect Results

↓

Visit Each Result

↓

Extract Information

↓

Repeat

↓

Close Browser

Browser should always close even when exceptions occur.

---

# 10. Error Handling Strategy

Possible failures

Browser fails

Timeout

Network failure

Missing elements

Invalid selectors

No search results

No email

No website

No phone

Recovery

Retry

Skip business

Continue execution

Log error

Never terminate entire run because of one business.

---

# 11. Logging Strategy

INFO

Browser started

Searching

Business found

Excel exported

WARNING

Email missing

Phone missing

Website missing

ERROR

Browser crash

Timeout

Unexpected exception

Log file

logs/application.log

---

# 12. Configuration

Store configurable values

Browser

Headless mode

Timeout

Maximum leads

Search website

Output folder

Log folder

These should never be hardcoded.

---

# 13. Extensibility

Future search sources

Google Maps

Bing Maps

Yellow Pages

Yelp

Clutch

LinkedIn Company Search

Only SearchManager should change.

Everything else remains unchanged.

---

# 14. Testing Strategy

Each module must be tested independently.

Prompt Parser

Browser Manager

Search Manager

Lead Extractor

Validator

Exporter

Finally

End-to-End Integration Test

---

# 15. Sequence Diagram

User

↓

main.py

↓

LeadGenerationAgent

↓

PromptParser

↓

BrowserManager

↓

SearchManager

↓

BusinessCollector

↓

LeadExtractor

↓

Validator

↓

ExcelExporter

↓

SummaryPrinter

↓

User receives Excel

---

# 16. Design Principles

Single Responsibility Principle

Open/Closed Principle

Dependency Injection where appropriate

Low coupling

High cohesion

Reusable components

No duplicated logic

Typed interfaces

Clear module boundaries

---

# 17. Folder Ownership

main.py

Application entry point only.

agent/

Workflow orchestration.

browser/

Playwright management.

parser/

Natural language parsing.

search/

Searching businesses.

extractor/

Lead extraction.

validator/

Data cleaning.

exporter/

Excel generation.

models/

Lead data structures.

utils/

Helpers.

config/

Settings and constants.

logs/

Execution logs.

outputs/

Generated Excel files.

tests/

Unit and integration tests.

---

# 18. Completion Criteria

The project is complete only when

✓ All 14 assignment requirements are satisfied.

✓ The program runs from one command.

✓ One natural language prompt starts the entire workflow.

✓ Multiple leads are collected.

✓ Missing fields are handled safely.

✓ Excel file is generated.

✓ Summary is displayed.

✓ Documentation is complete.

✓ Repository is clean.

✓ No runtime errors under supported setup.