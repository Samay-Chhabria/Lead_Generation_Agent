"""Qt controller that runs the agent on a worker thread.

The controller is the only piece of the GUI that talks to the backend. It
subscribes to the process-wide ``AgentExecutionLogger`` and re-emits every
event on a Qt signal, then runs ``LeadGenerationAgent.run`` inside a
``QThread`` so the UI thread never blocks. All ``event_received`` /
``run_finished`` deliveries are queued to the main thread by Qt, which is what
makes the GUI safe to drive from the worker.
"""

from __future__ import annotations

import contextlib
import gc
import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal

from app.execution.execution_logger import ExecutionEvent, get_execution_logger

#: Callable returning a fully constructed backend agent (built on the worker).
AgentBuilder = Callable[[], object]

_WORKER_LOGGER_NAME = "app.gui.worker"


@contextlib.contextmanager
def _suppress_worker_logging() -> None:
    """Silence stdlib logging while the agent runs on the worker thread.

    Calling ``logging`` from the worker thread is unsafe here: ``findCaller``
    walks the frame stack and Rich's console handler renders output, and both
    can crash the interpreter while the main thread runs a garbage collection
    cycle. Levels (and any detached Rich handlers) are restored as soon as the
    run ends. The GUI's progress still arrives through the
    ``AgentExecutionLogger`` event bus, which is unaffected.
    """
    root = logging.getLogger()
    rich_handlers = [
        handler for handler in root.handlers if handler.__class__.__name__ == "RichHandler"
    ]
    for handler in rich_handlers:
        root.removeHandler(handler)
    silenced: dict[logging.Logger, int] = {}
    for logger in (root, logging.getLogger(_WORKER_LOGGER_NAME)):
        silenced[logger] = logger.level
        logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        for logger, level in silenced.items():
            logger.setLevel(level)
        for handler in rich_handlers:
            root.addHandler(handler)


def build_worker_logger() -> logging.Logger:
    """Return a logger safe to use on the GUI worker thread.

    The agent runs on a QThread while the UI thread renders. This logger
    carries a plain stream handler and never propagates to the root logger, so
    it cannot reach Rich's console handler.
    """
    logger = logging.getLogger(_WORKER_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)
    return logger


class _AgentThread(QThread):
    """Runs a single agent run inside a dedicated thread."""

    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(self, builder: AgentBuilder, prompt: str) -> None:
        super().__init__()
        self._builder = builder
        self._prompt = prompt

    def run(self) -> None:  # noqa: D102
        # CPython 3.14 crashes (access violation) when the main thread's garbage
        # collector runs while a QThread is executing Python. Disable the global
        # cyclic collector for the whole run and restore it when the thread ends.
        gc.disable()
        try:
            agent = self._builder()
            with _suppress_worker_logging():
                result = agent.run(self._prompt, console=False)
            self.finished_result.emit(result)
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(str(exc))
        finally:
            gc.enable()


class AgentController(QObject):
    """Owns the worker thread and marshals backend events into Qt signals."""

    event_received = Signal(object)
    run_finished = Signal(object)
    run_failed = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = get_execution_logger()
        self._thread: _AgentThread | None = None
        self._subscribed = False
        self._logger.subscribe(self._on_logger_event)
        self._subscribed = True

    @property
    def busy(self) -> bool:
        """Return True while an agent run is active."""
        return self._thread is not None and self._thread.isRunning()

    def start(self, prompt: str, builder: AgentBuilder) -> bool:
        """Start a run for ``prompt`` on the worker thread.

        Args:
            prompt: The user's natural-language request.
            builder: Callable that constructs the backend agent.

        Returns:
            True when the run started, False when another run is active.
        """
        if self.busy:
            return False
        self.busy_changed.emit(True)
        thread = _AgentThread(builder, prompt)
        thread.finished_result.connect(self._on_finished_result)
        thread.failed.connect(self._on_run_failed)
        thread.finished.connect(self._on_thread_finished)
        self._thread = thread
        thread.start()
        return True

    def shutdown(self) -> None:
        """Unsubscribe from the logger when the window closes."""
        if self._subscribed:
            self._logger.unsubscribe(self._on_logger_event)
            self._subscribed = False

    # -- Signal handlers ----------------------------------------------------

    def _on_logger_event(self, event: ExecutionEvent) -> None:
        # Called from the worker thread; Qt queues delivery to the main thread.
        self.event_received.emit(event)

    def _on_finished_result(self, result: object) -> None:
        self._release_thread()
        self.run_finished.emit(result)

    def _on_run_failed(self, message: str) -> None:
        self._release_thread()
        self.run_failed.emit(message)

    def _release_thread(self) -> None:
        """Mark the run as finished as soon as its outcome arrives.

        The worker emits ``finished_result`` before its ``finally`` block runs,
        so the built-in ``QThread.finished`` signal can land on the main thread
        a moment later. Relying on that late signal to clear ``busy`` races with
        the UI (the search button stays disabled until it arrives), so the busy
        state is released here instead; the thread's own ``finished`` signal
        only schedules the eventual deletion.
        """
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.finished.connect(thread.deleteLater)
        self.busy_changed.emit(False)

    def _on_thread_finished(self) -> None:
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.deleteLater()
