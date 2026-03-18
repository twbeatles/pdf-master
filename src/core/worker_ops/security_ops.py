import logging

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_str
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin

logger = logging.getLogger(__name__)


class WorkerSecurityOpsMixin(WorkerHost):
    protect = _LegacyWorkerPdfOpsMixin.protect

    def decrypt_pdf(self):
        """암호화된 PDF 복호화"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        password = _as_str(self.kwargs.get("password"))
        doc = None
        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted and not doc.authenticate(password):
                raise ValueError(self._get_msg("err_wrong_password"))

            self._atomic_pdf_save(doc, output_path, garbage=4, deflate=True)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_decryption_success"))
