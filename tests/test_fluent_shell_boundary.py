"""Fluent/Qt boundary regression (P2–P4).

- FileSelectorWidget buttons MUST stay Qt: fluent buttons in this shared,
  deleteLater-heavy widget segfault a later global setStyleSheet
  (offscreen suite sequence: file widgets -> toolbar sheet -> main window).
- TabShell adapter contract: QTabWidget-compatible surface on both paths.
- End-to-end lifecycle sequence that used to crash (exit -1073741819).
"""

import os

from _deps import require_pyqt6


def _qapp():
    """Shared QApplication. CALLERS MUST KEEP the returned reference alive
    for the whole test, otherwise the app is garbage-collected and the next
    QWidget construction hits a fatal "Must construct a QApplication"."""
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_file_selector_buttons_stay_qt():
    _qapp_holder = _qapp()
    from PyQt6.QtWidgets import QPushButton

    from src.ui.common_widgets.file_selector import FileSelectorWidget

    selector = FileSelectorWidget()
    try:
        assert type(selector.btn_browse) is QPushButton
        assert type(selector.btn_clear) is QPushButton
    finally:
        selector.deleteLater()
    assert _qapp_holder is not None


def test_tab_shell_surface_contract():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from PyQt6.QtWidgets import QWidget

    from src.ui.tab_shell import TabShell, add_tab

    for mode in ("nav", "pivot"):
        shell = TabShell(mode=mode)
        pages = [QWidget() for _ in range(3)]
        for i, page in enumerate(pages):
            assert add_tab(shell, page, f"label-{i}", icon="SETTING") == i
        assert shell.count() == 3
        shell.setCurrentIndex(2)
        assert shell.currentIndex() == 2
        assert shell.currentWidget() is pages[2]
        assert shell.indexOf(pages[0]) == 0
        shell.setCurrentWidget(pages[1])
        assert shell.currentIndex() == 1
        shell.setDocumentMode(True)
        shell.setTabIcon(0, None)
        shell.setEnabled(False)
        assert not shell.isEnabled()
        shell.setEnabled(True)


def test_add_tab_falls_back_to_plain_qtabwidget():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from PyQt6.QtWidgets import QTabWidget, QWidget

    from src.ui.tab_shell import add_tab

    tabs = QTabWidget()
    page = QWidget()
    assert add_tab(tabs, page, "label", icon="SETTING") == 0
    assert tabs.count() == 1
    assert tabs.widget(0) is page


def test_widget_lifecycle_then_global_stylesheet():
    """Crash-sequence regression: file widgets -> sheets -> tab shell window."""
    app = _qapp()
    from PyQt6.QtWidgets import QWidget

    from src.ui.common_widgets.file_selector import FileSelectorWidget
    from src.ui.tab_shell import TabShell
    from src.ui.theme import DARK_STYLESHEET, NATIVE_DARK_STYLESHEET

    selector = FileSelectorWidget()
    selector.deleteLater()
    app.processEvents()

    app.setStyleSheet(DARK_STYLESHEET)
    app.processEvents()

    shell = TabShell(mode="nav")
    for i in range(8):
        shell.addTab(QWidget(), f"tab-{i}", icon="SETTING")
    shell.show()
    app.processEvents()
    for i in range(8):
        shell.setCurrentIndex(i)
        app.processEvents()
    app.setStyleSheet(NATIVE_DARK_STYLESHEET)
    app.processEvents()
    assert shell.currentIndex() == 7
    shell.close()
