"""Application entry point.

Contains no business logic: it only creates the application and runs it.

Run from the repository root with:

    python app/main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.application import LeadGenerationApplication


def main() -> int:
    """Bootstrap and run the Lead Generation Application."""
    prompt = sys.argv[1] if len(sys.argv) > 1 else None
    application = LeadGenerationApplication()
    return application.run(prompt)


if __name__ == "__main__":
    raise SystemExit(main())
