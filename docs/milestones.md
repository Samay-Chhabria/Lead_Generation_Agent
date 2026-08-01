# Lead Generation Agent

# Development Milestones

Version 1.0

---

# Overview

The project will be developed incrementally.

Each milestone must:

✓ Compile successfully

✓ Pass all tests

✓ Be committed to Git

✓ Be documented

Only then should development continue.

---

# Milestone 1

## Project Foundation

Estimated Time

30–45 minutes

### Goal

Create the project skeleton.

### Files

README.md

requirements.txt

.gitignore

.env.example

main.py

settings.py

logging_config.py

constants.py

### Deliverables

Project structure

Configuration

Logging

Environment loading

### Testing

Project starts

No import errors

Logging works

Settings load correctly

### Requirements Covered

12

13

14

### Definition of Done

Project runs successfully.

---

# Milestone 2

## Prompt Parser

Estimated Time

1–2 hours

### Goal

Understand user prompts.

### Example

coffee shops in America

↓

Business

coffee shops

Location

America

### Files

prompt_parser.py

parsed_query.py

parser_exception.py

### Tests

20+ prompts

Invalid prompts

Edge cases

### Requirements Covered

1

2

### Definition of Done

Parser extracts category and location correctly.

---

# Milestone 3

## Browser Automation

Estimated Time

1 hour

### Goal

Launch Playwright.

Open browser.

Open page.

Close browser.

### Files

browser_manager.py

browser_config.py

### Tests

Launch browser

Navigate

Close browser

Headless mode

### Requirements Covered

3

---

# Milestone 4

## Search Provider

Estimated Time

2–3 hours

### Goal

Search businesses.

Scroll.

Collect results.

### Files

base_provider.py

google_provider.py

(or chosen provider)

### Tests

Search

Scroll

Collect 20 businesses

### Requirements Covered

4

6

---

# Milestone 5

## Lead Extraction

Estimated Time

3 hours

### Goal

Extract

Business Name

Email

Phone

Website

Location

### Files

lead_extractor.py

lead.py

### Tests

Missing email

Missing phone

Missing website

Missing location

### Requirements Covered

5

7

---

# Milestone 6

## Validation

Estimated Time

1 hour

### Goal

Normalize data.

Remove duplicates.

### Files

validator.py

cleaner.py

### Requirements Covered

7

---

# Milestone 7

## Excel Export

Estimated Time

1 hour

### Goal

Generate .xlsx.

### Files

excel_exporter.py

filename_generator.py

### Requirements Covered

8

9

10

---

# Milestone 8

## Summary

Estimated Time

30 minutes

### Goal

Print execution summary.

### Requirements Covered

11

---

# Milestone 9

## Integration

Estimated Time

2 hours

### Goal

Connect all modules.

### Requirements Covered

1–12

---

# Milestone 10

## Documentation

Estimated Time

1 hour

### Goal

Finish README.

Examples.

Installation.

Usage.

Screenshots.

### Requirements Covered

13

14

---

# Git Workflow

Every milestone

↓

Run tests

↓

Commit

↓

Push

↓

Start next milestone

Never continue with failing tests.

---

# Final Acceptance Criteria

✓ All milestones complete

✓ All tests pass

✓ All 14 requirements complete

✓ Repository clean

✓ Ready for submission