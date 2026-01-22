import logging
import os
import subprocess
import sys

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core.constants import RECENT_FILES_MAX
from ..core.i18n import tm
from ..core.settings import save_settings
from .widgets import ToastWidget

logger = logging.getLogger(__name__)


class MainWindowPreviewMixin:

    def _create_preview_panel(self):
        panel = QGroupBox(tm.get("preview_title"))
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        self.preview_label = QLabel(tm.get("preview_default"))
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
        
        # 페이지 네비게이션 버튼 - objectName 사용
        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton(tm.get("prev_page"))
        self.btn_prev_page.setObjectName("navBtn")
        self.btn_prev_page.setFixedSize(80, 30)
        self.btn_prev_page.clicked.connect(self._prev_preview_page)
        nav_layout.addWidget(self.btn_prev_page)
        
        self.page_counter = QLabel("1 / 1")
        self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_layout.addWidget(self.page_counter)
        
        self.btn_next_page = QPushButton(tm.get("next_page"))
        self.btn_next_page.setObjectName("navBtn")
        self.btn_next_page.setFixedSize(80, 30)
        self.btn_next_page.clicked.connect(self._next_preview_page)
        nav_layout.addWidget(self.btn_next_page)
        
        # v4.5: Print button
        self.btn_print_preview = QPushButton(tm.get("btn_print_preview"))
        self.btn_print_preview.setObjectName("secondaryBtn")
        self.btn_print_preview.setFixedSize(70, 30)
        self.btn_print_preview.setToolTip(tm.get("tooltip_print_preview"))
        self.btn_print_preview.clicked.connect(self._print_current_preview)
        nav_layout.addWidget(self.btn_print_preview)
        
        layout.addLayout(nav_layout)
        self._set_preview_navigation_enabled(False)
        
        return panel

    def _print_current_preview(self):
        """현재 미리보기 PDF 인쇄"""
        if hasattr(self, '_current_preview_path') and self._current_preview_path:
            self._print_pdf(self._current_preview_path)
        else:
            QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))

    def _print_pdf(self, path):
        """PDF 직접 인쇄"""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))
            return
        
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                # 시스템 기본 PDF 뷰어로 인쇄 명령 전송
                if sys.platform == 'win32':
                    os.startfile(path, 'print')
                else:
                    subprocess.run(['lpr', path])
                toast = ToastWidget(tm.get("print_sent"), toast_type='success', duration=2000)
                toast.show_toast(self)
        except Exception as e:
            QMessageBox.warning(self, tm.get("print_error_title"), tm.get("print_error_msg", str(e)))

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
        doc = None
        try:
            doc = fitz.open(self._current_preview_path)
            if doc.is_encrypted:
                if not self._current_preview_password or not doc.authenticate(self._current_preview_password):
                    self.preview_label.setText(
                        tm.get("preview_password_wrong") if self._current_preview_password else tm.get("preview_encrypted")
                    )
                    self._reset_preview_state()
                    return
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
        except Exception as e:
            logger.warning(f"Preview render error: {e}")
        finally:
            if doc:
                doc.close()

    def _on_list_item_clicked(self, item):
        """리스트 아이템 클릭 시 미리보기 업데이트"""
        path = item.data(Qt.ItemDataRole.UserRole)
        self._update_preview(path)

    def _set_preview_navigation_enabled(self, enabled: bool):
        """미리보기 네비게이션 활성화/비활성화"""
        self.btn_prev_page.setEnabled(enabled)
        self.btn_next_page.setEnabled(enabled)
        self.btn_print_preview.setEnabled(enabled)
        if not enabled:
            self.page_counter.setText("0 / 0")

    def _reset_preview_state(self):
        """미리보기 상태 초기화"""
        self.preview_image.clear()
        self._current_preview_path = ""
        self._preview_total_pages = 0
        self._current_preview_page = 0
        self._current_preview_password = None
        self._set_preview_navigation_enabled(False)

    def _prompt_pdf_password(self, path: str):
        """암호화된 PDF 비밀번호 요청"""
        password, ok = QInputDialog.getText(
            self,
            tm.get("password_title"),
            tm.get("password_msg").format(os.path.basename(path)),
            QLineEdit.EchoMode.Password
        )
        if not ok or not password:
            return None
        return password

    def _open_preview_document(self, path: str):
        """미리보기용 PDF 열기 (암호화 대응)"""
        try:
            doc = fitz.open(path)
        except Exception:
            return None, "error"
        
        if not doc.is_encrypted:
            return doc, None
        
        doc.close()
        while True:
            password = self._prompt_pdf_password(path)
            if not password:
                self._current_preview_password = None
                return None, "cancelled"
            doc = fitz.open(path)
            if doc.authenticate(password):
                self._current_preview_password = password
                return doc, None
            doc.close()
            retry = QMessageBox.question(
                self,
                tm.get("password_title"),
                tm.get("password_retry"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if retry != QMessageBox.StandardButton.Yes:
                self._current_preview_password = None
                return None, "wrong"

    def _update_preview(self, path):
        if not path or not os.path.exists(path):
            self.preview_label.setText(tm.get("preview_default"))
            self._reset_preview_state()
            return
        
        # 최근 파일 목록 업데이트
        self._add_to_recent_files(path)
        
        try:
            self._current_preview_password = None
            doc, locked_state = self._open_preview_document(path)
            if not doc:
                if locked_state == "error":
                    raise RuntimeError(tm.get("err_pdf_corrupted"))
                if locked_state == "wrong":
                    self.preview_label.setText(tm.get("preview_password_wrong"))
                else:
                    self.preview_label.setText(tm.get("preview_encrypted"))
                self._reset_preview_state()
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
            self._set_preview_navigation_enabled(True)
            
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
            self._reset_preview_state()

    def _add_to_recent_files(self, path):
        """최근 파일 목록에 추가"""
        from ..core.constants import RECENT_FILES_MAX
        recent = self.settings.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.settings["recent_files"] = recent[:RECENT_FILES_MAX]  # v4.5: 상수 사용
        save_settings(self.settings)
