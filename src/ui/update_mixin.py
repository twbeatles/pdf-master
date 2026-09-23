"""User-facing, single-flight signed-update flow."""
from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from ..core.constants import UPDATE_MANIFEST_URL, UPDATE_PUBLIC_KEY_B64, UPDATE_RELEASES_URL, VERSION
from ..core.i18n import tm
from ..core.update_installer import consume_update_result, launch_update_helper
from ..core.update_manifest import (
    NoUpdateAvailableError,
    ReleaseManifest,
    days_until_expiry,
    manifest_expiry_status,
)
from ..core.update_service import check_for_update, download_update

logger = logging.getLogger(__name__)

#: 조용한 자동 확인 실패 후 1회 자동 재시도까지 대기 (ms). PROJECT_AUDIT.md §5 Gap 대응.
SILENT_CHECK_RETRY_DELAY_MS = 5 * 60 * 1000


class _UpdateSignals(QObject):
    ready = pyqtSignal(object); current = pyqtSignal(); failed = pyqtSignal(str); staged = pyqtSignal(object); progress = pyqtSignal(int)
    notice = pyqtSignal(str)


class UpdateMixin:
    def _initialize_updates(self) -> None:
        self._update_state = "idle"
        self._last_update_check_error: str | None = None
        self._last_update_check_at: datetime | None = None
        self._update_auto_retry_scheduled = False
        self._update_signals = _UpdateSignals(self)
        self._update_signals.ready.connect(self._offer_update)
        self._update_signals.current.connect(self._show_update_current)
        self._update_signals.failed.connect(self._show_update_failure)
        self._update_signals.staged.connect(self._apply_staged_update)
        self._update_signals.progress.connect(self._show_update_progress)
        self._update_signals.notice.connect(self._show_update_notice)
        QTimer.singleShot(0, self._show_previous_update_result)
        if sys.platform == "win32": QTimer.singleShot(2000, lambda: self.check_for_updates(silent=True))

    def _show_previous_update_result(self) -> None:
        result = consume_update_result()
        if not result or result.get("status") == "applied": return
        QMessageBox.warning(self, tm.get("update_failure"), str(result.get("error") or tm.get("update_recovered")))

    def _show_update_current(self) -> None:
        message = tm.get("update_current")
        if self._last_update_check_error:
            message += "\n" + tm.get("update_last_error", self._last_update_check_error)
        QMessageBox.information(self, tm.get("update_title"), message)

    def _show_update_notice(self, text: str) -> None:
        status_label = getattr(cast(Any, self), "status_label", None)
        if status_label is not None:
            try: status_label.setText(text)
            except RuntimeError: pass

    def _handle_check_no_update(self, silent: bool) -> str:
        self._update_state = "idle"
        if not silent: self._update_signals.current.emit()
        return "current"

    def _handle_check_failure(self, exc: BaseException, silent: bool) -> str:
        logger.warning("Update check failed", exc_info=True)
        self._last_update_check_error = str(exc) or repr(exc)
        self._last_update_check_at = datetime.now(timezone.utc)
        self._update_state = "idle"
        if silent:
            self._update_signals.notice.emit(tm.get("update_check_failed_hint"))
            self._schedule_silent_check_retry()
        else:
            self._update_signals.failed.emit(str(exc))
        return "failed"

    def _handle_check_ready(self, manifest: ReleaseManifest) -> str:
        self._update_signals.ready.emit(manifest)
        return "ready"

    def _schedule_silent_check_retry(self) -> None:
        """조용한 실패 후 1회만 자동 재시도 예약 (매 기동 폭주 방지)."""
        if getattr(self, "_update_auto_retry_scheduled", False):
            return
        self._update_auto_retry_scheduled = True
        QTimer.singleShot(SILENT_CHECK_RETRY_DELAY_MS, self._retry_silent_update_check)

    def _retry_silent_update_check(self) -> None:
        self._update_auto_retry_scheduled = False
        if sys.platform != "win32" or getattr(self, "_update_state", "idle") != "idle":
            return
        self.check_for_updates(silent=True)

    def check_for_updates(self, silent: bool = False) -> None:
        if sys.platform != "win32":
            if not silent: self._update_signals.failed.emit(tm.get("update_not_supported"))
            return
        if self._update_state != "idle": return
        self._update_state = "checking"
        def worker() -> None:
            try:
                manifest = check_for_update(
                    manifest_url=UPDATE_MANIFEST_URL,
                    public_key=UPDATE_PUBLIC_KEY_B64,
                    current_version=VERSION,
                )
            except NoUpdateAvailableError:
                self._handle_check_no_update(silent)
            except Exception as exc:
                self._handle_check_failure(exc, silent)
            else:
                self._handle_check_ready(manifest)
        threading.Thread(target=worker, name="PDFMasterUpdateCheck", daemon=True).start()

    def _offer_update(self, raw_manifest: object) -> None:
        if not isinstance(raw_manifest, ReleaseManifest):
            self._update_state = "idle"; return
        manifest = raw_manifest
        if self._update_state != "checking": return
        # 새 매니페스트 수신 성공 → 이전 실패 기록 초기화
        self._last_update_check_error = None
        self._last_update_check_at = None
        offer = tm.get("update_offer", manifest.version)
        if manifest_expiry_status(manifest.expires_at) == "expiring_soon":
            offer += "\n" + tm.get("update_expires_soon", days_until_expiry(manifest.expires_at))
        if not getattr(sys, "frozen", False):
            self._update_state = "idle"; QMessageBox.information(self, tm.get("update_title"), tm.get("update_dev_available", manifest.version)); return
        if QMessageBox.question(self, tm.get("update_found"), offer, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            self._update_state = "idle"; return
        self._update_state = "downloading"
        threading.Thread(target=self._download_update, args=(manifest,), name="PDFMasterUpdateDownload", daemon=True).start()

    def _download_update(self, manifest: ReleaseManifest) -> None:
        try: self._update_signals.staged.emit(download_update(manifest, self._update_signals.progress.emit))
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
