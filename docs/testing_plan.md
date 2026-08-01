# Testing Plan

Project: Lead Generation Agent

Version: 1.0

---

# Purpose

This document defines the testing strategy for the Lead Generation Agent.

Every module must pass its individual tests before integration.

No new module should be implemented until the previous module passes all tests.

---

# Testing Levels

The project will be tested at four levels:

1. Unit Testing
2. Module Testing
3. Integration Testing
4. End-to-End Testing

---

# Testing Environment

Operating System

- Windows 11
- Ubuntu 22.04 (Optional)
- macOS (Optional)

Python

3.12+

Browser

Chromium (Playwright)

Internet

Required

---

# Unit Tests

## Prompt Parser

### Test 1

Input

coffee shops in America

Expected

Business Type

coffee shops

Location

America

Status

☐ Pass

---

### Test 2

Input

software companies in Karachi

Expected

Business Type

software companies

Location

Karachi

Status

☐ Pass

---

### Test 3

Input

dentists near Lahore

Expected

Business Type

dentists

Location

Lahore

Status

☐ Pass

---

### Test 4

Input

restaurants in New York

Expected

Business Type

restaurants

Location

New York

Status

☐ Pass

---

### Test 5

Invalid Prompt

Input

abc

Expected

Validation Error

Status

☐ Pass

---

# Browser Manager Tests

### Browser Launch

Expected

Chromium launches successfully.

Status

☐ Pass

---

### New Page

Expected

A new browser page opens.

Status

☐ Pass

---

### Close Browser

Expected

Browser closes without exceptions.

Status

☐ Pass

---

### Headless Mode

Expected

Runs successfully in headless mode.

Status

☐ Pass

---

# Search Provider Tests

### Search Query

Input

software companies in Karachi

Expected

Search page opens.

Results appear.

Status

☐ Pass

---

### Result Collection

Expected

Collect multiple businesses.

Minimum

10

Status

☐ Pass

---

### Scroll Test

Expected

Dynamic scrolling loads additional results.

Status

☐ Pass

---

### Pagination (if applicable)

Expected

Next page loads correctly.

Status

☐ Pass

---

# Lead Extraction Tests

Each extracted lead should contain:

Business Name

Email

Phone Number

Website

Location

---

### Test Business With Complete Information

Expected

All fields populated correctly.

Status

☐ Pass

---

### Missing Email

Expected

Email = ""

No crash.

Status

☐ Pass

---

### Missing Phone

Expected

Phone = ""

Status

☐ Pass

---

### Missing Website

Expected

Website = ""

Status

☐ Pass

---

### Missing Location

Expected

Location = ""

Status

☐ Pass

---

# Validator Tests

### Duplicate Removal

Input

Duplicate businesses

Expected

Only one record remains.

Status

☐ Pass

---

### Invalid Email

Expected

Handled gracefully.

Status

☐ Pass

---

### Invalid URL

Expected

Normalized or left blank.

Status

☐ Pass

---

### Invalid Phone Number

Expected

Normalized or left blank.

Status

☐ Pass

---

# Excel Export Tests

### Workbook Creation

Expected

.xlsx file created.

Status

☐ Pass

---

### Sheet Creation

Expected

One worksheet.

Status

☐ Pass

---

### Header Validation

Expected Columns

Business Name

Email

Phone Number

Website

Location

Search Query

Date Collected

Status

☐ Pass

---

### Row Count

Input

25 leads

Expected

25 rows written.

Status

☐ Pass

---

### Auto Column Width

Expected

Readable columns.

Status

☐ Pass

---

### Filename

Expected

leads_software_companies_karachi.xlsx

Status

☐ Pass

---

# Logging Tests

Expected

INFO logs

WARNING logs

ERROR logs

Log file generated

Status

☐ Pass

---

# Exception Handling Tests

## Browser Crash

Expected

Application exits gracefully.

Status

☐ Pass

---

## Network Failure

Expected

Retry

or

Graceful error message.

Status

☐ Pass

---

## Missing Business Information

Expected

Skip missing fields.

Continue processing.

Status

☐ Pass

---

## Invalid Selectors

Expected

Log error.

Continue processing.

Status

☐ Pass

---

# Performance Tests

Lead Count

10

Expected

<30 seconds

Status

☐ Pass

---

Lead Count

25

Expected

<90 seconds

Status

☐ Pass

---

Lead Count

50

Expected

<3 minutes

Status

☐ Pass

---

# Integration Tests

## Full Workflow

Input

software companies in Karachi

Expected Workflow

✔ Prompt parsed

✔ Browser launched

✔ Search completed

✔ Multiple businesses collected

✔ Leads extracted

✔ Validation completed

✔ Excel generated

✔ Summary printed

Status

☐ Pass

---

## Missing Data Workflow

Expected

Program completes successfully.

Blank values inserted.

Status

☐ Pass

---

## Empty Search Results

Input

Businesses that do not exist

Expected

Excel created with headers only.

Summary reports

0 leads.

Status

☐ Pass

---

# End-to-End Acceptance Tests

## Requirement 1

Accept natural language prompt

☐ Pass

---

## Requirement 2

Extract business category and location

☐ Pass

---

## Requirement 3

Browser automation

☐ Pass

---

## Requirement 4

Search businesses

☐ Pass

---

## Requirement 5

Extract lead information

☐ Pass

---

## Requirement 6

Collect multiple leads

☐ Pass

---

## Requirement 7

Handle missing information

☐ Pass

---

## Requirement 8

Generate Excel

☐ Pass

---

## Requirement 9

Correct Excel columns

☐ Pass

---

## Requirement 10

Meaningful filename

☐ Pass

---

## Requirement 11

Execution summary

☐ Pass

---

## Requirement 12

No runtime errors

☐ Pass

---

## Requirement 13

README complete

☐ Pass

---

## Requirement 14

Submission ready

☐ Pass

---

# Regression Testing

After every completed milestone:

- Re-run Prompt Parser tests
- Re-run Browser tests
- Re-run Search tests
- Re-run Extraction tests
- Re-run Export tests
- Re-run Integration tests

No new module should break existing functionality.

---

# Final Release Checklist

□ All unit tests pass

□ All integration tests pass

□ All end-to-end tests pass

□ All 14 requirements verified

□ No runtime exceptions

□ README updated

□ Requirements file verified

□ .env.example verified

□ .gitignore verified

□ Output Excel generated successfully

□ Repository ready for submission