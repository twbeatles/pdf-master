import logging
import os

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_list, _as_str
from ._pdf_impl import FITZ_PDF_ENCRYPT_AES_256, FITZ_PDF_PERM_ACCESSIBILITY, FITZ_PDF_PERM_COPY, FITZ_PDF_PERM_PRINT
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin

logger = logging.getLogger(__name__)


class WorkerBatchOpsMixin(WorkerHost):
    compare_pdfs = _LegacyWorkerPdfOpsMixin.compare_pdfs

    def batch(self):
        """일괄 처리"""
        files = [path for path in _as_list(self.kwargs.get("files")) if isinstance(path, str)]
        output_dir = _as_str(self.kwargs.get("output_dir"))
        operation = _as_str(self.kwargs.get("operation"))
        option = _as_str(self.kwargs.get("option"))
        failed_files: list[tuple[str, str]] = []

        success_count = 0
        skipped_count = 0
        for idx, file_path in enumerate(files):
            self._check_cancelled()
            doc = None
            try:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}_processed.pdf")

                doc = fitz.open(file_path)

                if operation == "compress":
                    self._atomic_pdf_save(doc, out_path, garbage=4, deflate=True)
                elif operation == "watermark" and option:
                    for page in doc:
                        text_rect = fitz.Rect(
                            40,
                            (page.rect.height / 2) - 30,
                            page.rect.width - 40,
                            (page.rect.height / 2) + 30,
                        )
                        page.insert_textbox(
                            text_rect,
                            option,
                            fontsize=40,
                            fontname="helv",
                            color=(0.5, 0.5, 0.5),
                            fill_opacity=0.3,
                            align=1,
                        )
                    self._atomic_pdf_save(doc, out_path)
                elif operation == "encrypt" and option:
                    perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
                    self._atomic_pdf_save(
                        doc,
                        out_path,
                        encryption=FITZ_PDF_ENCRYPT_AES_256,
                        owner_pw=option,
                        user_pw=option,
                        permissions=perm,
                    )
                elif operation == "rotate":
                    for page in doc:
                        page.set_rotation(page.rotation + 90)
                    self._atomic_pdf_save(doc, out_path)
                else:
                    self._atomic_pdf_save(doc, out_path)
                success_count += 1
            except Exception as exc:
                from ..worker import CancelledError

                if isinstance(exc, CancelledError):
                    raise
                logger.warning("Batch error on %s: %s", file_path, exc)
                failed_files.append((os.path.basename(file_path), str(exc)))
                skipped_count += 1
            finally:
                if doc:
                    doc.close()

            self._emit_progress_if_due(int((idx + 1) / len(files) * 100))

        result_msg = self._get_msg("msg_batch_done", success_count, len(files))
        if skipped_count > 0:
            result_msg += self._get_msg("msg_batch_skipped", skipped_count)
            if failed_files:
                result_msg += self._get_msg("msg_batch_failed_header")
                for name, reason in failed_files[:3]:
                    result_msg += f"\n- {name}: {reason}"
                if len(failed_files) > 3:
                    result_msg += self._get_msg("msg_batch_failed_more", len(failed_files) - 3)
        self.finished_signal.emit(result_msg)
