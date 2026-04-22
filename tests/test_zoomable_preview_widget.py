import os
import time

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _send_key(widget, key, modifiers=None):
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QApplication

    if modifiers is None:
        modifiers = Qt.KeyboardModifier.NoModifier
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, key, modifiers))
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyRelease, key, modifiers))


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


def test_qpdf_preview_widget_toggle_search_panel_and_restore_state(tmp_path):
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

    widget.set_search_panel_visible(False)
    state = widget.capture_view_state()

    assert not widget.side_tabs.isVisible()
    assert state["search_panel_visible"] is False

    widget.restore_view_state(
        {
            "page": 0,
            "zoom_mode": "fit_view",
            "zoom_factor": 1.0,
            "search_panel_visible": True,
            "side_tab_index": 0,
            "search_query": "Alpha",
            "search_result_row": 0,
        }
    )

    for _ in range(50):
        app.processEvents()
        if widget.search_results.count() > 0:
            break
        time.sleep(0.02)

    assert widget.side_tabs.isVisible()
    assert widget.search_input.text() == "Alpha"
    assert widget.search_results.currentRow() == 0

    widget.close()


def test_qpdf_preview_widget_enter_shift_enter_and_escape(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
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

    widget.focus_search_input()
    widget.search_input.setText("Alpha")
    _send_key(widget.search_input, Qt.Key.Key_Return.value)

    for _ in range(50):
        app.processEvents()
        if widget.search_results.count() > 1:
            break
        time.sleep(0.02)

    assert widget.search_results.count() > 1

    widget.search_results.setCurrentRow(0)
    _send_key(widget.search_input, Qt.Key.Key_Return.value)
    app.processEvents()
    assert widget.search_results.currentRow() == 1

    _send_key(
        widget.search_input,
        Qt.Key.Key_Return.value,
        Qt.KeyboardModifier.ShiftModifier,
    )
    app.processEvents()
    assert widget.search_results.currentRow() == 0

    _send_key(widget.search_input, Qt.Key.Key_Escape.value)
    app.processEvents()
    assert widget.search_input.text() == ""

    _send_key(widget.search_input, Qt.Key.Key_Escape.value)
    app.processEvents()
    assert not widget.side_tabs.isVisible()

    widget.close()


def test_main_window_ctrl_f_opens_preview_search_and_focuses_input(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt

    from src.ui.main_window import PDFMasterApp

    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)

    app = _make_app()
    window = PDFMasterApp()
    window.show()
    window._update_preview(str(pdf_path))
    window.preview_image.set_search_panel_visible(False)
    app.processEvents()

    _send_key(window, Qt.Key.Key_F.value, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()

    assert window.preview_image.side_tabs.isVisible()
    assert window.preview_image.side_tabs.currentIndex() == 0
    assert window.preview_image.search_input.hasFocus()

    window.close()
