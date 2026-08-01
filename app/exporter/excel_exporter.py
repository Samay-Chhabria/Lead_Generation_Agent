"""Excel workbook generation (planned for Milestone 7).

Scaffold only. The exporter will create an .xlsx workbook with a headers
row, one row per lead, sized columns, and a meaningful output filename.
"""

from pathlib import Path

from app.models.lead import Lead


class ExcelExporter:
    """Writes collected leads to an .xlsx workbook."""

    def export(self, leads: list[Lead], output_path: Path) -> Path:
        """Export leads to the given file path.

        Args:
            leads: The validated leads to write.
            output_path: Destination for the .xlsx file.

        Returns:
            The path of the created workbook.

        Raises:
            NotImplementedError: Milestone 7 implements this method.
        """
        raise NotImplementedError("ExcelExporter.export will be implemented in Milestone 7.")
