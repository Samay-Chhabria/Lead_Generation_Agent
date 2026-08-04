"""Excel workbook export (Milestone 7).

ExcelExporter coordinates workbook construction and destination management to
produce a professional .xlsx file from already-processed Lead objects
(Requirement 8). It performs no normalization or validation itself: callers hand
it the final, cleaned leads. Construction and file-system concerns are delegated
to injectable collaborators (WorkbookBuilder and FileManager) so each piece can
be tested and replaced in isolation.
"""

import logging
from pathlib import Path

from openpyxl.utils import exceptions as openpyxl_exceptions

from app.config.logging_config import get_logger
from app.exceptions.export_exception import ExportException
from app.exporter.file_manager import FileManager
from app.exporter.workbook_builder import WorkbookBuilder
from app.models.lead import Lead

_SAVE_ERRORS: tuple[type[BaseException], ...] = (OSError,) + tuple(
    member
    for member in vars(openpyxl_exceptions).values()
    if isinstance(member, type) and issubclass(member, Exception)
)


class ExcelExporter:
    """Write processed leads to a meaningful .xlsx workbook."""

    def __init__(
        self,
        workbook_builder: WorkbookBuilder | None = None,
        file_manager: FileManager | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the exporter with optional injectable collaborators.

        Args:
            workbook_builder: Optional WorkbookBuilder; a default is created
                when omitted.
            file_manager: Optional FileManager; a default is created when
                omitted.
            logger: Optional logger; a package logger is used when omitted.
        """
        self._builder = workbook_builder or WorkbookBuilder(logger=logger)
        self._file_manager = file_manager or FileManager(Path("outputs"))
        self._logger = logger or get_logger("exporter")

    def export(self, leads: list[Lead], business_type: str, location: str | None = None) -> Path:
        """Build and save a workbook for the given leads.

        Args:
            leads: The processed leads to write. Missing fields are written as
                blank cells.
            business_type: The business category used for the filename.
            location: Optional target location used for the filename.

        Returns:
            The path of the saved .xlsx workbook.

        Raises:
            ExportException: When the workbook cannot be built, named, or saved.
        """
        self._logger.info("Exporting leads...")
        workbook = self._builder.build(leads)
        try:
            path = self._file_manager.save_path(business_type, location)
            workbook.save(path)
        except ExportException:
            raise
        except _SAVE_ERRORS as exc:
            raise ExportException(f"Workbook could not be saved: {exc}") from exc
        self._logger.info("Workbook saved: %s.", path)
        self._logger.info("Export completed. Output: %s.", path)
        return path
