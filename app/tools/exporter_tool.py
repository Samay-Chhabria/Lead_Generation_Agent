"""Lead exporter tool.

Exports the collected, processed leads to an Excel workbook using the existing
``ExcelExporter``. This is the terminal tool of every plan: it writes the final
deliverable and its result path feeds the execution summary.
"""

from typing import Any

from app.exceptions.export_exception import ExportException
from app.exporter.excel_exporter import ExcelExporter
from app.exporter.file_manager import FileManager
from app.models.lead import Lead
from app.tools.base import Tool, ToolContext, ToolResult


class LeadExporterTool(Tool):
    """Export collected leads to an Excel workbook."""

    name = "lead_exporter"
    description = "Export the collected leads to an Excel workbook file."

    def __init__(
        self,
        context: ToolContext | None = None,
        exporter: ExcelExporter | None = None,
    ) -> None:
        super().__init__(context)
        if exporter is None:
            exporter = ExcelExporter(
                file_manager=FileManager(self.settings.output_dir),
                logger=self._logger,
            )
        self._exporter = exporter

    def run(
        self,
        leads: list[Lead] | None = None,
        business_type: str = "businesses",
        location: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Export the given leads to a workbook.

        Args:
            leads: The processed leads to write.
            business_type: Business category used for the filename.
            location: Optional location used for the filename.

        Returns:
            A ToolResult whose ``data`` holds the output ``path`` and the
            ``exported_count``.
        """
        leads = list(leads or [])
        try:
            path = self._exporter.export(leads, business_type or "businesses", location)
        except ExportException as exc:
            return ToolResult.fail(str(exc))
        except Exception as exc:  # pragma: no cover - defensive catch-all
            return ToolResult.fail(f"Export failed: {exc}")
        self._logger.info("Lead export complete: %d leads -> %s.", len(leads), path)
        return ToolResult.ok(path=path, exported_count=len(leads))
