"""Generic helper utilities."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create the directory (and any parents) if missing, then return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
