# Lead Generation Agent

## Project Overview

This project is an AI-powered Lead Generation Agent capable of understanding natural language business search requests, automatically searching business listing websites through browser automation, extracting lead information, and exporting the collected data into an Excel spreadsheet.

Example prompts:

- coffee shops in America
- dentists in Lahore
- software companies in Karachi
- marketing agencies in Dubai
- plumbers in New York

The user only provides a natural language prompt.

The system performs the entire workflow automatically.

---

# Objective

Create a fully automated Lead Generation Agent that satisfies all project requirements.

The agent should:

1. Understand the user's request.
2. Extract business category.
3. Extract target location.
4. Launch a browser automatically.
5. Visit a business listing website.
6. Search businesses.
7. Visit business pages.
8. Extract business information.
9. Handle missing data safely.
10. Store results.
11. Export Excel.
12. Print execution summary.

---

# Functional Requirements

## Requirement 1

Accept a natural language prompt.

Example:

coffee shops in America

Output

Business Type:
Coffee Shops

Location:
America

---

## Requirement 2

Automatically extract

Business Category

and

Location

from the prompt.

No manual input should be required.

Possible techniques

- Regex
- spaCy NER
- LLM
- Hybrid parser

---

## Requirement 3

Use Browser Automation.

Preferred framework

Playwright

Alternative

Selenium

Playwright is preferred because it is:

- Faster
- More reliable
- Better maintained
- Easier async support

---

## Requirement 4

Search businesses.

Possible sources

- Bing Maps
- Google Maps
- Yelp
- Yellow Pages

The scraper should be modular so the search source can be changed easily.

---

## Requirement 5

Extract

Business Name

Email

Phone Number

Website

Location

Whenever available.

---

## Requirement 6

Collect multiple businesses.

Not just the first result.

Support configurable limits.

Example

10

20

50

100

---

## Requirement 7

Gracefully handle missing information.

Example

No website

No email

No phone

Should never crash.

Store empty string instead.

---

## Requirement 8

Export Excel

.xlsx

using openpyxl.

---

## Requirement 9

Excel Columns

Business Name

Email

Phone Number

Website

Location

Search Query

Date Collected

(Optional)

---

## Requirement 10

Meaningful filename

Examples

leads.xlsx

leads_coffee_shops.xlsx

software_companies_karachi.xlsx

---

## Requirement 11

Print summary

Example

====================================

Search Query:
coffee shops in America

Businesses Found:
37

Saved:
leads_coffee_shops.xlsx

Execution Time:
54 seconds

====================================

---

## Requirement 12

Project should run successfully after dependencies are installed.

No runtime errors.

Graceful exception handling.

Logging enabled.

---

## Requirement 13

Provide documentation

README.md

Include

Installation

Dependencies

Running

Examples

Folder Structure

Troubleshooting

Output

Screenshots

---

## Requirement 14

Project submission

Do NOT include

node_modules

venv

__pycache__

playwright browsers

Generated Excel files

Instead include

README

requirements.txt

.env.example

.gitignore

source code

---

# Non Functional Requirements

Readable

Modular

Maintainable

Scalable

Reusable

Type hinted

Documented

Testable

Logging enabled

---

# Proposed Tech Stack

Python 3.12+

Playwright

BeautifulSoup (optional)

lxml

pandas

openpyxl

python-dotenv

pydantic

spaCy

Rich

tqdm

logging

---

# Suggested Folder Structure

lead-generation-agent/

│

├── app/

│ ├── agent/

│ ├── parser/

│ ├── browser/

│ ├── scraper/

│ ├── extractor/

│ ├── models/

│ ├── exporter/

│ ├── utils/

│ ├── config/

│ └── main.py

│

├── outputs/

│ └── generated excel files

│

├── logs/

│

├── tests/

│

├── README.md

├── requirements.txt

├── .env.example

├── .gitignore

└── context.md

---

# Agent Workflow

User Prompt

↓

Prompt Parser

↓

Extract Business Type

↓

Extract Location

↓

Launch Browser

↓

Open Maps Website

↓

Search Businesses

↓

Collect Business URLs

↓

Visit Business Pages

↓

Extract Data

↓

Validate Data

↓

Create Lead Objects

↓

Export Excel

↓

Print Summary

↓

Exit

---

# Core Data Model

Lead

Business Name

Email

Phone Number

Website

Location

Search Query

Collected Time

---

# Error Handling

Timeouts

Missing website

Invalid page

No email

Captcha

Browser crash

Network issue

Retry mechanism

Logging

Graceful recovery

---

# Future Improvements

Multiple search engines

Parallel scraping

Proxy rotation

Captcha solving

CSV export

Google Sheets export

CRM integration

Deduplication

Company size

LinkedIn

Social media links

AI lead scoring

Email validation
