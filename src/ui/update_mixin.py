"""User-facing signed-update flow."""
from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from ..core.constants import UPDATE_MANIFEST_URL, UPDATE_PUBLIC_KEY_B64, UPDATE_RELEASES_URL, VERSION
from ..core.i18n import tm
from ..core.update_installer import launch_update_helper, stage_update
from ..core.update_manifest import NoUpdateAvailableError, download_release_manifest, verify_release_manifest

logger = logging.getLogger(__name__)


class _UpdateSignals(QObject):
    ready = pyqtSignal(object)
    current = pyqtSignal()
    failed = pyqtSignal(str)


class UpdateMixin:
    def _initialize_updates(self) -> None:
        self._update_signals = _UpdateSignals(self)
        self._update_signals.ready.connect(self._offer_update)
        self._update_signals.current.connect(lambda: QMessageBox.information(self, tm.get("update_title"), tm.get("update_current")))
        self._update_signals.failed.connect(lambda error: QMessageBox.warning(self, tm.get("update_check_failed"), error))
        QTimer.singleShot(2000, lambda: self.check_for_updates(silent=True))

    def check_for_updates(self, silent: bool = False) -> None:
        def worker() -> None:
            try:
                manifest = verify_release_manifest(download_release_manifest(UPDATE_MANIFEST_URL), public_key=UPDATE_PUBLIC_KEY_B64, current_version=VERSION)
            except NoUpdateAvailableError:
                if not silent:
                    self._update_signals.current.emit()
            except Exception as exc:
                logger.warning("Update check failed", exc_info=True)
                if not silent:
                    self._update_signals.failed.emit(str(exc))
            else:
                self._update_signals.ready.emit(manifest)
        threading.Thread(target=worker, name="PDFMasterUpdateCheck", daemon=True).start()

    def _offer_update(self, manifest) -> None:
        if not getattr(sys, "frozen", False):
            QMessageBox.information(self, tm.get("update_title"), tm.get("update_dev_available", manifest.version))
            return
        choice = QMessageBox.question(self, tm.get("update_found"), tm.get("update_offer", manifest.version), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            staged = stage_update(manifest)
            launch_update_helper(target=Path(sys.executable).resolve(), staged=staged)
        except Exception as exc:
            QMessageBox.warning(self, tm.get("update_failure"), str(exc))
            return
        QMessageBox.information(self, tm.get("update_title"), tm.get("update_staged"))
        QApplication.quit()

    def open_release_page(self) -> None:
        webbrowser.open(UPDATE_RELEASES_URL)
