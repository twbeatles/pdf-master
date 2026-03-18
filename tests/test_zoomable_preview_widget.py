from _deps import require_pyqt6


def _make_app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


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
