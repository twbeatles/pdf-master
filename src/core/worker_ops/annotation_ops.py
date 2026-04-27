from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_int, _as_str
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin


class WorkerAnnotationOpsMixin(WorkerHost):
    watermark = _LegacyWorkerPdfOpsMixin.watermark
    image_watermark = _LegacyWorkerPdfOpsMixin.image_watermark
    add_page_numbers = _LegacyWorkerPdfOpsMixin.add_page_numbers
    add_stamp = _LegacyWorkerPdfOpsMixin.add_stamp
    insert_signature = _LegacyWorkerPdfOpsMixin.insert_signature
    highlight_text = _LegacyWorkerPdfOpsMixin.highlight_text
    draw_shapes = _LegacyWorkerPdfOpsMixin.draw_shapes
    add_link = _LegacyWorkerPdfOpsMixin.add_link
    add_text_markup = _LegacyWorkerPdfOpsMixin.add_text_markup
    insert_textbox = _LegacyWorkerPdfOpsMixin.insert_textbox
    add_sticky_note = _LegacyWorkerPdfOpsMixin.add_sticky_note
    add_ink_annotation = _LegacyWorkerPdfOpsMixin.add_ink_annotation
    add_freehand_signature = _LegacyWorkerPdfOpsMixin.add_freehand_signature
    redact_text = _LegacyWorkerPdfOpsMixin.redact_text

    def add_annotation(self):
        """PDF에 주석 추가"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)
        annot_type = _as_str(self.kwargs.get("annot_type"), "text")
        text = _as_str(self.kwargs.get("text"))
        point = cast(list[float], self.kwargs.get("point") or [100, 100])
        rect = cast(list[float], self.kwargs.get("rect") or [100, 100, 300, 150])
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]
            annot = None
            if annot_type in ("text", "sticky"):
                annot = page.add_text_annot(fitz.Point(point[0], point[1]), text)
            elif annot_type == "freetext":
                annot = page.add_freetext_annot(fitz.Rect(rect), text, fontsize=12)
            else:
                self.error_signal.emit(self._get_msg("err_operation_failed", f"unsupported annotation type: {annot_type}"))
                return

            if annot:
                annot.update()

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_annotation_added", page_num + 1))

    def remove_annotations(self):
        """PDF에서 모든 주석 제거"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        count = 0
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            for page in doc:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    page.delete_annot(annot)
                    count += 1
                    annot = next_annot

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_annotations_removed", count))
