"""Application entry point.

Contains no business logic: it only creates the application and runs it. The
prompt is read interactively from the console ("Please enter your search:").

Run from the repository root with:

    python app/main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.application import LeadGenerationApplication


def main() -> int:
    """Bootstrap and run the Lead Generation Application interactively."""
    application = LeadGenerationApplication()
    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
