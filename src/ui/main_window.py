import sys
import os
import json
import fitz
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox, 
    QSpinBox, QSplitter, QGroupBox, QScrollArea, QApplication, 
    QInputDialog, QLineEdit, QProgressBar, QListWidget, QListWidgetItem,
    QAbstractItemView, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage, QKeySequence, QShortcut

from ..core.settings import load_settings, save_settings
from ..core.worker import WorkerThread
from .widgets import FileSelectorWidget, FileListWidget, ImageListWidget, DropZoneWidget, WheelEventFilter
from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET, ThemeColors

APP_NAME = "PDF Master"
VERSION = "2.4"

class PDFMasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker = None
        self._last_output_path = None  # 마지막 저장 경로 추적
        self._current_preview_page = 0
        self._current_preview_doc = None
        
        # 휠 이벤트 필터 설치 (스크롤로 값 변경 방지)
        self._wheel_filter = WheelEventFilter(self)
        
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1200, 850)  # 더 큰 기본 크기
        self.setMinimumSize(950, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 10, 15, 10)  # 더 컴팩트한 여백
        main_layout.setSpacing(8)
        
        # Header - 컴팩트하게
        header = self._create_header()
        main_layout.addLayout(header)
        
        # Content area with splitter - 더 큰 비율
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setHandleWidth(5)  # 드래그 핸들 더 넘게
        self.content_splitter.setChildrenCollapsible(False)  # 패널 접기 방지
        
        # Tabs (left side)
        tabs_widget = QWidget()
        tabs_layout = QVBoxLayout(tabs_widget)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)
        self.content_splitter.addWidget(tabs_widget)
        
        # Preview panel (right side)
        preview_widget = self._create_preview_panel()
        self.content_splitter.addWidget(preview_widget)
        self.content_splitter.setSizes([650, 450])  # 미리보기 패널 더 크게
        
        # 사용자 설정 복원
        saved_sizes = self.settings.get("splitter_sizes")
        if saved_sizes:
            self.content_splitter.setSizes(saved_sizes)
        self.content_splitter.splitterMoved.connect(self._save_splitter_state)
        
        main_layout.addWidget(self.content_splitter, 1)  # stretch factor 1로 최대 확장
        
        # Setup tabs
        self.setup_merge_tab()
        self.setup_convert_tab()
        self.setup_page_tab()
        self.setup_reorder_tab()  # NEW: 페이지 순서 변경
        self.setup_edit_sec_tab()
        self.setup_batch_tab()    # NEW: 일괄 처리
        self.setup_advanced_tab()  # NEW: 고급 기능
        
        # 컴팩트한 상태 바
        status_frame = QFrame()
        status_frame.setMaximumHeight(36)  # 높이 제한
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(10)
        
        self.status_label = QLabel("✨ 준비 완료")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        status_layout.addWidget(self.progress_bar)
        
        self.btn_open_folder = QPushButton("📂 폴더")
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setFixedWidth(70)
        self.btn_open_folder.setFixedHeight(24)
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_last_folder)
        status_layout.addWidget(self.btn_open_folder)
        
        main_layout.addWidget(status_frame)
        
        self._apply_theme()
        self._setup_shortcuts()
        
        # 모든 QSpinBox, QComboBox에 휠 필터 설치
        self._install_wheel_filters()
    
    def _install_wheel_filters(self):
        """모든 입력 위젯에 휠 이벤트 필터 설치"""
        for widget in self.findChildren(QSpinBox):
            widget.installEventFilter(self._wheel_filter)
        for widget in self.findChildren(QComboBox):
            widget.installEventFilter(self._wheel_filter)
    
    def _setup_shortcuts(self):
        """Keyboard shortcuts"""
        QShortcut(QKeySequence("Ctrl+O"), self, self._shortcut_open_file)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("F1"), self, self._show_help)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.tabs.setCurrentIndex(3))
    
    def _shortcut_open_file(self):
        """Open file via shortcut"""
        f, _ = QFileDialog.getOpenFileName(self, "PDF 선택", "", "PDF (*.pdf)")
        if f:
            self._update_preview(f)
            self.status_label.setText(f"📄 {os.path.basename(f)} 로드됨")
    
    def _open_last_folder(self):
        """Open folder containing last output"""
        if self._last_output_path and os.path.exists(self._last_output_path):
            folder = os.path.dirname(self._last_output_path)
            if sys.platform == 'win32':
                subprocess.Popen(['explorer', '/select,', self._last_output_path])
            else:
                subprocess.Popen(['open', folder])
        
    def _save_splitter_state(self):
        """Save splitter position"""
        self.settings["splitter_sizes"] = self.content_splitter.sizes()
        save_settings(self.settings)
        
    def _create_header(self):
        header = QHBoxLayout()
        header.setSpacing(15)
        
        # 컴팩트한 타이틀
        title = QLabel(f"📑 {APP_NAME}")
        title.setObjectName("header")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e94560;")
        header.addWidget(title)
        
        ver_label = QLabel(f"v{VERSION}")
        ver_label.setStyleSheet("color: #666; font-size: 11px;")
        header.addWidget(ver_label)
        
        header.addStretch()
        
        # Theme toggle
        theme_text = "DARK" if self.settings.get("theme") == "dark" else "LIGHT"
        self.btn_theme = QPushButton(theme_text)
        self.btn_theme.setMinimumSize(70, 32)
        self.btn_theme.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 5px 10px; } QPushButton:hover { background-color: #ff5a7a; }")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)
        
        # Help button
        btn_help = QPushButton("HELP")
        btn_help.setMinimumSize(60, 32)
        btn_help.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 5px 10px; } QPushButton:hover { background-color: #ff5a7a; }")
        btn_help.clicked.connect(self._show_help)
        header.addWidget(btn_help)
        
        return header
    
    def _create_preview_panel(self):
        panel = QGroupBox("📋 미리보기")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        self.preview_label = QLabel("PDF 파일을 선택하면\n여기에 정보가 표시됩니다")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMaximumHeight(120)  # 정보 영역 높이 제한
        layout.addWidget(self.preview_label)
        
        # 더 큰 미리보기 이미지 영역
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setMinimumSize(250, 350)
        self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
        self.preview_image.setSizePolicy(self.preview_image.sizePolicy().horizontalPolicy(), 
                                          self.preview_image.sizePolicy().verticalPolicy())
        layout.addWidget(self.preview_image, 1)
        
        # 페이지 네비게이션 버튼
        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton("PREV")
        self.btn_prev_page.setMinimumSize(70, 30)
        self.btn_prev_page.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #ff5a7a; }")
        self.btn_prev_page.clicked.connect(self._prev_preview_page)
        nav_layout.addWidget(self.btn_prev_page)
        
        self.page_counter = QLabel("1 / 1")
        self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_layout.addWidget(self.page_counter)
        
        self.btn_next_page = QPushButton("NEXT")
        self.btn_next_page.setMinimumSize(70, 30)
        self.btn_next_page.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #ff5a7a; }")
        self.btn_next_page.clicked.connect(self._next_preview_page)
        nav_layout.addWidget(self.btn_next_page)
        layout.addLayout(nav_layout)
        
        return panel
    
    def _prev_preview_page(self):
        if self._current_preview_page > 0:
            self._current_preview_page -= 1
            self._render_preview_page()
    
    def _next_preview_page(self):
        if hasattr(self, '_preview_total_pages') and self._current_preview_page < self._preview_total_pages - 1:
            self._current_preview_page += 1
            self._render_preview_page()
    
    def _render_preview_page(self):
        if not hasattr(self, '_current_preview_path') or not self._current_preview_path:
            return
        try:
            doc = fitz.open(self._current_preview_path)
            if self._current_preview_page < len(doc):
                page = doc[self._current_preview_page]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = bytes(pix.samples)
                img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(img.copy())
                preview_size = self.preview_image.size()
                target_w = max(280, preview_size.width() - 20)
                target_h = max(400, preview_size.height() - 20)
                scaled = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_image.setPixmap(scaled)
                self.page_counter.setText(f"{self._current_preview_page + 1} / {self._preview_total_pages}")
            doc.close()
        except Exception as e:
            print(f"Preview render error: {e}")
    
    def _on_list_item_clicked(self, item):
        """리스트 아이템 클릭 시 미리보기 업데이트"""
        path = item.data(Qt.ItemDataRole.UserRole)
        self._update_preview(path)
    
    
    def _update_preview(self, path):
        if not path or not os.path.exists(path):
            self.preview_label.setText("PDF 파일을 선택하면\n여기에 정보가 표시됩니다")
            self.preview_image.clear()
            return
        
        # 최근 파일 목록 업데이트
        self._add_to_recent_files(path)
        
        try:
            doc = fitz.open(path)
            
            # 암호화된 PDF 처리
            if doc.is_encrypted:
                doc.close()
                password, ok = QInputDialog.getText(
                    self, "🔒 암호 입력", 
                    f"'{os.path.basename(path)}'\n\n비밀번호를 입력하세요:",
                    QLineEdit.EchoMode.Password
                )
                if ok and password:
                    doc = fitz.open(path)
                    if not doc.authenticate(password):
                        doc.close()
                        self.preview_label.setText("❌ 비밀번호가 틀렸습니다")
                        self.preview_image.clear()
                        return
                else:
                    self.preview_label.setText("🔒 암호화된 PDF\n비밀번호가 필요합니다")
                    self.preview_image.clear()
                    return
            
            size_kb = os.path.getsize(path) / 1024
            meta = doc.metadata
            title = meta.get('title', '-') if meta else '-'
            author = meta.get('author', '-') if meta else '-'
            info = f"""📄 {os.path.basename(path)}

📊 페이지: {len(doc)}p  💾 크기: {size_kb:.1f}KB
📝 제목: {title or '-'}
👤 작성자: {author or '-'}"""
            self.preview_label.setText(info)
            
            # 페이지 네비게이션 변수 초기화
            self._current_preview_path = path
            self._preview_total_pages = len(doc)
            self._current_preview_page = 0
            self.page_counter.setText(f"1 / {len(doc)}")
            
            # Thumbnail
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                img_data = bytes(pix.samples)
                img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(img.copy())
                preview_size = self.preview_image.size()
                target_w = max(280, preview_size.width() - 20)
                target_h = max(400, preview_size.height() - 20)
                scaled = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_image.setPixmap(scaled)
            doc.close()
        except Exception as e:
            self.preview_label.setText(f"미리보기 오류: {e}")
    
    def _add_to_recent_files(self, path):
        """최근 파일 목록에 추가"""
        recent = self.settings.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.settings["recent_files"] = recent[:10]  # 최대 10개
        save_settings(self.settings)
    
    def _toggle_theme(self):
        current = self.settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        self._apply_theme()
        self.btn_theme.setText("DARK" if new_theme == "dark" else "LIGHT")
    
    def _apply_theme(self):
        theme = self.settings.get("theme", "dark")
        is_dark = theme == "dark"
        QApplication.instance().setStyleSheet(DARK_STYLESHEET if is_dark else LIGHT_STYLESHEET)
        
        # 모든 DropZone 위젯 테마 동기화
        for widget in self.findChildren(DropZoneWidget):
            widget.set_theme(is_dark)
        
        # 미리보기 패널 테마 동기화
        if hasattr(self, 'preview_image'):
            if is_dark:
                self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
                self.preview_label.setStyleSheet("color: #888; padding: 10px; font-size: 12px;")
            else:
                self.preview_image.setStyleSheet("background: #f0f0f0; border-radius: 8px; border: 1px solid #ddd;")
                self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px; background: transparent;")
    
    def _show_help(self):
        QMessageBox.information(self, "도움말", f"""📑 {APP_NAME} v{VERSION}

🔹 파일을 드래그하거나 버튼으로 선택하세요
🔹 각 탭에서 원하는 작업을 선택하세요
🔹 작업 완료 시 저장 위치를 지정합니다

주요 기능:
• 📎 병합: 여러 PDF를 하나로
• 🖼️ 변환: PDF ↔ 이미지
• ✂️ 페이지: 추출, 삭제, 회전
• 🔒 보안: 암호화, 워터마크""")
    
    # Worker helpers
    def run_worker(self, mode, output_path=None, **kwargs):
        # output_path 추적 (폴더 열기 기능용)
        if output_path:
            self._last_output_path = output_path
            kwargs['output_path'] = output_path
        elif 'output_path' in kwargs:
            self._last_output_path = kwargs['output_path']
        elif 'output_dir' in kwargs:
            self._last_output_path = kwargs['output_dir']
        
        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText("⏳ 작업 처리 중...")
        self.set_ui_busy(True)
        self.worker.start()
    
    def on_success(self, msg):
        self.set_ui_busy(False)
        self.status_label.setText("✅ 작업 완료!")
        self.progress_bar.setValue(100)
        self.btn_open_folder.setVisible(True)  # 폴더 열기 버튼 표시
        QMessageBox.information(self, "완료", msg)
        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
    
    def on_fail(self, msg):
        self.set_ui_busy(False)
        self.status_label.setText("❌ 오류 발생")
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        QMessageBox.critical(self, "오류", f"작업 중 문제가 발생했습니다.\n{msg}")
    
    def set_ui_busy(self, busy):
        self.tabs.setEnabled(not busy)
        self.btn_open_folder.setEnabled(not busy)

    # ===================== Tab 1: 병합 =====================
    def setup_merge_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Guide
        guide = QLabel("📎 여러 PDF 파일을 하나로 합칩니다")
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일들을 아래에 드래그하세요 (순서 조정 가능)")
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.merge_list = FileListWidget()
        self.merge_list.itemClicked.connect(self._on_list_item_clicked)
        layout.addWidget(self.merge_list)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton("➕ 파일 추가")
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._merge_add_files)
        
        b_del = QPushButton("➖ 선택 삭제")
        b_del.setObjectName("secondaryBtn")
        b_del.clicked.connect(lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()])
        
        b_clr = QPushButton("🧹 전체 삭제")
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self.merge_list.clear)
        
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_del)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        step2 = QLabel("2️⃣ 병합 실행")
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        b_run = QPushButton("🚀 PDF 병합 실행")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_merge)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, "📎 병합")
    
    def _merge_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.merge_list.addItem(item)
    
    def action_merge(self):
        files = self.merge_list.get_all_paths()
        if len(files) < 2:
            return QMessageBox.warning(self, "알림", "2개 이상의 PDF 파일이 필요합니다.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "merged.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("merge", files=files, output_path=save)

    # ===================== Tab 2: 변환 =====================
    def setup_convert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # PDF → 이미지
        grp_img = QGroupBox("🖼️ PDF → 이미지 변환 (다중 파일)")
        l_img = QVBoxLayout(grp_img)
        step = QLabel("1️⃣ PDF 파일들을 드래그하거나 추가하세요")
        step.setObjectName("stepLabel")
        l_img.addWidget(step)
        self.img_conv_list = FileListWidget()
        self.img_conv_list.setMaximumHeight(100)
        l_img.addWidget(self.img_conv_list)
        self.img_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.img_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_img = QHBoxLayout()
        btn_add_pdf = QPushButton("➕ PDF 추가")
        btn_add_pdf.clicked.connect(self._add_pdf_for_img)
        
        btn_clear_img = QPushButton("🗑️ 전체 삭제")
        btn_clear_img.setToolTip("목록 비우기")
        btn_clear_img.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_img.clicked.connect(self.img_conv_list.clear)
        
        btn_layout_img.addWidget(btn_add_pdf)
        btn_layout_img.addWidget(btn_clear_img)
        l_img.addLayout(btn_layout_img)
        
        opt = QHBoxLayout()
        opt.addWidget(QLabel("포맷:"))
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["png", "jpg"])
        opt.addWidget(self.cmb_fmt)
        opt.addWidget(QLabel("해상도(DPI):"))
        self.spn_dpi = QSpinBox()
        self.spn_dpi.setRange(72, 600)
        self.spn_dpi.setValue(150)
        opt.addWidget(self.spn_dpi)
        opt.addStretch()
        l_img.addLayout(opt)
        
        b_img = QPushButton("🖼️ 이미지로 변환")
        b_img.clicked.connect(self.action_img)
        l_img.addWidget(b_img)
        content_layout.addWidget(grp_img)
        
        # 이미지 → PDF
        grp_img2pdf = QGroupBox("📄 이미지 → PDF 변환")
        l_i2p = QVBoxLayout(grp_img2pdf)
        step2 = QLabel("1️⃣ 이미지 파일들을 아래에 드래그하세요")
        step2.setObjectName("stepLabel")
        l_i2p.addWidget(step2)
        self.img_list = ImageListWidget()
        l_i2p.addWidget(self.img_list)
        
        btn_i2p = QHBoxLayout()
        b_add_img = QPushButton("➕ 이미지 추가")
        b_add_img.setObjectName("secondaryBtn")
        b_add_img.clicked.connect(self._add_images)
        b_clr_img = QPushButton("🧹 초기화")
        b_clr_img.setObjectName("secondaryBtn")
        b_clr_img.clicked.connect(self.img_list.clear)
        btn_i2p.addWidget(b_add_img)
        btn_i2p.addWidget(b_clr_img)
        btn_i2p.addStretch()
        l_i2p.addLayout(btn_i2p)
        
        b_i2p = QPushButton("📄 PDF로 변환")
        b_i2p.clicked.connect(self.action_img_to_pdf)
        l_i2p.addWidget(b_i2p)
        content_layout.addWidget(grp_img2pdf)
        
        # 텍스트 추출
        grp_txt = QGroupBox("📝 텍스트 추출 (다중 파일)")
        l_txt = QVBoxLayout(grp_txt)
        step_txt = QLabel("PDF 파일들을 드래그하거나 추가하세요")
        step_txt.setObjectName("stepLabel")
        l_txt.addWidget(step_txt)
        self.txt_conv_list = FileListWidget()
        self.txt_conv_list.setMaximumHeight(100)
        l_txt.addWidget(self.txt_conv_list)
        self.txt_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.txt_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_txt = QHBoxLayout()
        btn_add_txt = QPushButton("➕ PDF 추가")
        btn_add_txt.clicked.connect(self._add_pdf_for_txt)
        
        btn_clear_txt = QPushButton("🗑️ 전체 삭제")
        btn_clear_txt.setToolTip("목록 비우기")
        btn_clear_txt.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_txt.clicked.connect(self.txt_conv_list.clear)
        
        btn_layout_txt.addWidget(btn_add_txt)
        btn_layout_txt.addWidget(btn_clear_txt)
        l_txt.addLayout(btn_layout_txt)
        b_txt = QPushButton("📝 텍스트(.txt) 저장")
        b_txt.clicked.connect(self.action_txt)
        l_txt.addWidget(b_txt)
        content_layout.addWidget(grp_txt)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "🔄 변환")
    
    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "이미지 선택", "", "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        for f in files:
            item = QListWidgetItem(f"🖼️ {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.img_list.addItem(item)
    
    def _add_pdf_for_img(self):
        """이미지 변환용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.img_conv_list.add_file(f)
    
    def _add_pdf_for_txt(self):
        """텍스트 추출용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.txt_conv_list.add_file(f)
    
    def action_img(self):
        paths = self.img_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("convert_to_img", file_paths=paths, output_dir=d, 
                          fmt=self.cmb_fmt.currentText(), dpi=self.spn_dpi.value())
    
    def action_img_to_pdf(self):
        files = self.img_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "이미지 파일을 추가하세요.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "images.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("images_to_pdf", files=files, output_path=save)
    
    def action_txt(self):
        paths = self.txt_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("extract_text", file_paths=paths, output_dir=d)

    # ===================== Tab 3: 페이지 =====================
    def setup_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 추출
        grp_split = QGroupBox("✂️ 페이지 추출")
        l_s = QVBoxLayout(grp_split)
        self.sel_split = FileSelectorWidget()
        self.sel_split.pathChanged.connect(self._update_preview)
        l_s.addWidget(self.sel_split)
        h = QHBoxLayout()
        h.addWidget(QLabel("추출할 페이지 (예: 1-3, 5):"))
        self.inp_range = QLineEdit()
        self.inp_range.setPlaceholderText("1, 3-5, 8")
        h.addWidget(self.inp_range)
        l_s.addLayout(h)
        b_s = QPushButton("✂️ 추출 실행")
        b_s.clicked.connect(self.action_split)
        l_s.addWidget(b_s)
        content_layout.addWidget(grp_split)
        
        # 삭제
        grp_del = QGroupBox("🗑️ 페이지 삭제")
        l_d = QVBoxLayout(grp_del)
        self.sel_del = FileSelectorWidget()
        l_d.addWidget(self.sel_del)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("삭제할 페이지 (예: 1, 3-5):"))
        self.inp_del_range = QLineEdit()
        self.inp_del_range.setPlaceholderText("2, 4-6")
        h2.addWidget(self.inp_del_range)
        l_d.addLayout(h2)
        b_d = QPushButton("🗑️ 삭제 실행")
        b_d.clicked.connect(self.action_delete_pages)
        l_d.addWidget(b_d)
        content_layout.addWidget(grp_del)
        
        # 회전
        grp_rot = QGroupBox("🔄 페이지 회전")
        l_r = QVBoxLayout(grp_rot)
        self.sel_rot = FileSelectorWidget()
        l_r.addWidget(self.sel_rot)
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("회전 각도:"))
        self.cmb_rot = QComboBox()
        self.cmb_rot.addItems(["90° 시계방향", "180°", "270° 시계방향"])
        h3.addWidget(self.cmb_rot)
        h3.addStretch()
        l_r.addLayout(h3)
        b_r = QPushButton("🔄 회전 실행")
        b_r.clicked.connect(self.action_rotate)
        l_r.addWidget(b_r)
        content_layout.addWidget(grp_rot)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "✂️ 페이지")
    
    def action_split(self):
        path = self.sel_split.get_path()
        rng = self.inp_range.text()
        if not path or not rng:
            return QMessageBox.warning(self, "알림", "파일과 페이지 범위를 입력하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더")
        if d:
            self.run_worker("split", file_path=path, output_dir=d, page_range=rng)
    
    def action_delete_pages(self):
        path = self.sel_del.get_path()
        rng = self.inp_del_range.text()
        if not path or not rng:
            return QMessageBox.warning(self, "알림", "파일과 삭제할 페이지를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "deleted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("delete_pages", file_path=path, output_path=s, page_range=rng)
    
    def action_rotate(self):
        path = self.sel_rot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        angle_map = {"90° 시계방향": 90, "180°": 180, "270° 시계방향": 270}
        angle = angle_map.get(self.cmb_rot.currentText(), 90)
        s, _ = QFileDialog.getSaveFileName(self, "저장", "rotated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("rotate", file_path=path, output_path=s, angle=angle)

    # ===================== Tab 4: 편집/보안 =====================
    def setup_edit_sec_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 메타데이터
        grp_meta = QGroupBox("📋 메타데이터 수정")
        l_m = QVBoxLayout(grp_meta)
        self.sel_meta = FileSelectorWidget()
        self.sel_meta.pathChanged.connect(self._load_metadata)
        l_m.addWidget(self.sel_meta)
        self.sel_meta.pathChanged.connect(self._update_preview)
        form = QFormLayout()
        self.inp_title = QLineEdit()
        self.inp_author = QLineEdit()
        self.inp_subj = QLineEdit()
        form.addRow("제목:", self.inp_title)
        form.addRow("작성자:", self.inp_author)
        form.addRow("주제:", self.inp_subj)
        l_m.addLayout(form)
        b_m = QPushButton("💾 메타데이터 저장")
        b_m.clicked.connect(self.action_metadata)
        l_m.addWidget(b_m)
        content_layout.addWidget(grp_meta)
        
        # 워터마크
        grp_wm = QGroupBox("💧 워터마크 삽입")
        l_w = QVBoxLayout(grp_wm)
        self.sel_wm = FileSelectorWidget()
        l_w.addWidget(self.sel_wm)
        self.sel_wm.pathChanged.connect(self._update_preview)
        h_w = QHBoxLayout()
        self.inp_wm = QLineEdit()
        self.inp_wm.setPlaceholderText("워터마크 텍스트")
        h_w.addWidget(self.inp_wm)
        self.cmb_wm_color = QComboBox()
        self.cmb_wm_color.addItems(["회색", "검정", "빨강", "파랑"])
        h_w.addWidget(self.cmb_wm_color)
        l_w.addLayout(h_w)
        b_w = QPushButton("💧 워터마크 적용")
        b_w.clicked.connect(self.action_watermark)
        l_w.addWidget(b_w)
        content_layout.addWidget(grp_wm)
        
        # 보안
        grp_sec = QGroupBox("🔒 보안 && 압축")
        l_sec = QVBoxLayout(grp_sec)
        self.sel_sec = FileSelectorWidget()
        l_sec.addWidget(self.sel_sec)
        self.sel_sec.pathChanged.connect(self._update_preview)
        h_sec = QHBoxLayout()
        self.inp_pw = QLineEdit()
        self.inp_pw.setPlaceholderText("비밀번호 입력")
        self.inp_pw.setEchoMode(QLineEdit.EchoMode.Password)
        h_sec.addWidget(self.inp_pw)
        b_enc = QPushButton("🔒 암호화")
        b_enc.clicked.connect(self.action_protect)
        h_sec.addWidget(b_enc)
        b_comp = QPushButton("📦 압축")
        b_comp.clicked.connect(self.action_compress)
        h_sec.addWidget(b_comp)
        l_sec.addLayout(h_sec)
        content_layout.addWidget(grp_sec)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "🔒 편집/보안")
    
    def _load_metadata(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            doc = fitz.open(path)
            m = doc.metadata
            self.inp_title.setText(m.get('title', '') or '')
            self.inp_author.setText(m.get('author', '') or '')
            self.inp_subj.setText(m.get('subject', '') or '')
            doc.close()
        except: pass
    
    def action_metadata(self):
        path = self.sel_meta.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        meta = {'title': self.inp_title.text(), 'author': self.inp_author.text(), 'subject': self.inp_subj.text()}
        s, _ = QFileDialog.getSaveFileName(self, "저장", "metadata_updated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("metadata_update", file_path=path, output_path=s, metadata=meta)
    
    def action_watermark(self):
        path = self.sel_wm.get_path()
        text = self.inp_wm.text()
        if not path or not text:
            return QMessageBox.warning(self, "알림", "파일과 텍스트를 입력하세요.")
        c_map = {"회색": (0.5,0.5,0.5), "검정": (0,0,0), "빨강": (1,0,0), "파랑": (0,0,1)}
        color = c_map.get(self.cmb_wm_color.currentText(), (0.5,0.5,0.5))
        s, _ = QFileDialog.getSaveFileName(self, "저장", "watermarked.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("watermark", file_path=path, output_path=s, text=text, color=color)
    
    def action_protect(self):
        path = self.sel_sec.get_path()
        pw = self.inp_pw.text()
        if not path or not pw:
            return QMessageBox.warning(self, "알림", "파일과 비밀번호를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "encrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("protect", file_path=path, output_path=s, password=pw)
    
    def action_compress(self):
        path = self.sel_sec.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "compressed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("compress", file_path=path, output_path=s)

    # ===================== Tab 5: 페이지 순서 변경 =====================
    def setup_reorder_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        guide = QLabel("🔀 PDF 페이지 순서를 변경합니다")
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일 선택")
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.sel_reorder = FileSelectorWidget()
        self.sel_reorder.pathChanged.connect(self._load_pages_for_reorder)
        layout.addWidget(self.sel_reorder)
        self.sel_reorder.pathChanged.connect(self._update_preview)
        
        step2 = QLabel("2️⃣ 페이지를 드래그하여 순서 변경")
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        self.reorder_list = QListWidget()
        self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.reorder_list.setMinimumHeight(150)
        self.reorder_list.setToolTip("페이지를 드래그하여 순서를 변경하세요")
        layout.addWidget(self.reorder_list)
        
        btn_box = QHBoxLayout()
        b_reverse = QPushButton("🔃 역순 정렬")
        b_reverse.setObjectName("secondaryBtn")
        b_reverse.clicked.connect(self._reverse_pages)
        btn_box.addWidget(b_reverse)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        b_run = QPushButton("💾 순서 변경 저장")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_reorder)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, "🔀 순서")
    
    def _load_pages_for_reorder(self, path):
        """페이지 목록 로드"""
        self.reorder_list.clear()
        if not path or not os.path.exists(path):
            return
        try:
            doc = fitz.open(path)
            for i in range(len(doc)):
                item = QListWidgetItem(f"📄 페이지 {i+1}")
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.reorder_list.addItem(item)
            doc.close()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"페이지 로드 실패: {e}")
    
    def _reverse_pages(self):
        """페이지 역순 정렬"""
        items = []
        while self.reorder_list.count() > 0:
            items.append(self.reorder_list.takeItem(0))
        for item in reversed(items):
            self.reorder_list.addItem(item)
    
    def action_reorder(self):
        path = self.sel_reorder.get_path()
        if not path or self.reorder_list.count() == 0:
            return QMessageBox.warning(self, "알림", "PDF를 선택하고 페이지를 확인하세요.")
        page_order = [self.reorder_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.reorder_list.count())]
        s, _ = QFileDialog.getSaveFileName(self, "저장", "reordered.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("reorder", file_path=path, output_path=s, page_order=page_order)

    # ===================== Tab 6: 일괄 처리 =====================
    def setup_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        guide = QLabel("📦 여러 PDF에 동일한 작업을 일괄 적용합니다")
        guide.setObjectName("desc")
        content_layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일들 선택")
        step1.setObjectName("stepLabel")
        content_layout.addWidget(step1)
        
        self.batch_list = FileListWidget()
        self.batch_list.itemClicked.connect(self._on_list_item_clicked)
        content_layout.addWidget(self.batch_list)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton("➕ 파일 추가")
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._batch_add_files)
        b_folder = QPushButton("📁 폴더 전체")
        b_folder.setObjectName("secondaryBtn")
        b_folder.clicked.connect(self._batch_add_folder)
        b_clr = QPushButton("🧹 초기화")
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self.batch_list.clear)
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_folder)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        content_layout.addLayout(btn_box)
        
        step2 = QLabel("2️⃣ 적용할 작업 선택")
        step2.setObjectName("stepLabel")
        content_layout.addWidget(step2)
        
        # 작업 선택
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("작업:"))
        self.cmb_batch_op = QComboBox()
        self.cmb_batch_op.addItems(["📦 압축", "💧 워터마크", "🔒 암호화", "🔄 회전(90°)"])
        opt_layout.addWidget(self.cmb_batch_op)
        opt_layout.addStretch()
        content_layout.addLayout(opt_layout)
        
        # 워터마크/암호 옵션
        opt_layout2 = QHBoxLayout()
        opt_layout2.addWidget(QLabel("텍스트/암호:"))
        self.inp_batch_opt = QLineEdit()
        self.inp_batch_opt.setPlaceholderText("워터마크 텍스트 또는 비밀번호")
        opt_layout2.addWidget(self.inp_batch_opt)
        content_layout.addLayout(opt_layout2)
        
        step3 = QLabel("3️⃣ 출력 폴더 선택 및 실행")
        step3.setObjectName("stepLabel")
        content_layout.addWidget(step3)
        
        b_run = QPushButton("🚀 일괄 처리 실행")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_batch)
        content_layout.addWidget(b_run)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "📦 일괄")
    
    def _batch_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.batch_list.addItem(item)
    
    def _batch_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            for f in os.listdir(folder):
                if f.lower().endswith('.pdf'):
                    path = os.path.join(folder, f)
                    item = QListWidgetItem(f"📄 {f}")
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    item.setToolTip(path)
                    self.batch_list.addItem(item)
    
    def action_batch(self):
        files = self.batch_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if not out_dir:
            return
        op = self.cmb_batch_op.currentText()
        opt = self.inp_batch_opt.text()
        self.run_worker("batch", files=files, output_dir=out_dir, operation=op, option=opt)

    # ===================== Tab 7: 고급 기능 =====================
    def setup_advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        guide = QLabel("🔧 고급 PDF 편집 기능")
        guide.setObjectName("desc")
        content_layout.addWidget(guide)
        
        # 1. PDF 분할
        grp_split = QGroupBox("✂️ PDF 분할")
        l_split = QVBoxLayout(grp_split)
        self.sel_split_adv = FileSelectorWidget()
        l_split.addWidget(self.sel_split_adv)
        self.sel_split_adv.pathChanged.connect(self._update_preview)
        opt_split = QHBoxLayout()
        opt_split.addWidget(QLabel("분할 모드:"))
        self.cmb_split_mode = QComboBox()
        self.cmb_split_mode.addItems(["각 페이지별", "범위 지정"])
        opt_split.addWidget(self.cmb_split_mode)
        self.inp_split_range = QLineEdit()
        self.inp_split_range.setPlaceholderText("예: 1-3, 5-7, 10-12")
        opt_split.addWidget(self.inp_split_range)
        l_split.addLayout(opt_split)
        b_split = QPushButton("✂️ PDF 분할 실행")
        b_split.clicked.connect(self.action_split_adv)
        l_split.addWidget(b_split)
        content_layout.addWidget(grp_split)
        
        # 2. 페이지 번호
        grp_pn = QGroupBox("🔢 페이지 번호 삽입")
        l_pn = QVBoxLayout(grp_pn)
        self.sel_pn = FileSelectorWidget()
        l_pn.addWidget(self.sel_pn)
        self.sel_pn.pathChanged.connect(self._update_preview)
        
        # 형식 안내 라벨
        guide_pn = QLabel("📌 형식: {n}=현재페이지, {total}=전체페이지")
        guide_pn.setStyleSheet("color: #888; font-size: 11px;")
        l_pn.addWidget(guide_pn)
        
        opt_pn = QHBoxLayout()
        opt_pn.addWidget(QLabel("위치:"))
        self.cmb_pn_pos = QComboBox()
        self.cmb_pn_pos.addItems(["하단 중앙", "상단 중앙"])
        opt_pn.addWidget(self.cmb_pn_pos)
        opt_pn.addWidget(QLabel("형식:"))
        self.cmb_pn_format = QComboBox()
        self.cmb_pn_format.addItems([
            "{n} / {total}",
            "Page {n} of {total}",
            "- {n} -",
            "{n}",
            "페이지 {n}"
        ])
        self.cmb_pn_format.setEditable(True)
        opt_pn.addWidget(self.cmb_pn_format)
        l_pn.addLayout(opt_pn)
        b_pn = QPushButton("🔢 페이지 번호 삽입")
        b_pn.clicked.connect(self.action_page_numbers)
        l_pn.addWidget(b_pn)
        content_layout.addWidget(grp_pn)
        
        # 3. 스탬프
        grp_stamp = QGroupBox("📌 스탬프 추가")
        l_stamp = QVBoxLayout(grp_stamp)
        self.sel_stamp = FileSelectorWidget()
        l_stamp.addWidget(self.sel_stamp)
        self.sel_stamp.pathChanged.connect(self._update_preview)
        opt_stamp = QHBoxLayout()
        opt_stamp.addWidget(QLabel("스탬프:"))
        self.cmb_stamp = QComboBox()
        self.cmb_stamp.addItems(["기밀", "승인됨", "초안", "최종본", "복사본 금지"])
        self.cmb_stamp.setEditable(True)
        opt_stamp.addWidget(self.cmb_stamp)
        opt_stamp.addWidget(QLabel("위치:"))
        self.cmb_stamp_pos = QComboBox()
        self.cmb_stamp_pos.addItems(["우상단", "좌상단", "우하단", "좌하단"])
        opt_stamp.addWidget(self.cmb_stamp_pos)
        l_stamp.addLayout(opt_stamp)
        b_stamp = QPushButton("📌 스탬프 추가")
        b_stamp.clicked.connect(self.action_stamp)
        l_stamp.addWidget(b_stamp)
        content_layout.addWidget(grp_stamp)
        
        # 4. 여백 자르기
        grp_crop = QGroupBox("📐 여백 자르기 (Crop)")
        l_crop = QVBoxLayout(grp_crop)
        self.sel_crop = FileSelectorWidget()
        l_crop.addWidget(self.sel_crop)
        self.sel_crop.pathChanged.connect(self._update_preview)
        opt_crop = QHBoxLayout()
        for side in ["좌", "상", "우", "하"]:
            opt_crop.addWidget(QLabel(f"{side}:"))
            spn = QSpinBox()
            spn.setRange(0, 200)
            spn.setValue(20)
            setattr(self, f"spn_crop_{side}", spn)
            opt_crop.addWidget(spn)
        l_crop.addLayout(opt_crop)
        b_crop = QPushButton("📐 여백 자르기")
        b_crop.clicked.connect(self.action_crop)
        l_crop.addWidget(b_crop)
        content_layout.addWidget(grp_crop)
        
        # 5. 빈 페이지 삽입
        grp_blank = QGroupBox("📄 빈 페이지 삽입")
        l_blank = QVBoxLayout(grp_blank)
        self.sel_blank = FileSelectorWidget()
        l_blank.addWidget(self.sel_blank)
        self.sel_blank.pathChanged.connect(self._update_preview)
        opt_blank = QHBoxLayout()
        opt_blank.addWidget(QLabel("삽입 위치 (페이지 번호):"))
        self.spn_blank_pos = QSpinBox()
        self.spn_blank_pos.setRange(1, 999)
        self.spn_blank_pos.setValue(1)
        opt_blank.addWidget(self.spn_blank_pos)
        opt_blank.addStretch()
        l_blank.addLayout(opt_blank)
        b_blank = QPushButton("📄 빈 페이지 삽입")
        b_blank.clicked.connect(self.action_blank_page)
        l_blank.addWidget(b_blank)
        content_layout.addWidget(grp_blank)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "🔧 고급")
    
    def action_split_adv(self):
        path = self.sel_split_adv.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if out_dir:
            mode = 'each' if self.cmb_split_mode.currentIndex() == 0 else 'range'
            self.run_worker("split_by_pages", file_path=path, output_dir=out_dir, 
                          split_mode=mode, ranges=self.inp_split_range.text())
    
    def action_page_numbers(self):
        path = self.sel_pn.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "numbered.pdf", "PDF (*.pdf)")
        if s:
            pos = 'bottom' if self.cmb_pn_pos.currentIndex() == 0 else 'top'
            self.run_worker("add_page_numbers", file_path=path, output_path=s,
                          position=pos, format=self.cmb_pn_format.currentText())
    
    def action_stamp(self):
        path = self.sel_stamp.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "stamped.pdf", "PDF (*.pdf)")
        if s:
            pos_map = {"우상단": "top-right", "좌상단": "top-left", 
                      "우하단": "bottom-right", "좌하단": "bottom-left"}
            pos = pos_map.get(self.cmb_stamp_pos.currentText(), "top-right")
            self.run_worker("add_stamp", file_path=path, output_path=s,
                          stamp_text=self.cmb_stamp.currentText(), position=pos)
    
    def action_crop(self):
        path = self.sel_crop.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "cropped.pdf", "PDF (*.pdf)")
        if s:
            margins = {
                'left': self.spn_crop_좌.value(),
                'top': self.spn_crop_상.value(),
                'right': self.spn_crop_우.value(),
                'bottom': self.spn_crop_하.value()
            }
            self.run_worker("crop_pdf", file_path=path, output_path=s, margins=margins)
    
    def action_blank_page(self):
        path = self.sel_blank.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_blank.pdf", "PDF (*.pdf)")
        if s:
            pos = self.spn_blank_pos.value() - 1  # 0-indexed
            self.run_worker("insert_blank_page", file_path=path, output_path=s, position=pos)

