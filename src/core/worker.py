import logging
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from .worker_ops import WorkerAiOpsMixin, WorkerPdfOpsMixin
from .worker_runtime import WorkerRuntimeMixin

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    """작업 취소 시 발생하는 예외"""


class WorkerThread(QThread, WorkerRuntimeMixin, WorkerPdfOpsMixin, WorkerAiOpsMixin):
    progress_signal = pyqtSignal(int)
    partial_result_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal(str)

    def __init__(self, mode: str, **kwargs: Any):
        super().__init__()
        self.mode = mode
        created_output_paths = kwargs.get("created_output_paths")
        if not isinstance(created_output_paths, list):
            kwargs["created_output_paths"] = []
        self.kwargs = kwargs
        self.result_payload: dict[str, Any] = {}
        self._cancel_requested = False
        self._last_progress_value: int | None = None
        self._last_progress_emit_ts_ms = 0.0
        logger.debug("WorkerThread initialized: mode=%s", mode)

    def cancel(self):
        """작업 취소 요청"""
        self._cancel_requested = True
        try:
            self.requestInterruption()
        except Exception:
            logger.debug("requestInterruption() failed", exc_info=True)
        logger.info("Cancel requested for task: %s", self.mode)

    def run(self):
        return WorkerRuntimeMixin.run(self)
