# Lead Generation Agent - Technology Stack

Version: 1.0

---

# Overview

This document explains every technology, library, and tool used in the project, why it was selected, possible alternatives, and best practices.

The chosen stack prioritizes:

- Reliability
- Maintainability
- Simplicity
- Cross-platform compatibility
- Performance
- Ease of setup

---

# Programming Language

## Python

Version

Python 3.12+

Reason

- Excellent automation ecosystem
- Mature browser automation libraries
- Great Excel support
- Strong typing support
- Huge community

Alternatives

Node.js

Java

C#

Go

Python provides the best balance for automation tasks.

---

# Browser Automation

Library

Playwright

Reason

- Fast
- Stable
- Modern API
- Auto waiting
- Excellent documentation
- Cross-browser support

Browsers

Chromium

Firefox (future)

WebKit (future)

Alternatives

Selenium

Puppeteer

Recommendation

Use Playwright with Chromium.

---

# HTML Parsing

Library

BeautifulSoup4

Reason

Useful for parsing HTML content from business websites if needed.

Alternative

lxml

XPath

Note

Most extraction will rely on Playwright selectors.

BeautifulSoup is optional.

---

# Data Models

Library

Python dataclasses

Reason

Simple

Fast

Readable

Lightweight

Alternative

Pydantic

Recommendation

Start with dataclasses.

Upgrade to Pydantic only if validation becomes complex.

---

# Excel Generation

Library

openpyxl

Reason

Native .xlsx support

Formatting support

Reliable

Alternative

xlsxwriter

Recommendation

Use openpyxl.

---

# Data Handling

Library

pandas

Purpose

Optional.

Useful for

Data cleaning

Deduplication

Statistics

Future CSV export

If unnecessary, avoid introducing it.

---

# Logging

Library

Python logging

Reason

Built-in

No external dependency

Supports

INFO

WARNING

ERROR

File logging

Console logging

Rotation (future)

---

# Environment Variables

Library

python-dotenv

Purpose

Load

.env

Safely.

Store

Browser settings

Timeouts

Output paths

Future API keys

---

# Testing

Framework

pytest

Reason

Industry standard

Readable

Powerful fixtures

Easy integration

---

# Code Formatting

black

Purpose

Automatic formatting.

---

# Import Sorting

isort

Purpose

Consistent imports.

---

# Linting

ruff

Reason

Fast

Combines many linting checks

Simple configuration

---

# Type Checking

mypy

Purpose

Catch type-related issues during development.

---

# Progress Indicators

tqdm

Purpose

Show scraping progress.

Example

Extracting businesses...

█████████

45/100

---

# Console Output

rich

Purpose

Beautiful tables

Colored logs

Readable summaries

---

# URL Validation

urllib.parse

Reason

Built into Python.

Avoid external dependency.

---

# Email Validation

Regular Expressions

Optional

email-validator package

Recommendation

Start with regex.

---

# Phone Normalization

re

Optional

phonenumbers

Recommendation

Use phonenumbers if international support is needed.

---

# Retry Logic

tenacity

Purpose

Retry transient failures

Browser actions

Network timeouts

Alternative

Custom retry decorator

Recommendation

Start with a lightweight custom retry helper.

---

# Configuration

Use a central settings module.

Example values

HEADLESS=True

MAX_LEADS=50

TIMEOUT=30000

OUTPUT_FOLDER=outputs/

LOG_FOLDER=logs/

SEARCH_PROVIDER=google_maps

---

# Project Dependencies

Core

playwright

openpyxl

python-dotenv

beautifulsoup4

rich

pytest

Optional

pandas

phonenumbers

mypy

black

ruff

isort

---

# Browser Installation

Install dependencies

pip install -r requirements.txt

Install Playwright browsers

playwright install chromium

Verify installation before first run.

---

# Expected Runtime Environment

Operating Systems

Windows

Linux

macOS

Minimum RAM

4 GB

Recommended RAM

8 GB+

Internet

Required

Python

3.12+

---

# Repository Files

requirements.txt

Dependency list.

README.md

Documentation.

.env.example

Configuration template.

.gitignore

Ignore generated files.

LICENSE

Project license.

---

# Version Recommendations

Python 3.12+

Playwright latest stable

openpyxl latest stable

pytest latest stable

rich latest stable

Avoid pinning overly old versions unless compatibility issues arise.

---

# Future Enhancements

Support multiple browser engines.

Proxy support.

CAPTCHA handling.

Async scraping.

Parallel extraction.

Google Sheets export.

Database storage.

CRM integration.

Docker containerization.

CI/CD pipeline with GitHub Actions.