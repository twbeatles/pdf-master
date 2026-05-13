import os

from _deps import require_pyqt6


def _qapp():
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_progress_overlay_uses_english_runtime_strings():
    app = _qapp()
    from src.core.i18n import tm
    from src.ui.progress_overlay import ProgressOverlayWidget

    previous_lang = tm.active_lang_code
    tm.active_lang_code = "en"
    widget = None
    try:
        widget = ProgressOverlayWidget()
        widget.show_progress()
        assert widget.title_label.text() == "Processing..."
        assert widget.desc_label.text() == "Please wait..."
        assert widget.cancel_btn.text() == "✕ Cancel"

        widget.update_progress(100)
        assert widget.title_label.text() == "Done!"

        widget._on_cancel()
        assert widget.cancel_btn.text() == "Cancelling..."
        assert widget.desc_label.text() == "Cancelling the current task..."
    finally:
        tm.active_lang_code = previous_lang
        if widget is not None:
            widget.deleteLater()
        app.processEvents()


def test_file_widgets_use_english_tooltips():
    app = _qapp()
    from src.core.i18n import tm
    from src.ui.widgets import FileListWidget, FileSelectorWidget, ImageListWidget

    previous_lang = tm.active_lang_code
    tm.active_lang_code = "en"
    selector = None
    pdf_list = None
    image_list = None
    try:
        selector = FileSelectorWidget()
        pdf_list = FileListWidget()
        image_list = ImageListWidget()

        assert selector.btn_browse.toolTip() == "Click to select a file"
        assert selector.btn_clear.toolTip() == "Clear the selected file"
        assert pdf_list.toolTip() == "Drag PDF files here. You can also reorder them."
        assert image_list.toolTip() == "Drag image files here (PNG, JPG, etc.)"
    finally:
        tm.active_lang_code = previous_lang
        if selector is not None:
            selector.deleteLater()
        if pdf_list is not None:
            pdf_list.deleteLater()
        if image_list is not None:
            image_list.deleteLater()
        app.processEvents()
