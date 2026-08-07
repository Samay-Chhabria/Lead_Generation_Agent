<!--
Thank you for contributing! Please complete this template so the change can be
reviewed efficiently. See CONTRIBUTING.md for the full workflow.
-->

## Description

<!--
What does this pull request do? Why is it needed?
If it fixes an issue, reference it: Fixes #123
If it implements a project requirement, name it (e.g. R7).
-->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Refactor (no behavior change)
- [ ] Documentation update
- [ ] CI / build / tooling change
- [ ] Test-only change
- [ ] Other (please describe)

## Testing

<!--
Describe how you verified the change.
-->

- [ ] Ran `ruff check app tests` — no lint errors
- [ ] Ran `black --check app tests` — formatting clean
- [ ] Ran `pytest` — full suite passes (expect `483 passed`)
- [ ] Ran `pytest tests/test_requirement_matrix.py -v` — 14/14 pass (if behavior changed)
- [ ] Verified affected behavior manually (describe how)

<!-- If relevant, paste the pytest summary line. -->

## Checklist

- [ ] My code follows the project's coding standards (see CONTRIBUTING.md)
- [ ] I added or updated tests for my change
- [ ] I updated the documentation if behavior or configuration changed
      (`.env.example`, `README.md`, `RUN_GUIDE.md`, `DEVELOPER_GUIDE.md`,
      `CHANGELOG.md`)
- [ ] I kept the change focused on a single concern
- [ ] I checked for and removed secrets, API keys, and generated artifacts
      (`.xlsx`, `.log`, caches) from the diff

## Screenshots (if applicable)

<!--
Add screenshots or console output that demonstrate the change, especially for
UI, console output, or Excel workbook changes.
-->
