import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 not available")


def _build_window():
    from PyQt6.QtWidgets import QTabWidget, QWidget
    from src.ui.main_window_tabs_basic import MainWindowTabsBasicMixin

    class DummyWindow(QWidget, MainWindowTabsBasicMixin):
        def __init__(self):
            super().__init__()
            self.tabs = QTabWidget()
            self.settings = {}

        def _on_list_item_clicked(self, *_args, **_kwargs):
            return None

        def _update_preview(self, *_args, **_kwargs):
            return None

        def run_worker(self, *_args, **_kwargs):
            return None

    return DummyWindow()


def test_convert_format_combo_exposes_expected_formats():
    _skip_if_missing_deps()
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    _ = app
    win = _build_window()
    win.setup_convert_tab()

    items = [win.cmb_fmt.itemText(i) for i in range(win.cmb_fmt.count())]
    assert items == ["png", "jpg", "webp", "bmp", "tiff"]


def test_convert_preset_falls_back_when_old_format_not_supported(monkeypatch):
    _skip_if_missing_deps()
    from PyQt6.QtWidgets import QApplication
    import src.ui.main_window_tabs_basic as tabs_basic_module

    app = QApplication.instance() or QApplication([])
    _ = app
    win = _build_window()
    win.setup_convert_tab()

    class DummyToast:
        def __init__(self, *_args, **_kwargs):
            pass

        def show_toast(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(tabs_basic_module, "ToastWidget", DummyToast)
    monkeypatch.setattr(
        tabs_basic_module.QInputDialog,
        "getItem",
        lambda *_args, **_kwargs: ("legacy", True),
    )

    win.settings["convert_presets"] = {
        "legacy": {"format": "gif", "dpi": 180},
    }

    win._load_convert_preset()

    assert win.cmb_fmt.currentText() == "png"
    assert win.spn_dpi.value() == 180

