from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QResizeEvent
from ...core.i18n import tm


class LoadingSpinner(QLabel):
    """
    간단한 로딩 스피너 (텍스트 기반)
    실제 애니메이션 대신 이모지 회전으로 표현
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("⏳")
        self.setStyleSheet("font-size: 24px; background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._frames = ["⏳", "⌛"]
        self._current_frame = 0

        from PyQt6.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        """애니메이션 시작"""
        self._timer.start(500)
        self.show()

    def stop(self):
        """애니메이션 중지"""
        self._timer.stop()
        self.hide()

    def _animate(self):
        """프레임 전환"""
        self._current_frame = (self._current_frame + 1) % len(self._frames)
        self.setText(self._frames[self._current_frame])
