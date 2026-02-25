import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from ..core.i18n import tm
from ..core.worker import WorkerThread
from .widgets import ToastWidget

logger = logging.getLogger(__name__)


class MainWindowWorkerMixin:

    def run_worker(self, mode, output_path=None, **kwargs):
        """작업 스레드 실행 (안전한 동시 작업 처리)"""
        # 이전 Worker가 실행 중인지 확인
        if self.worker and self.worker.isRunning():
            result = QMessageBox.question(
                self, tm.get("task_in_progress"),
                tm.get("task_wait_or_cancel"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.Yes:
                self._pending_worker = {
                    "mode": mode,
                    "output_path": output_path,
                    "kwargs": dict(kwargs),
                }
                toast = ToastWidget(tm.get("msg_worker_queued"), toast_type='info', duration=2000)
                toast.show_toast(self)
                return
            return  # 새 작업 취소

        # 이전 Worker 정리 (v4.5: 강화된 정리)
        if self.worker:
            # 실행 중이면 잠시 대기
            if self.worker.isRunning():
                self.worker.wait(500)
            self._finalize_worker()

        self._pending_worker = None
        self._cancel_pending = False
        self._cancel_handled = False
        
        # output_path 추적 (폴더 열기 기능용)
        if output_path:
            self._last_output_path = output_path
            self._has_output = True
            kwargs['output_path'] = output_path
        elif kwargs.get('output_path'):
            self._last_output_path = kwargs['output_path']
            self._has_output = True
        elif kwargs.get('output_dir'):
            self._last_output_path = kwargs['output_dir']
            self._has_output = True
        else:
            self._last_output_path = None
            self._has_output = False
        
        # 작업 모드에 따른 설명 (Undo에서도 사용)
        mode_descriptions = {
            "merge": tm.get("action_merge"),
            "convert_to_img": tm.get("action_convert_to_img"),
            "images_to_pdf": tm.get("action_images_to_pdf"),
            "extract_text": tm.get("action_extract_text"),
            "split": tm.get("action_split"),
            "delete_pages": tm.get("action_delete_pages"),
            "rotate": tm.get("action_rotate"),
            "add_page_numbers": tm.get("action_add_page_numbers"),
            "watermark": tm.get("action_watermark"),
            "image_watermark": tm.get("mode_image_watermark"),
            "protect": tm.get("action_encrypt"),
            "compress": tm.get("action_compress"),
            "metadata_update": tm.get("mode_metadata_update"),
            "reorder": tm.get("mode_reorder"),
            "batch": tm.get("mode_batch"),
            "split_by_pages": tm.get("mode_split_by_pages"),
            "resize_pages": tm.get("mode_resize_pages"),
            "add_stamp": tm.get("mode_add_stamp"),
            "crop_pdf": tm.get("mode_crop_pdf"),
            "insert_textbox": tm.get("mode_insert_textbox"),
            "draw_shapes": tm.get("mode_draw_shapes"),
            "add_link": tm.get("mode_add_link"),
            "copy_page_between_docs": tm.get("mode_copy_pages"),
            "insert_signature": tm.get("mode_insert_signature"),
            "add_freehand_signature": tm.get("mode_add_freehand_signature"),
            "add_sticky_note": tm.get("mode_add_sticky_note"),
            "add_ink_annotation": tm.get("mode_add_ink"),
            "add_text_markup": tm.get("mode_add_text_markup"),
            "add_background": tm.get("mode_add_background"),
            "add_attachment": tm.get("mode_add_attachment"),
            "list_attachments": tm.get("mode_list_attachments"),
            "extract_attachments": tm.get("mode_extract_attachments"),
            "get_form_fields": tm.get("mode_get_form_fields"),
            "fill_form": tm.get("mode_fill_form"),
            "list_annotations": tm.get("mode_list_annotations"),
            "remove_annotations": tm.get("mode_remove_annotations"),
            "extract_images": tm.get("mode_extract_images"),
            "extract_links": tm.get("mode_extract_links"),
            "extract_tables": tm.get("mode_extract_tables"),
            "extract_markdown": tm.get("mode_extract_markdown"),
            "search_text": tm.get("mode_search_text"),
            "highlight_text": tm.get("mode_highlight_text"),
            "get_pdf_info": tm.get("mode_get_pdf_info"),
            "get_bookmarks": tm.get("mode_get_bookmarks"),
            "decrypt_pdf": tm.get("mode_decrypt_pdf"),
            "compare_pdfs": tm.get("mode_compare_pdfs"),
            "ai_summarize": tm.get("mode_ai_summarize"),
            "ai_ask_question": tm.get("mode_ai_ask"),
            "ai_extract_keywords": tm.get("mode_ai_keywords"),
        }
        
        # v4.3: Undo 지원 작업 - 백업 생성
        self._pending_undo = None  # 초기화
        # v4.5: Undo 지원 모드 확장
        undo_supported_modes = [
            'delete_pages', 'rotate', 'add_page_numbers', 'watermark', 'compress',
            'add_stamp', 'image_watermark', 'crop_pdf', 'insert_textbox', 'draw_shapes',
            'reorder', 'reverse_pages', 'duplicate_page', 'insert_blank_page',
            'add_link', 'add_background', 'add_text_markup'
        ]
        if mode in undo_supported_modes:
            source = kwargs.get('file_path', '')
            output = kwargs.get('output_path', '')
            if source and output:
                backup = self._create_backup_for_undo(source)
                if backup:
                    self._pending_undo = {
                        'action_type': mode,
                        'description': mode_descriptions.get(mode, mode),
                        'backup_path': backup,
                        'source_path': source,
                        'output_path': output
                    }
        
        description = mode_descriptions.get(mode, tm.get("processing_plain")) + "..."
        
        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.worker.cancelled_signal.connect(self.on_cancelled)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText(tm.get("processing_status"))
        self.set_ui_busy(True)
        
        # 진행 오버레이 표시 (개선된 UX)
        self.progress_overlay.show_progress(tm.get("processing"), description)
        
        self.worker.start()

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

    def on_cancelled(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return  # stale signal

        # v4.5: AI 모드 플래그 초기화 (취소 시에도 정상 초기화)
        if hasattr(self, '_ai_worker_mode'):
            self._ai_worker_mode = False
        if hasattr(self, '_keyword_worker_mode'):
            self._keyword_worker_mode = False
        if hasattr(self, '_chat_worker_mode'):
            self._chat_worker_mode = False
            self._chat_pending_path = None

        self._cleanup_cancelled_worker()
        self._finalize_worker()
        self._run_pending_worker()
        QTimer.singleShot(3000, self._reset_progress_if_idle)

    def on_success(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return  # stale signal

        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()  # 오버레이 숨기기
        self.status_label.setText(tm.get("completed"))
        self.progress_bar.setValue(100)
        self.btn_open_folder.setVisible(bool(getattr(self, "_has_output", False) and self._last_output_path))
        
        # v4.0: AI 요약 결과 처리
        if hasattr(self, '_ai_worker_mode') and self._ai_worker_mode:
            self._ai_worker_mode = False
            if self.worker and hasattr(self.worker, 'kwargs'):
                summary = self.worker.kwargs.get('summary_result', '')
                if summary and hasattr(self, 'txt_summary_result'):
                    self.txt_summary_result.setPlainText(summary)
        
        # v4.5: AI 채팅 답변 처리
        if hasattr(self, '_chat_worker_mode') and self._chat_worker_mode:
            self._chat_worker_mode = False
            if self.worker and hasattr(self.worker, 'kwargs'):
                answer = self.worker.kwargs.get('answer_result', '')
                if answer:
                    pending_path = self._chat_pending_path
                    if pending_path:
                        self._record_chat_entry(pending_path, "assistant", answer)
                        self._save_chat_histories()
                    if hasattr(self, 'txt_chat_history') and pending_path == self.sel_chat_pdf.get_path():
                        # "AI가 답변 생성 중..." 메시지 제거 (마지막 줄)
                        cursor = self.txt_chat_history.textCursor()
                        cursor.movePosition(cursor.MoveOperation.End)
                        cursor.select(cursor.SelectionType.BlockUnderCursor)
                        cursor.removeSelectedText()
                        cursor.deletePreviousChar()
                        # 답변 추가
                        self.txt_chat_history.append(f"<b>{tm.get('chat_assistant_prefix')}</b> {answer}")
                        self.txt_chat_history.append("<hr>")
                self._chat_pending_path = None
        
        # v4.5: 키워드 추출 결과 처리
        if hasattr(self, '_keyword_worker_mode') and self._keyword_worker_mode:
            self._keyword_worker_mode = False
            if self.worker and hasattr(self.worker, 'kwargs'):
                keywords = self.worker.kwargs.get('keywords_result', [])
                if keywords and hasattr(self, 'lbl_keywords_result'):
                    # 태그 형태로 키워드 표시
                    keyword_tags = " • ".join(keywords)
                    self.lbl_keywords_result.setText(keyword_tags)
                else:
                    self.lbl_keywords_result.setText(tm.get("msg_no_keywords"))
        
        # v4.3: Undo 등록 (파일 수정 작업)
        if hasattr(self, '_pending_undo') and self._pending_undo:
            undo_info = self._pending_undo
            self._pending_undo = None  # 소비
            
            before_state = {
                "backup_path": undo_info['backup_path'],
                "target_path": undo_info['output_path']
            }
            after_state = {
                "output_path": undo_info['output_path'],
                "target_path": undo_info['output_path']
            }
            
            self.undo_manager.push(
                action_type=undo_info['action_type'],
                description=undo_info['description'],
                before_state=before_state,
                after_state=after_state,
                undo_callback=self._restore_from_backup,
                redo_callback=self._redo_from_output
            )
            logger.info(f"Registered undo for: {undo_info['action_type']}")
        
        custom_dialog_shown = False
        if self.worker and hasattr(self.worker, "kwargs"):
            mode = getattr(self.worker, "mode", "")
            if mode == "get_form_fields" and hasattr(self, "form_fields_list"):
                fields = self.worker.kwargs.get("result_fields", []) or []
                self.form_fields_list.clear()
                self._form_field_data = {}
                from PyQt6.QtCore import Qt
                from PyQt6.QtWidgets import QListWidgetItem
                for field in fields:
                    name = field.get("name", f"field_{self.form_fields_list.count()}")
                    value = field.get("value", "")
                    item = QListWidgetItem(f"📋 {name}: {value}")
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    item.setToolTip(tm.get("msg_field_tooltip", field.get("type", "-"), field.get("page", 0)))
                    self.form_fields_list.addItem(item)
                    self._form_field_data[name] = value
                if not fields:
                    QMessageBox.information(self, tm.get("info"), tm.get("msg_no_form_fields"))
                else:
                    toast = ToastWidget(tm.get("msg_form_fields_detected", len(fields)), toast_type='success', duration=2000)
                    toast.show_toast(self)
                custom_dialog_shown = True
            elif mode == "list_attachments":
                attachments = self.worker.kwargs.get("result_attachments", []) or []
                if not attachments:
                    QMessageBox.information(self, tm.get("info"), tm.get("msg_no_attachments"))
                else:
                    rows = [
                        tm.get("msg_attachment_row", att.get("name", "Unknown"), att.get("size", 0))
                        for att in attachments
                    ]
                    QMessageBox.information(
                        self,
                        tm.get("title_attachment_list"),
                        tm.get("msg_attachment_list_body", len(attachments), "\n".join(rows)),
                    )
                custom_dialog_shown = True

        # Toast 알림 표시
        toast = ToastWidget(tm.get("completed"), toast_type='success', duration=4000)
        toast.show_toast(self)

        if not custom_dialog_shown:
            QMessageBox.information(self, tm.get("info"), msg)
        self._finalize_worker()
        self._run_pending_worker()
        QTimer.singleShot(3000, self._reset_progress_if_idle)

    def on_fail(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return  # stale signal

        # v4.5: AI 모드 플래그 초기화 (에러 시에도 정상 초기화)
        if hasattr(self, '_ai_worker_mode'):
            self._ai_worker_mode = False
        if hasattr(self, '_keyword_worker_mode'):
            self._keyword_worker_mode = False

        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()  # 오버레이 숨기기
        self.status_label.setText(tm.get("error"))
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        
        if hasattr(self, '_chat_worker_mode') and self._chat_worker_mode:
            self._chat_worker_mode = False
            pending_path = self._chat_pending_path
            self._chat_pending_path = None
            if pending_path and pending_path in self._chat_histories:
                history = self._chat_histories.get(pending_path, [])
                if history and history[-1].get("role") == "user":
                    history.pop()
                    if not history:
                        del self._chat_histories[pending_path]
                    self._save_chat_histories()
            if hasattr(self, 'txt_chat_history'):
                cursor = self.txt_chat_history.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
                self.txt_chat_history.append(f"<span style='color:#ef4444'>❌ {msg}</span>")
        
        # Toast 알림 표시
        toast = ToastWidget(tm.get("error"), toast_type='error', duration=5000)
        toast.show_toast(self)
        
        QMessageBox.critical(self, tm.get("error"), tm.get("msg_worker_error", msg))
        self._finalize_worker()
        self._run_pending_worker()

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

    # ===================== Undo/Redo 헬퍼 =====================
