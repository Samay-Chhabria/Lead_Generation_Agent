"""Results / completion panel widget.

Shows the outcome of a finished run: success/failure, businesses found, leads
saved, execution time, the output workbook (with its long path word-wrapped and
selectable), and the Export / Open Folder / Run Again actions.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.gui.widgets.cards import ScrollablePanel, body_frame, soft_wrap


def _open_in_explorer(path: Path) -> None:
    """Open the parent folder of ``path`` in the OS file manager."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


class ResultsPanel(ScrollablePanel):
    """End-of-run results card with completion actions."""

    run_again = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Results", icon="📊", parent=parent)
        self._colors = {"success": "#2fce7a", "danger": "#ff5c68"}
        self._status = QLabel("Ready — enter a prompt and press Search.")
        self._status.setObjectName("h2")
        self._status.setWordWrap(True)
        self.content.addWidget(self._status)

        self._rows: dict[str, QLabel] = {}
        body = body_frame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 8, 10, 8)
        body_layout.setSpacing(4)
        for key in ("businesses", "leads", "time", "output", "output_path"):
            self._rows[key] = self._add_row(body_layout, key)
        self.content.addWidget(body)

        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._open_excel = QPushButton("📤  Export Excel")
        self._open_excel.clicked.connect(self._on_open_excel)
        self._open_folder = QPushButton("📂  Open Folder")
        self._open_folder.clicked.connect(self._on_open_folder)
        self._run_again = QPushButton("🔁  Run Again")
        self._run_again.clicked.connect(self.run_again.emit)
        for button in (self._open_excel, self._open_folder, self._run_again):
            layout.addWidget(button)
        layout.addStretch(1)
        self.content.addWidget(actions)

        self._output_path: Path | None = None

    def reset(self) -> None:
        """Prepare the panel for a new run."""
        self._status.setText("Running...")
        for label in self._rows.values():
            label.setText("")
        self._output_path = None
        self._open_excel.setEnabled(False)
        self._open_folder.setEnabled(False)

    def show_result(self, result: object) -> None:
        """Render the completion screen for an ExecutionResult."""
        success = bool(getattr(result, "success", False))
        self._status.setText("✅ Task Completed Successfully" if success else "❌ Task Failed")
        color = self._colors["success"] if success else self._colors["danger"]
        self._status.setStyleSheet(f"color: {color}; font-weight: 700;")

        businesses = getattr(result, "collected_leads", 0)
        leads = getattr(result, "processed_leads", 0)
        seconds = float(getattr(result, "execution_time", 0.0))
        path = getattr(result, "excel_output_path", None)
        output = Path(path) if path is not None else None

        self._rows["businesses"].setText(f"Businesses Found: {businesses}")
        self._rows["leads"].setText(f"Leads Saved: {leads}")
        self._rows["time"].setText(f"Execution Time: {seconds:.1f} seconds")
        if output is not None:
            self._rows["output"].setText(f"Output File: {output.name}")
            self._rows["output_path"].setText(soft_wrap(str(output)))
            self._output_path = output
            self._open_excel.setEnabled(output.exists())
            self._open_folder.setEnabled(output.parent.exists())
        else:
            self._rows["output"].setText("Output File: —")
            self._rows["output_path"].setText("")
            self._output_path = None
            self._open_excel.setEnabled(False)
            self._open_folder.setEnabled(False)

    def show_error(self, message: str) -> None:
        """Render a failure when the run itself crashed."""
        self._status.setText("❌ Task Failed")
        self._status.setStyleSheet(f"color: {self._colors['danger']}; font-weight: 700;")
        self._rows["businesses"].setText("")
        self._rows["leads"].setText("")
        self._rows["time"].setText("")
        self._rows["output"].setText(f"Reason: {message}")
        self._rows["output_path"].setText("")
        self._output_path = None
        self._open_excel.setEnabled(False)
        self._open_folder.setEnabled(False)

    def apply_theme(self, theme: object) -> None:
        """Store the theme's success/danger colours for status text."""
        self._colors = {"success": theme.success, "danger": theme.danger}

    # -- Internals ----------------------------------------------------------

    def _add_row(self, layout: QVBoxLayout, key: str) -> QLabel:
        label = QLabel("")
        label.setWordWrap(True)
        if key == "output_path":
            label.setObjectName("resultPath")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            label.setObjectName("value")
        layout.addWidget(label)
        return label

    def _on_open_excel(self) -> None:
        if self._output_path is not None and self._output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path)))

    def _on_open_folder(self) -> None:
        if self._output_path is not None:
            _open_in_explorer(self._output_path)
