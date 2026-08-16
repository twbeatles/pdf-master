"""User-facing, single-flight signed-update flow."""
from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, cast

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from ..core.constants import UPDATE_MANIFEST_URL, UPDATE_PUBLIC_KEY_B64, UPDATE_RELEASES_URL, VERSION
from ..core.i18n import tm
from ..core.update_installer import consume_update_result, launch_update_helper, stage_update
from ..core.update_manifest import NoUpdateAvailableError, ReleaseManifest, download_release_manifest, verify_release_manifest

logger = logging.getLogger(__name__)


class _UpdateSignals(QObject):
    ready = pyqtSignal(object); current = pyqtSignal(); failed = pyqtSignal(str); staged = pyqtSignal(object); progress = pyqtSignal(int)


class UpdateMixin:
    def _initialize_updates(self) -> None:
        self._update_state = "idle"
        self._update_signals = _UpdateSignals(self)
        self._update_signals.ready.connect(self._offer_update)
        self._update_signals.current.connect(lambda: QMessageBox.information(self, tm.get("update_title"), tm.get("update_current")))
        self._update_signals.failed.connect(self._show_update_failure)
        self._update_signals.staged.connect(self._apply_staged_update)
        self._update_signals.progress.connect(self._show_update_progress)
        QTimer.singleShot(0, self._show_previous_update_result)
        if sys.platform == "win32": QTimer.singleShot(2000, lambda: self.check_for_updates(silent=True))

    def _show_previous_update_result(self) -> None:
        result = consume_update_result()
        if not result or result.get("status") == "applied": return
        QMessageBox.warning(self, tm.get("update_failure"), str(result.get("error") or tm.get("update_recovered")))

    def check_for_updates(self, silent: bool = False) -> None:
        if sys.platform != "win32" or self._update_state != "idle": return
        self._update_state = "checking"
        def worker() -> None:
            try:
                manifest = verify_release_manifest(download_release_manifest(UPDATE_MANIFEST_URL), public_key=UPDATE_PUBLIC_KEY_B64, current_version=VERSION)
            except NoUpdateAvailableError:
                self._update_state = "idle"
                if not silent: self._update_signals.current.emit()
            except Exception as exc:
                logger.warning("Update check failed", exc_info=True); self._update_state = "idle"
                if not silent: self._update_signals.failed.emit(str(exc))
            else: self._update_signals.ready.emit(manifest)
        threading.Thread(target=worker, name="PDFMasterUpdateCheck", daemon=True).start()

    def _offer_update(self, raw_manifest: object) -> None:
        if not isinstance(raw_manifest, ReleaseManifest):
            self._update_state = "idle"; return
        manifest = raw_manifest
        if self._update_state != "checking": return
        if not getattr(sys, "frozen", False):
            self._update_state = "idle"; QMessageBox.information(self, tm.get("update_title"), tm.get("update_dev_available", manifest.version)); return
        if QMessageBox.question(self, tm.get("update_found"), tm.get("update_offer", manifest.version), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            self._update_state = "idle"; return
        self._update_state = "downloading"
        threading.Thread(target=self._download_update, args=(manifest,), name="PDFMasterUpdateDownload", daemon=True).start()

    def _download_update(self, manifest: ReleaseManifest) -> None:
        try: self._update_signals.staged.emit(stage_update(manifest, self._update_signals.progress.emit))
        except Exception as exc:
            logger.warning("Update download failed", exc_info=True); self._update_state = "idle"; self._update_signals.failed.emit(str(exc))

    def _show_update_progress(self, value: int) -> None:
        status_label = getattr(cast(Any, self), "status_label", None)
        if status_label is not None: status_label.setText(f"{tm.get('update_downloading')} {value}%")

    def _apply_staged_update(self, staged: object) -> None:
        if self._update_state != "downloading" or not isinstance(staged, Path): return
        try: launch_update_helper(target=Path(sys.executable).resolve(), staged=staged)
        except Exception as exc: self._update_state = "idle"; self._show_update_failure(str(exc)); return
        self._update_state = "applying"; QMessageBox.information(self, tm.get("update_title"), tm.get("update_staged")); QApplication.quit()

    def _show_update_failure(self, error: str) -> None:
        QMessageBox.warning(self, tm.get("update_failure"), error)

    def open_release_page(self) -> None:
        webbrowser.open(UPDATE_RELEASES_URL)
