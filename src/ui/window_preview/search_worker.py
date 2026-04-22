import logging
import os

from PyQt6.QtCore import QThread, pyqtSignal

from ...core.optional_deps import fitz

logger = logging.getLogger(__name__)


class PreviewSearchThread(QThread):
    resultsReady = pyqtSignal(int, str, str, int, object)
    failed = pyqtSignal(int, str)
    cancelled = pyqtSignal(int)

    def __init__(
        self,
        pdf_path: str,
        password: str | None,
        query: str,
        request_id: int,
        parent=None,
    ):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.password = password
        self.query = query
        self.request_id = int(request_id)
        self.mtime_ns = self._read_mtime_ns(pdf_path)

    def run(self):
        if not self.pdf_path or not self.query:
            self.failed.emit(self.request_id, "invalid preview search request")
            return

        try:
            doc = fitz.open(self.pdf_path)
        except Exception as exc:
            logger.debug("Preview search open failed", exc_info=True)
            self.failed.emit(self.request_id, str(exc))
            return

        try:
            if doc.is_encrypted:
                if not self.password or not doc.authenticate(self.password):
                    self.failed.emit(self.request_id, "preview search password failed")
                    return

            matches: list[tuple[int, tuple[float, float, float, float]]] = []
            for page_index in range(len(doc)):
                if self.isInterruptionRequested():
                    self.cancelled.emit(self.request_id)
                    return
                page = doc[page_index]
                try:
                    page_matches = page.search_for(self.query)
                except Exception:
                    logger.debug(
                        "Preview search failed on page %s",
                        page_index,
                        exc_info=True,
                    )
                    continue

                for rect in page_matches or []:
                    matches.append(
                        (
                            page_index,
                            (
                                float(getattr(rect, "x0", 0.0)),
                                float(getattr(rect, "y0", 0.0)),
                                float(getattr(rect, "x1", 0.0)),
                                float(getattr(rect, "y1", 0.0)),
                            ),
                        )
                    )

            if self.isInterruptionRequested():
                self.cancelled.emit(self.request_id)
                return
            self.resultsReady.emit(
                self.request_id,
                self.pdf_path,
                self.query,
                self.mtime_ns,
                matches,
            )
        except Exception as exc:
            logger.debug("Preview search worker failed", exc_info=True)
            self.failed.emit(self.request_id, str(exc))
        finally:
            try:
                doc.close()
            except Exception:
                logger.debug("Failed to close preview search document", exc_info=True)

    @staticmethod
    def _read_mtime_ns(path: str) -> int:
        try:
            return int(os.stat(path).st_mtime_ns)
        except OSError:
            return 0
