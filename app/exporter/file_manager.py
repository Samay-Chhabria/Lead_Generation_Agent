"""Output filename generation and destination management.

FileManager owns the "where and what to call the workbook" concern so the
exporter stays free of filesystem naming logic. It builds meaningful filenames
from the search context (``leads_<business_type>_<location>.xlsx``), keeps them
filesystem-safe, avoids silently overwriting previous exports by appending a
timestamp when a file already exists, and makes sure the destination directory
exists before a workbook is saved (Requirement 10).
"""

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.exceptions.export_exception import ExportException
from app.utils.helpers import ensure_directory

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE_RUNS = re.compile(r"\s+")
_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class FileManager:
    """Build safe, meaningful output paths inside a configured directory.

    Args:
        output_dir: Directory where workbooks are saved. It is created
            automatically when missing.
        clock: Callable returning the current datetime; injectable so filename
            timestamping is deterministic in tests.
    """

    def __init__(self, output_dir: Path, clock: Callable[[], datetime] | None = None) -> None:
        self._output_dir = Path(output_dir)
        self._clock = clock or datetime.now

    def generate_filename(self, business_type: str, location: str | None = None) -> str:
        """Build ``leads_<business_type>_<location>.xlsx``.

        Spaces are replaced with underscores and characters that are invalid in
        filenames are stripped. An empty ``location`` is omitted from the name.

        Args:
            business_type: The business category from the search prompt.
            location: Optional target location from the search prompt.

        Returns:
            A filesystem-safe filename ending in ``.xlsx``.

        Raises:
            ExportException: When the business type has no usable characters.
        """
        business = self._sanitize_component(business_type)
        if not business:
            raise ExportException("Business type produces an unusable filename.")
        parts = ["leads", business]
        location_part = self._sanitize_component(location) if location else ""
        if location_part:
            parts.append(location_part)
        return "_".join(parts) + ".xlsx"

    def resolve_path(self, business_type: str, location: str | None = None) -> Path:
        """Return the destination path, avoiding clobbering existing files.

        When the base filename already exists in the output directory, a
        timestamp (``_YYYYMMDD_HHMMSS``) is appended before the extension so no
        previous export is ever overwritten.

        Args:
            business_type: The business category from the search prompt.
            location: Optional target location from the search prompt.

        Returns:
            The full destination path inside the output directory.
        """
        filename = self.generate_filename(business_type, location)
        target = self._output_dir / filename
        if target.exists():
            stamp = self._clock().strftime(_TIMESTAMP_FORMAT)
            target = self._output_dir / f"{target.stem}_{stamp}.xlsx"
        return target

    def save_path(self, business_type: str, location: str | None = None) -> Path:
        """Resolve the destination path and ensure its directory exists.

        Args:
            business_type: The business category from the search prompt.
            location: Optional target location from the search prompt.

        Returns:
            The full destination path, ready to be saved to.

        Raises:
            ExportException: When the output directory cannot be created.
        """
        path = self.resolve_path(business_type, location)
        try:
            ensure_directory(path.parent)
        except OSError as exc:
            raise ExportException(f"Cannot create output directory '{path.parent}': {exc}") from exc
        return path

    @staticmethod
    def _sanitize_component(part: str) -> str:
        """Make a filename component safe and underscore-separated."""
        cleaned = _WHITESPACE_RUNS.sub("_", part.strip())
        cleaned = _INVALID_FILENAME_CHARS.sub("", cleaned)
        return cleaned.strip("._ ")
