import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from ...core.i18n import tm
from ..widgets import ToastWidget

logger = logging.getLogger(__name__)

def _on_progress_update(self, value: int):
    """진행률 업데이트 (오버레이 + 상태바)"""
    sender = self.sender()
    if sender is not None and sender is not self.worker:
        return  # stale signal
    self.progress_bar.setValue(value)
    self.progress_overlay.update_progress(value)

def _on_worker_cancelled(self):
    """작업 취소 처리"""
    if self.worker and self.worker.isRunning():
        self._cancel_pending = True
        if hasattr(self.worker, 'cancel'):
            self.worker.cancel()
        self.status_label.setText(tm.get("cancelling"))

def _cleanup_cancelled_worker(self):
    """취소된 작업 정리 (임시 파일 포함)"""
    if getattr(self, "_cancel_handled", False):
        return
    self.set_ui_busy(False)
    self.progress_overlay.hide_progress()
    self.status_label.setText(tm.get("cancelled"))
    self.progress_bar.setValue(0)
    self.btn_open_folder.setVisible(False)
    self._has_output = False
    self._cancel_pending = False
    self._cancel_handled = True

    # v4.4: 취소된 작업의 미완성 출력 파일 정리
    if hasattr(self, '_last_output_path') and self._last_output_path:
        output_path = self._last_output_path
        # 파일인 경우 삭제 시도
        if os.path.isfile(output_path):
            try:
                # 최근 생성된 파일만 삭제 (5초 이내)
                import time
                if time.time() - os.path.getmtime(output_path) < 5:
                    os.remove(output_path)
                    logger.info(f"Removed incomplete output file: {output_path}")
            except Exception as e:
                logger.debug(f"Could not remove cancelled output: {e}")

    toast = ToastWidget(tm.get("msg_worker_cancelled"), toast_type='warning', duration=3000)
    toast.show_toast(self)

def set_ui_busy(self, busy):
    self.tabs.setEnabled(not busy)
    self.btn_open_folder.setEnabled(not busy)

def _finalize_worker(self):
    """현재 worker의 시그널 연결을 해제하고 Qt 메모리 정리를 예약합니다."""
    if not self.worker:
        return
    try:
        self.worker.progress_signal.disconnect()
        self.worker.finished_signal.disconnect()
        self.worker.error_signal.disconnect()
        self.worker.cancelled_signal.disconnect()
    except (TypeError, RuntimeError):
        pass  # 이미 해제되었거나 연결이 없는 경우
    self.worker.deleteLater()
    self.worker = None

def _run_pending_worker(self):
    """대기 중인 작업이 있으면 자동 실행"""
    pending = getattr(self, "_pending_worker", None)
    if not pending:
        return
    if self.worker and self.worker.isRunning():
        QTimer.singleShot(200, self._run_pending_worker)
        return
    self._pending_worker = None
    QTimer.singleShot(0, lambda: self.run_worker(
        pending["mode"],
        pending.get("output_path"),
        **pending.get("kwargs", {})
    ))

def _reset_progress_if_idle(self):
    """작업이 없을 때만 진행률 초기화"""
    if self.worker and self.worker.isRunning():
        return
    self.progress_bar.setValue(0)
