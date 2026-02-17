"""
Progress Overlay Widget for PDF Master
작업 진행 중 표시되는 세련된 오버레이 다이얼로그
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor


class ProgressOverlayWidget(QFrame):
    """
    풀스크린 오버레이 진행 다이얼로그
    
    Features:
        - 반투명 배경
        - 중앙 정렬된 카드 UI
        - 진행바 + 취소 버튼
        - 작업 설명 표시
    """
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark_theme = True
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        # 전체 오버레이 배경
        self.setStyleSheet("background: rgba(0, 0, 0, 0.7);")
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 중앙 카드
        self.card = QFrame()
        self.card.setFixedSize(420, 200)
        self.card.setObjectName("progressCard")
        self._apply_card_style()
        
        # 그림자 효과
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 25, 30, 25)
        card_layout.setSpacing(16)
        
        # 아이콘 + 타이틀
        header_layout = QHBoxLayout()
        self.icon_label = QLabel("⏳")
        self.icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        header_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("작업 처리 중...")
        self.title_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: 700; 
            color: #f0f4f8; 
            background: transparent;
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        card_layout.addLayout(header_layout)
        
        # 설명
        self.desc_label = QLabel("잠시만 기다려 주세요...")
        self.desc_label.setStyleSheet("""
            font-size: 13px; 
            color: #94a3b8; 
            background: transparent;
        """)
        self.desc_label.setWordWrap(True)
        card_layout.addWidget(self.desc_label)
        
        # 진행바
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #1c2432;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f8cff, stop:0.5 #7fb3ff, stop:1 #4f8cff);
                border-radius: 5px;
            }
        """)
        card_layout.addWidget(self.progress_bar)
        
        # 진행률 텍스트
        self.progress_text = QLabel("0%")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_text.setStyleSheet("""
            font-size: 12px; 
            color: #64748b; 
            font-weight: 600;
            background: transparent;
        """)
        card_layout.addWidget(self.progress_text)
        
        # 취소 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("✕ 취소")
        self.cancel_btn.setFixedSize(100, 36)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 2px solid #ef4444;
                color: #ef4444;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.15);
            }
            QPushButton:pressed {
                background: rgba(239, 68, 68, 0.25);
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.card)
    
    def _apply_card_style(self):
        if self._is_dark_theme:
            self.card.setStyleSheet("""
                #progressCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1c2432, stop:1 #141922);
                    border: 1px solid rgba(79, 140, 255, 0.3);
                    border-radius: 16px;
                }
            """)
        else:
            self.card.setStyleSheet("""
                #progressCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ffffff, stop:1 #f8fafc);
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                }
            """)
            self.title_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: 700; 
                color: #1e293b; 
                background: transparent;
            """)
            self.desc_label.setStyleSheet("""
                font-size: 13px; 
                color: #64748b; 
                background: transparent;
            """)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 5px;
                    background: #e2e8f0;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4f8cff, stop:0.5 #7fb3ff, stop:1 #4f8cff);
                    border-radius: 5px;
                }
            """)
            self.progress_text.setStyleSheet("""
                font-size: 12px; 
                color: #94a3b8; 
                font-weight: 600;
                background: transparent;
            """)
    
    def set_theme(self, is_dark: bool):
        """테마 설정"""
        self._is_dark_theme = is_dark
        if is_dark:
            self.setStyleSheet("background: rgba(0, 0, 0, 0.7);")
        else:
            self.setStyleSheet("background: rgba(0, 0, 0, 0.5);")
        self._apply_card_style()
    
    def show_progress(self, title: str = "작업 처리 중...", description: str = ""):
        """오버레이 표시"""
        self.title_label.setText(title)
        self.desc_label.setText(description or "잠시만 기다려 주세요...")
        self.progress_bar.setValue(0)
        self.progress_text.setText("0%")
        self.icon_label.setText("⏳")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("✕ 취소")
        
        # 부모 크기에 맞게 조절
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        self.show()
        self.raise_()
    
    def update_progress(self, value: int, description: str = None):
        """진행률 업데이트"""
        self.progress_bar.setValue(value)
        self.progress_text.setText(f"{value}%")
        if description:
            self.desc_label.setText(description)
        
        # 진행 상태에 따른 아이콘 변경
        if value >= 100:
            self.icon_label.setText("✅")
            self.title_label.setText("완료!")
        elif value >= 50:
            self.icon_label.setText("🔄")
    
    def hide_progress(self):
        """오버레이 숨기기"""
        self.hide()
    
    def _on_cancel(self):
        """취소 버튼 클릭"""
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("취소 중...")
        self.desc_label.setText("작업을 취소하는 중입니다...")
        self.cancelled.emit()
    
    def resizeEvent(self, event):
        """부모 크기 변경 시 오버레이도 조절"""
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())


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
