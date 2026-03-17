import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm
from ...core.settings import KEYRING_AVAILABLE, get_api_key, save_settings, set_api_key
from ..main_window_config import AI_AVAILABLE, MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from ..widgets import FileSelectorWidget, ToastWidget, is_pdf_encrypted

logger = logging.getLogger(__name__)

def _save_summary_result(self):
    """요약 결과 저장"""
    text = self.txt_summary_result.toPlainText()
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_no_summary"))

    s, _ = QFileDialog.getSaveFileName(self, tm.get("dlg_save_summary"), "summary.txt", tm.get("file_filter_text"))
    if s:
        with open(s, 'w', encoding='utf-8') as f:
            f.write(text)
        toast = ToastWidget(tm.get("msg_summary_saved"), toast_type='success', duration=2000)
        toast.show_toast(self)

def action_ai_summarize(self):
    """AI 요약 실행"""
    # 오프라인 안전 체크
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), 
            tm.get("msg_ai_unavailable"))

    path = self.sel_ai_pdf.get_path()
    api_key = self.txt_api_key.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    # v4.5: 공용 함수 사용
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))

    style = self.cmb_summary_style.currentData() or "concise"
    lang = self.cmb_summary_lang.currentData() or "ko"

    max_pages = self.spn_max_pages.value()
    if max_pages == 0:
        max_pages = None


    self.txt_summary_result.clear()
    self.txt_summary_result.setPlaceholderText(tm.get("msg_ai_working"))

    # Worker 실행 (결과는 finished 시그널에서 처리)
    self._ai_worker_mode = True
    self.run_worker("ai_summarize", 
                   file_path=path, 
                   api_key=api_key,
                   language=lang,
                   style=style,
                   max_pages=max_pages)

def _ask_ai_question(self):
    """PDF 채팅 - 질문하기"""
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), tm.get("msg_ai_unavailable"))

    path = self.sel_chat_pdf.get_path()
    api_key = self.txt_api_key.text().strip()
    question = self.txt_ai_question.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    # v4.5: 공용 함수 사용
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))
    if not question:
        return

    conversation_history = list(self._chat_histories.get(path, []))
    self._record_chat_entry(path, "user", question)
    self._save_chat_histories()

    # 질문을 채팅 히스토리에 추가
    self.txt_chat_history.append(f"<b>{tm.get('chat_user_prefix')}</b> {question}")
    self.txt_chat_history.append(f"<i>{tm.get('msg_ai_thinking')}</i>")
    self.txt_ai_question.clear()

    # Worker 실행
    self._chat_worker_mode = True
    self._chat_pending_path = path
    self.run_worker("ai_ask_question",
                   file_path=path,
                   api_key=api_key,
                   question=question,
                   conversation_history=conversation_history)

def _on_chat_pdf_changed(self, path: str):
    """채팅 PDF 변경 시 미리보기 및 히스토리 동기화"""
    self._update_preview(path)
    self._load_chat_history_for_path(path)

def _load_chat_history_for_path(self, path: str):
    """선택된 PDF의 채팅 히스토리 표시"""
    if not hasattr(self, "txt_chat_history"):
        return
    self.txt_chat_history.clear()
    if not path:
        return
    history = self._chat_histories.get(path, [])
    for entry in history:
        role = entry.get("role")
        content = entry.get("content", "")
        if role == "user":
            self.txt_chat_history.append(f"<b>{tm.get('chat_user_prefix')}</b> {content}")
        elif role == "assistant":
            self.txt_chat_history.append(f"<b>{tm.get('chat_assistant_prefix')}</b> {content}")
            self.txt_chat_history.append("<hr>")

def _clear_chat_history(self):
    """채팅 히스토리 삭제"""
    path = self.sel_chat_pdf.get_path() if hasattr(self, "sel_chat_pdf") else None
    if path and path in self._chat_histories:
        del self._chat_histories[path]
        self._save_chat_histories()
    self.txt_chat_history.clear()
    toast = ToastWidget(tm.get("msg_chat_cleared"), toast_type='info', duration=2000)
    toast.show_toast(self)

def _extract_keywords(self):
    """키워드 추출"""
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), tm.get("msg_ai_unavailable"))

    path = self.sel_kw_pdf.get_path()
    api_key = self.txt_api_key.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    # v4.5: 공용 함수 사용
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))

    max_keywords = self.spn_max_keywords.value()
    lang = self.cmb_summary_lang.currentData() or "ko"

    self.lbl_keywords_result.setText(tm.get("msg_ai_thinking"))

    # Worker 실행
    self._keyword_worker_mode = True
    self.run_worker("ai_extract_keywords",
                   file_path=path,
                   api_key=api_key,
                   max_keywords=max_keywords,
                   language=lang)

def _show_thumbnail_grid(self):
    """썸네일 그리드 다이얼로그 표시"""
    path = self.sel_thumb_pdf.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    from ..thumbnail_grid import ThumbnailGridWidget

    # 다이얼로그 생성
    dialog = QDialog(self)
    dialog.setWindowTitle(tm.get("title_thumb_grid").format(os.path.basename(path)))
    dialog.resize(800, 600)

    layout = QVBoxLayout(dialog)

    # 썸네일 그리드 위젯
    thumbnail_grid = ThumbnailGridWidget()
    thumbnail_grid.pageSelected.connect(lambda pg: self._on_grid_page_selected(pg, dialog))
    layout.addWidget(thumbnail_grid)

    # 닫기 버튼
    btn_close = QPushButton(tm.get("close"))
    btn_close.clicked.connect(dialog.accept)
    layout.addWidget(btn_close)

    # PDF 로드
    thumbnail_grid.load_pdf(path)

    dialog.exec()

def _on_grid_page_selected(self, page_index: int, dialog: QDialog):
    """그리드에서 페이지 선택 시"""
    self._current_preview_page = page_index
    self._render_preview_page()
    self.status_label.setText(tm.get("status_page_sel").format(page_index + 1))
