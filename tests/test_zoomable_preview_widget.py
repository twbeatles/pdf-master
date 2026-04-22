from _deps import require_pyqt6, require_pyqt6_and_pymupdf


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


def test_zoomable_preview_widget_controlled_mode_emits_render_requested_on_resize():
    require_pyqt6()
    import time

    from PyQt6.QtGui import QColor, QPixmap

    from src.ui.zoomable_preview import ZoomablePreviewWidget

    app = _make_app()
    widget = ZoomablePreviewWidget()
    widget.set_controlled_mode(True)
    widget.resize(420, 640)
    widget.show()

    pixmap = QPixmap(320, 480)
    pixmap.fill(QColor("white"))
    widget.set_preview_pixmap(pixmap, current_page=0, total_pages=3)

    renders = []
    widget.renderRequested.connect(lambda: renders.append("render"))

    widget.resize(520, 760)
    time.sleep(0.25)
    app.processEvents()

    widget.close()
    assert renders


def test_zoomable_preview_widget_updates_page_state_and_emits_navigation():
    require_pyqt6()
    from PyQt6.QtGui import QColor, QPixmap

    from src.ui.zoomable_preview import ZoomablePreviewWidget

    app = _make_app()
    widget = ZoomablePreviewWidget()
    widget.set_controlled_mode(True)
    widget.set_navigation_enabled(True)
    widget.resize(420, 640)
    widget.show()
    app.processEvents()

    pixmap = QPixmap(320, 480)
    pixmap.fill(QColor("white"))
    widget.set_preview_pixmap(pixmap, current_page=0, total_pages=3)
    app.processEvents()

    requested_pages = []
    widget.pageChanged.connect(lambda page: requested_pages.append(page))
    widget.go_to_page(1, emit_signal=True)
    app.processEvents()

    assert widget.page_label.text() == "2 / 3"
    assert requested_pages == [1]
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_zoomable_preview_widget_search_panel_toggle_and_state():
    require_pyqt6()

    from src.core.i18n import tm
    from src.ui.zoomable_preview import ZoomablePreviewWidget

    app = _make_app()
    widget = ZoomablePreviewWidget()
    widget.set_controlled_mode(True)
    widget.resize(420, 640)
    widget.show()
    app.processEvents()

    assert not widget.search_bar.isVisible()

    widget.set_search_available(True)
    widget.set_search_panel_visible(True)
    widget.set_search_query("needle")
    widget.set_search_result_state(1, 4, query="needle")
    app.processEvents()

    assert widget.search_bar.isVisible()
    assert widget.btn_toggle_search.text() == tm.get("btn_preview_search_hide")
    assert widget.search_status_label.text() == tm.get(
        "preview_search_status_count", 2, 4
    )
    assert widget.btn_search_prev.isEnabled()
    assert widget.btn_search_next.isEnabled()

    widget.clear_search_state(clear_query=True)
    app.processEvents()

    assert widget.search_input.text() == ""
    assert widget.search_status_label.text() == tm.get("preview_search_status_idle")
    assert not widget.btn_search_prev.isEnabled()
    assert not widget.btn_search_next.isEnabled()

    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_preview_panel_buttons_allow_full_label_width():
    require_pyqt6()

    from src.ui.main_window import PDFMasterApp

    app = _make_app()
    window = PDFMasterApp()
    window.show()
    app.processEvents()

    assert window.btn_prev_page.maximumWidth() >= window.btn_prev_page.sizeHint().width()
    assert window.btn_next_page.maximumWidth() >= window.btn_next_page.sizeHint().width()
    assert window.btn_print_preview.maximumWidth() >= window.btn_print_preview.sizeHint().width()

    window.close()
    window.deleteLater()
    app.processEvents()


def test_zoomable_preview_widget_standalone_load_hides_search_controls(tmp_path):
    require_pyqt6_and_pymupdf()

    from src.core.optional_deps import fitz
    from src.ui.zoomable_preview import ZoomablePreviewWidget

    pdf_path = tmp_path / "standalone.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=300)
    doc.save(str(pdf_path))
    doc.close()

    app = _make_app()
    widget = ZoomablePreviewWidget()
    widget.resize(420, 640)
    widget.show()
    widget.load_pdf(str(pdf_path))
    app.processEvents()

    assert not widget.btn_toggle_search.isVisible()
    assert not widget.search_bar.isVisible()

    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_zoomable_preview_widget_enter_shift_enter_escape_flow():
    require_pyqt6()

    from PyQt6.QtCore import Qt

    from src.ui.zoomable_preview import ZoomablePreviewWidget

    app = _make_app()
    widget = ZoomablePreviewWidget()
    widget.set_controlled_mode(True)
    widget.set_search_available(True)
    widget.set_search_panel_visible(True)
    widget.show()
    app.processEvents()

    search_requests = []
    step_requests = []
    cleared = []

    widget.searchRequested.connect(lambda query: search_requests.append(query))
    widget.searchStepRequested.connect(lambda step: step_requests.append(step))
    widget.searchCleared.connect(lambda: cleared.append(True))

    widget.search_input.setText("needle")
    app.processEvents()
    _send_key(widget.search_input, Qt.Key.Key_Return.value)
    app.processEvents()

    assert search_requests == ["needle"]
    assert step_requests == []

    widget.set_search_result_state(0, 3, query="needle")
    app.processEvents()

    _send_key(widget.search_input, Qt.Key.Key_Return.value)
    app.processEvents()
    _send_key(
        widget.search_input,
        Qt.Key.Key_Return.value,
        Qt.KeyboardModifier.ShiftModifier,
    )
    app.processEvents()

    assert step_requests == [1, -1]

    _send_key(widget.search_input, Qt.Key.Key_Escape.value)
    app.processEvents()
    assert widget.search_input.text() == ""
    assert cleared

    _send_key(widget.search_input, Qt.Key.Key_Escape.value)
    app.processEvents()
    assert not widget.search_bar.isVisible()

    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_main_window_ctrl_f_opens_preview_search_and_focuses_input(tmp_path):
    require_pyqt6_and_pymupdf()

    from PyQt6.QtCore import Qt

    from src.core.optional_deps import fitz
    from src.ui.main_window import PDFMasterApp

    pdf_path = tmp_path / "preview_shortcut.pdf"
    doc = fitz.open()
    page = doc.new_page(width=200, height=300)
    page.insert_text((72, 72), "shortcut target")
    doc.save(str(pdf_path))
    doc.close()

    app = _make_app()
    window = PDFMasterApp()
    window.show()
    window._update_preview(str(pdf_path))
    window.preview_image.set_search_panel_visible(False)
    window.activateWindow()
    app.processEvents()

    assert not window.preview_image.search_bar.isVisible()

    _send_key(
        window,
        Qt.Key.Key_F.value,
        Qt.KeyboardModifier.ControlModifier,
    )
    app.processEvents()

    assert window.preview_image.search_bar.isVisible()
    assert window.preview_image.search_input.hasFocus()

    window.close()
    window.deleteLater()
    app.processEvents()
