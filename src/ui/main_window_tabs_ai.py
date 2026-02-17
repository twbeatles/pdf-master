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

from ..core.i18n import tm
from ..core.settings import save_settings
from .main_window_config import AI_AVAILABLE, MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from .thumbnail_grid import ThumbnailGridWidget
from .widgets import FileSelectorWidget, ToastWidget, is_pdf_encrypted

logger = logging.getLogger(__name__)


class MainWindowTabsAiMixin:

    def _load_chat_histories(self):
        """저장된 채팅 히스토리 로드"""
        raw = self.settings.get("chat_histories", {})
        if not isinstance(raw, dict):
            return {}
        cleaned = {}
        for path, entries in raw.items():
            if not isinstance(path, str) or not isinstance(entries, list):
                continue
            cleaned_entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                role = entry.get("role")
                content = entry.get("content")
                if role in ("user", "assistant") and isinstance(content, str) and content:
                    cleaned_entries.append({"role": role, "content": content})
            if cleaned_entries:
                cleaned[path] = cleaned_entries[-MAX_CHAT_HISTORY_ENTRIES:]
        if len(cleaned) > MAX_CHAT_HISTORY_PDFS:
            cleaned = dict(list(cleaned.items())[-MAX_CHAT_HISTORY_PDFS:])
        return cleaned

    def _trim_chat_histories(self):
        """채팅 히스토리 크기 제한"""
        for path, entries in list(self._chat_histories.items()):
            if not isinstance(entries, list) or not entries:
                del self._chat_histories[path]
                continue
            if len(entries) > MAX_CHAT_HISTORY_ENTRIES:
                self._chat_histories[path] = entries[-MAX_CHAT_HISTORY_ENTRIES:]
        if len(self._chat_histories) > MAX_CHAT_HISTORY_PDFS:
            self._chat_histories = dict(list(self._chat_histories.items())[-MAX_CHAT_HISTORY_PDFS:])

    def _save_chat_histories(self):
        """채팅 히스토리 저장"""
        self._trim_chat_histories()
        self.settings["chat_histories"] = self._chat_histories
        save_settings(self.settings)

    def _record_chat_entry(self, path: str, role: str, content: str):
        """채팅 기록 추가"""
        if not path or not content:
            return
        history = self._chat_histories.pop(path, [])
        history.append({"role": role, "content": content})
        self._chat_histories[path] = history
        self._trim_chat_histories()

    def setup_ai_tab(self):
        """AI 요약 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # AI 요약 섹션
        grp_summary = QGroupBox(tm.get("grp_ai_summary"))
        l_summary = QVBoxLayout(grp_summary)
        
        # ⚠️ AI 패키지 미설치 경고 배너
        if not AI_AVAILABLE:
            ai_warning = QLabel(tm.get("msg_ai_unavailable"))
            ai_warning.setStyleSheet("""
                QLabel {
                    background-color: #3a1a1a;
                    color: #ff6b6b;
                    padding: 15px;
                    border: 2px solid #ff6b6b;
                    border-radius: 8px;
                    font-size: 12px;
                }
            """)
            ai_warning.setWordWrap(True)
            ai_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l_summary.addWidget(ai_warning)
            l_summary.addWidget(QLabel(""))  # 간격
        
        # API 키 설정
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel(tm.get("lbl_api_key")))
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText(tm.get("ph_api_key"))
        self.txt_api_key.setEnabled(AI_AVAILABLE)
        saved_key = self.settings.get("gemini_api_key", "")
        if saved_key:
            self.txt_api_key.setText(saved_key)
        api_layout.addWidget(self.txt_api_key)
        
        btn_save_key = QPushButton(tm.get("btn_save_key"))
        btn_save_key.setFixedWidth(70)
        btn_save_key.setEnabled(AI_AVAILABLE)
        btn_save_key.clicked.connect(self._save_api_key)
        api_layout.addWidget(btn_save_key)
        
        l_summary.addLayout(api_layout)
        
        # API 키 안내
        api_hint = QLabel(tm.get("msg_api_hint"))
        api_hint.setOpenExternalLinks(True)
        api_hint.setStyleSheet("color: #888; font-size: 11px;")
        l_summary.addWidget(api_hint)
        
        l_summary.addWidget(QLabel(""))  # 간격
        
        # PDF 파일 선택
        step1 = QLabel(tm.get("step_ai_1"))
        step1.setObjectName("stepLabel")
        l_summary.addWidget(step1)
        
        self.sel_ai_pdf = FileSelectorWidget(tm.get("lbl_ai_file"), ['.pdf'])
        self.sel_ai_pdf.pathChanged.connect(self._update_preview)
        l_summary.addWidget(self.sel_ai_pdf)
        
        # 요약 옵션
        step2 = QLabel(tm.get("step_ai_2"))
        step2.setObjectName("stepLabel")
        l_summary.addWidget(step2)
        
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel(tm.get("lbl_ai_style")))
        self.cmb_summary_style = QComboBox()
        summary_styles = [
            (tm.get("style_concise"), "concise"),
            (tm.get("style_detailed"), "detailed"),
            (tm.get("style_bullet"), "bullet"),
        ]
        for label, value in summary_styles:
            self.cmb_summary_style.addItem(label, value)
        self.cmb_summary_style.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.cmb_summary_style)
        
        opt_layout.addWidget(QLabel(tm.get("lbl_ai_lang")))
        self.cmb_summary_lang = QComboBox()
        summary_langs = [
            (tm.get("lang_ko"), "ko"),
            (tm.get("lang_en"), "en"),
        ]
        for label, value in summary_langs:
            self.cmb_summary_lang.addItem(label, value)
        self.cmb_summary_lang.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.cmb_summary_lang)
        
        opt_layout.addWidget(QLabel(tm.get("lbl_max_pages")))
        self.spn_max_pages = QSpinBox()
        self.spn_max_pages.setRange(0, 100)
        self.spn_max_pages.setValue(0)
        self.spn_max_pages.setToolTip(tm.get("tooltip_max_pages"))
        self.spn_max_pages.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.spn_max_pages)
        
        opt_layout.addStretch()
        l_summary.addLayout(opt_layout)
        
        # 요약 실행 버튼
        self.btn_ai_summarize = QPushButton(tm.get("btn_ai_run"))
        self.btn_ai_summarize.setObjectName("actionBtn")
        self.btn_ai_summarize.setEnabled(AI_AVAILABLE)
        self.btn_ai_summarize.clicked.connect(self.action_ai_summarize)
        if not AI_AVAILABLE:
            self.btn_ai_summarize.setToolTip(tm.get("tooltip_ai_unavailable"))
        l_summary.addWidget(self.btn_ai_summarize)
        
        # 요약 결과 표시
        step3 = QLabel(tm.get("step_ai_3"))
        step3.setObjectName("stepLabel")
        l_summary.addWidget(step3)
        
        self.txt_summary_result = QTextEdit()
        self.txt_summary_result.setPlaceholderText(tm.get("ph_ai_result") if AI_AVAILABLE else tm.get("msg_ai_disabled"))
        self.txt_summary_result.setMinimumHeight(200)
        self.txt_summary_result.setReadOnly(True)
        l_summary.addWidget(self.txt_summary_result)
        
        # 저장 버튼
        btn_save_summary = QPushButton(tm.get("btn_save_summary"))
        btn_save_summary.setObjectName("secondaryBtn")
        btn_save_summary.clicked.connect(self._save_summary_result)
        l_summary.addWidget(btn_save_summary)
        
        content_layout.addWidget(grp_summary)
        
        # 페이지 썸네일 그리드 섹션
        grp_thumb = QGroupBox(tm.get("grp_thumb"))
        l_thumb = QVBoxLayout(grp_thumb)
        
        thumb_desc = QLabel(tm.get("desc_thumb"))
        thumb_desc.setObjectName("desc")
        l_thumb.addWidget(thumb_desc)
        
        self.sel_thumb_pdf = FileSelectorWidget(tm.get("lbl_thumb_file"), ['.pdf'])
        l_thumb.addWidget(self.sel_thumb_pdf)
        
        btn_show_grid = QPushButton(tm.get("btn_show_grid"))
        btn_show_grid.setObjectName("actionBtn")
        btn_show_grid.clicked.connect(self._show_thumbnail_grid)
        l_thumb.addWidget(btn_show_grid)
        
        content_layout.addWidget(grp_thumb)
        
        # v4.5: PDF 채팅 섹션
        grp_chat = QGroupBox(tm.get("grp_ai_chat"))
        l_chat = QVBoxLayout(grp_chat)
        
        chat_step = QLabel(tm.get("step_ai_chat"))
        chat_step.setObjectName("stepLabel")
        l_chat.addWidget(chat_step)
        
        # PDF 파일 선택 (채팅용)
        self.sel_chat_pdf = FileSelectorWidget(tm.get("lbl_ai_file"), ['.pdf'])
        self.sel_chat_pdf.pathChanged.connect(self._on_chat_pdf_changed)
        l_chat.addWidget(self.sel_chat_pdf)
        
        # 질문 입력
        q_layout = QHBoxLayout()
        self.txt_ai_question = QLineEdit()
        self.txt_ai_question.setPlaceholderText(tm.get("ph_ai_question"))
        self.txt_ai_question.setEnabled(AI_AVAILABLE)
        self.txt_ai_question.returnPressed.connect(self._ask_ai_question)
        q_layout.addWidget(self.txt_ai_question)
        
        self.btn_ask_ai = QPushButton(tm.get("btn_ask_ai"))
        self.btn_ask_ai.setObjectName("actionBtn")
        self.btn_ask_ai.setEnabled(AI_AVAILABLE)
        self.btn_ask_ai.setFixedWidth(100)
        self.btn_ask_ai.clicked.connect(self._ask_ai_question)
        q_layout.addWidget(self.btn_ask_ai)
        l_chat.addLayout(q_layout)
        
        # 대화 히스토리
        l_chat.addWidget(QLabel(tm.get("lbl_chat_history")))
        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setPlaceholderText("...")
        self.txt_chat_history.setMinimumHeight(150)
        self.txt_chat_history.setReadOnly(True)
        l_chat.addWidget(self.txt_chat_history)
        
        # 대화 삭제 버튼
        btn_clear_chat = QPushButton(tm.get("btn_clear_chat"))
        btn_clear_chat.setObjectName("secondaryBtn")
        btn_clear_chat.clicked.connect(self._clear_chat_history)
        l_chat.addWidget(btn_clear_chat)
        
        content_layout.addWidget(grp_chat)
        
        # v4.5: 키워드 추출 섹션
        grp_keywords = QGroupBox(tm.get("grp_keywords"))
        l_keywords = QVBoxLayout(grp_keywords)
        
        # PDF 파일 선택 (키워드용)
        self.sel_kw_pdf = FileSelectorWidget(tm.get("lbl_ai_file"), ['.pdf'])
        self.sel_kw_pdf.pathChanged.connect(self._update_preview)
        l_keywords.addWidget(self.sel_kw_pdf)
        
        kw_opt_layout = QHBoxLayout()
        kw_opt_layout.addWidget(QLabel(tm.get("lbl_max_keywords")))
        self.spn_max_keywords = QSpinBox()
        self.spn_max_keywords.setRange(3, 20)
        self.spn_max_keywords.setValue(10)
        self.spn_max_keywords.setEnabled(AI_AVAILABLE)
        kw_opt_layout.addWidget(self.spn_max_keywords)
        kw_opt_layout.addStretch()
        l_keywords.addLayout(kw_opt_layout)
        
        self.btn_extract_keywords = QPushButton(tm.get("btn_extract_keywords"))
        self.btn_extract_keywords.setObjectName("actionBtn")
        self.btn_extract_keywords.setEnabled(AI_AVAILABLE)
        self.btn_extract_keywords.clicked.connect(self._extract_keywords)
        l_keywords.addWidget(self.btn_extract_keywords)
        
        # 키워드 결과
        l_keywords.addWidget(QLabel(tm.get("lbl_keywords_result")))
        self.lbl_keywords_result = QLabel("")
        self.lbl_keywords_result.setWordWrap(True)
        self.lbl_keywords_result.setStyleSheet("""
            QLabel {
                background: rgba(79, 140, 255, 0.1);
                border: 1px solid #4f8cff;
                border-radius: 8px;
                padding: 10px;
                min-height: 50px;
            }
        """)
        l_keywords.addWidget(self.lbl_keywords_result)
        
        content_layout.addWidget(grp_keywords)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"🤖 {tm.get('tab_ai')}")

    def _save_api_key(self):
        """API 키 저장"""
        key = self.txt_api_key.text().strip()
        self.settings["gemini_api_key"] = key
        save_settings(self.settings)
        toast = ToastWidget(tm.get("msg_key_saved"), toast_type='success', duration=2000)
        toast.show_toast(self)

    def _save_summary_result(self):
        """요약 결과 저장"""
        text = self.txt_summary_result.toPlainText()
        if not text:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_no_summary"))
        
        s, _ = QFileDialog.getSaveFileName(self, tm.get("dlg_save_summary"), "summary.txt", "텍스트 (*.txt)")
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
        self.txt_chat_history.append(f"<b>🧑 질문:</b> {question}")
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
                self.txt_chat_history.append(f"<b>🧑 질문:</b> {content}")
            elif role == "assistant":
                self.txt_chat_history.append(f"<b>🤖 답변:</b> {content}")
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
    
    
    # action_convert_to_word 함수 제거됨 (v4.2)

    def _show_thumbnail_grid(self):
        """썸네일 그리드 다이얼로그 표시"""
        path = self.sel_thumb_pdf.get_path()
        if not path:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
        
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

    # ===================== 설정 저장 및 리소스 정리 =====================
