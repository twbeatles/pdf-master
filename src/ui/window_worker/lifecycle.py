import logging
import os
import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from ...core.i18n import tm
from ...core.worker_runtime import get_operation_spec
from ..widgets import ToastWidget

logger = logging.getLogger(__name__)


def _collect_worker_input_paths(worker) -> set[str]:
    if worker is None:
        return set()

    kwargs = getattr(worker, "kwargs", {})
    if not isinstance(kwargs, dict):
        return set()

    input_paths: set[str] = set()
    path_keys = ("file_path", "file_path1", "file_path2", "source_path", "replace_path")
    list_keys = ("file_paths", "files")

    for key in path_keys:
        value = kwargs.get(key)
        if isinstance(value, str) and value:
            input_paths.add(os.path.abspath(value))

    for key in list_keys:
        value = kwargs.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    input_paths.add(os.path.abspath(item))

    return input_paths

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
    worker = getattr(self, "worker", None)
    spec = get_operation_spec(getattr(worker, "mode", "")) if worker else None
    cleanup_policy = spec.cancel_cleanup if spec is not None else "created_outputs"
    created_paths = getattr(worker, "kwargs", {}).get("created_output_paths", []) if worker else []
    if not isinstance(created_paths, list):
        created_paths = []
    created_paths_abs = {os.path.abspath(str(path)) for path in created_paths if isinstance(path, str) and path}
    input_paths_abs = _collect_worker_input_paths(worker)

    # v4.4: 취소된 작업의 미완성 출력 파일 정리
    if cleanup_policy != "none" and hasattr(self, '_last_output_path') and self._last_output_path:
        output_path = self._last_output_path
        if os.path.isdir(output_path) and cleanup_policy == "created_outputs":
            output_dir_abs = os.path.abspath(output_path)
            for created_path_abs in created_paths_abs:
                try:
                    if not os.path.isfile(created_path_abs):
                        continue
                    if os.path.commonpath([output_dir_abs, created_path_abs]) != output_dir_abs:
                        continue
                    os.remove(created_path_abs)
                    logger.info("Removed cancelled output file: %s", created_path_abs)
                except Exception as e:
                    logger.debug(f"Could not remove cancelled output: {e}")
        elif os.path.isfile(output_path):
            output_path_abs = os.path.abspath(output_path)
            should_remove = False
            if output_path_abs in input_paths_abs or getattr(self, "_last_output_existed", False):
                logger.info("Keeping cancelled output path because it pre-existed or is an input: %s", output_path_abs)
            else:
                should_remove = output_path_abs in created_paths_abs
                if not should_remove:
                    try:
                        should_remove = time.time() - os.path.getmtime(output_path_abs) < 5
                    except Exception:
                        should_remove = False
            try:
                if should_remove and os.path.isfile(output_path_abs):
                    os.remove(output_path_abs)
                    logger.info(f"Removed incomplete output file: {output_path_abs}")
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
