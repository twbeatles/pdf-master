import os
import time

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _make_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((72, 72), "Alpha Beta Alpha")
    doc.set_toc([[1, "Intro", 1]])
    doc.save(str(path))
    doc.close()


def test_qpdf_preview_widget_updates_page_state_and_zoom(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtPdf import QPdfDocument

    from src.ui.zoomable_preview import ZoomablePreviewWidget

    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)

    app = _make_app()
    widget = ZoomablePreviewWidget()
    doc = QPdfDocument(None)
    assert doc.load(str(pdf_path)) == QPdfDocument.Error.None_
    widget.set_document(doc, str(pdf_path))
    widget.resize(640, 720)
    widget.show()
    app.processEvents()

    widget.go_to_page(0)
    app.processEvents()
    widget._set_custom_zoom(1.5)
    app.processEvents()
    state = widget.capture_view_state()

    assert widget.page_label.text() == "1 / 1"
    assert state["zoom_mode"] == "custom"
    assert state["zoom_factor"] == 1.5

    widget.close()


def test_qpdf_preview_widget_populates_search_and_bookmarks(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import QModelIndex
    from PyQt6.QtPdf import QPdfDocument

    from src.ui.zoomable_preview import ZoomablePreviewWidget

    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)

    app = _make_app()
    widget = ZoomablePreviewWidget()
    doc = QPdfDocument(None)
    assert doc.load(str(pdf_path)) == QPdfDocument.Error.None_
    widget.set_document(doc, str(pdf_path))
    widget.search_input.setText("Alpha")
    widget._on_search_requested()

    for _ in range(50):
        app.processEvents()
        if widget.search_results.count() > 0:
            break
        time.sleep(0.02)

    assert widget.search_results.count() > 0
    assert widget.bookmark_model.rowCount(QModelIndex()) == 1

    widget.close()
