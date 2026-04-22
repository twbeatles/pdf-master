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
    saved_key = self._load_api_key_for_ui()
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

    self.lbl_summary_meta = QLabel("")
    self.lbl_summary_meta.setWordWrap(True)
    self.lbl_summary_meta.setVisible(False)
    l_summary.addWidget(self.lbl_summary_meta)

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
    self.sel_thumb_pdf.pathChanged.connect(self._update_preview)
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
    self.txt_chat_history.setPlaceholderText(tm.get("ph_chat_history"))
    self.txt_chat_history.setMinimumHeight(150)
    self.txt_chat_history.setReadOnly(True)
    l_chat.addWidget(self.txt_chat_history)

    self.lbl_chat_meta = QLabel("")
    self.lbl_chat_meta.setWordWrap(True)
    self.lbl_chat_meta.setVisible(False)
    l_chat.addWidget(self.lbl_chat_meta)

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

    self.lbl_keywords_meta = QLabel("")
    self.lbl_keywords_meta.setWordWrap(True)
    self.lbl_keywords_meta.setVisible(False)
    l_keywords.addWidget(self.lbl_keywords_meta)

    content_layout.addWidget(grp_keywords)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    self.tabs.addTab(tab, f"🤖 {tm.get('tab_ai')}")
