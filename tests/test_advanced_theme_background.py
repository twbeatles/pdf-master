"""Render real advanced pages against an opposite OS palette in isolation.

Fluent owns process-global Qt objects; a subprocess keeps the full window
lifecycle from contaminating the smaller callback/boundary regression suite.
"""

import os
from pathlib import Path
import subprocess
import sys

from _deps import require_pyqt6


def test_advanced_pages_follow_explicit_theme_with_dark_os_palette():
    require_pyqt6()
    script = r'''
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget
from src.ui.fluent_theme import setup_app_theme
from src.ui.main_window import PDFMasterApp
from src.ui import main_window as window_module
from src.core._settings_impl.defaults import default_settings
import tempfile

# Keep the user's settings and exit persistence outside this render check.
window_module.load_settings = default_settings
window_module.save_settings = lambda settings: None
test_temp = tempfile.TemporaryDirectory(prefix="theme-render-")
tempfile.tempdir = test_temp.name

app = QApplication([])
assert setup_app_theme(app)
palette = app.palette()
palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
app.setPalette(palette)
window = PDFMasterApp()
window._save_settings_on_exit = lambda: None
window._save_chat_histories = lambda: None
window.show()
contents = [w for w in window.findChildren(QWidget)
            if w.objectName() == "advancedContent"]
assert len(contents) == 4, len(contents)
for mode, expected in [("light", "#ffffff"), ("dark", "#141922"),
                       ("light", "#ffffff")]:
    window.settings["theme"] = mode
    window._apply_theme()
    app.processEvents()
    for content in contents:
        scroll = content.parentWidget().parentWidget()
        page = scroll.parentWidget()
        for surface in (page, content):
            assert surface.palette().color(surface.backgroundRole()).name() == expected, (
                mode, surface.objectName(), surface.palette().color(surface.backgroundRole()).name())
        image = content.grab().toImage()
        pixel = image.pixelColor(image.width() - 2, image.height() - 2).name()
        assert pixel == expected, (mode, pixel)
window.close()
print("advanced theme rendering OK")
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "advanced theme rendering OK" in result.stdout
