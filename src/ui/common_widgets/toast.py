from __future__ import annotations

import logging
import os
from typing import Any

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.optional_deps import FITZ_AVAILABLE, fitz
from ...core.pdf_validation import validate_pdf_file
from ...core.settings import load_settings

logger = logging.getLogger(__name__)


class ToastWidget(QFrame):
    """비차단형 토스트 알림 위젯 (페이드 애니메이션 + 스택)"""
    closed = pyqtSignal()
    _active_toasts = []  # 활성 토스트 스택 관리

    def __init__(self, message, toast_type='info', duration=3000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # 색상 맵
        colors = {
            'success': ('#00d9a0', '#0a3a2a'),
            'error': ('#ff6b6b', '#3a1a1a'),
            'warning': ('#ffb347', '#3a2a1a'),
            'info': ('#5dade2', '#1a2a3a')
        }
        fg, bg = colors.get(toast_type, colors['info'])

        # 아이콘 맵
        icons = {'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
        icon = icons.get(toast_type, 'ℹ️')

        # 향상된 스타일 (v4.1)
        self.setStyleSheet(f"""
            ToastWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg}, stop:1 rgba(0,0,0,0.95));
                border: 2px solid {fg};
                border-radius: 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 22px; background: transparent;")
        layout.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"""
            color: {fg};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            letter-spacing: 0.3px;
        """)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {fg};
                border: none;
                font-size: 20px;
                font-weight: bold;
                border-radius: 13px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.15);
            }}
        """)
        close_btn.clicked.connect(self.close_toast)
        layout.addWidget(close_btn)

        self.setFixedWidth(380)
        self.adjustSize()

        # Import here to avoid circular import
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
        from PyQt6.QtWidgets import QGraphicsOpacityEffect

        # Opacity effect for fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        # Fade in animation
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade out animation
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out.finished.connect(self._on_fade_out_done)

        # Auto close timer
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close_toast)

    def show_toast(self, parent_widget=None):
        """토스트 표시 (스택 위치 자동 계산)"""
        self._parent_widget = parent_widget  # 부모 윈도우 참조 저장
        ToastWidget._active_toasts.append(self)

        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.right() - self.width() - 20
            y = parent_geo.bottom() - 60

            # 같은 부모에 속한 토스트만 계산하여 스택 오프셋 적용
            for toast in ToastWidget._active_toasts[:-1]:
                if toast.isVisible() and getattr(toast, '_parent_widget', None) == parent_widget:
                    y -= toast.height() + 10

            self.move(x, y)

        self.show()
        self.fade_in.start()
        self.close_timer.start(self.duration)

    def close_toast(self):
        """토스트 닫기 (페이드 아웃)"""
        self.close_timer.stop()
        self.fade_out.start()

    def _on_fade_out_done(self):
        """페이드 아웃 완료 후 정리"""
        if self in ToastWidget._active_toasts:
            ToastWidget._active_toasts.remove(self)
        self.closed.emit()
        self.hide()
        self.deleteLater()
