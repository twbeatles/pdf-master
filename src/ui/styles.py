
# -------------------------------------------------------------------------
# UI Colors & Fonts Constants (v4.1 Enhanced)
# -------------------------------------------------------------------------
class ThemeColors:
    """향상된 색상 팔레트 (v4.1 Premium)"""
    # Primary Accent (통일된 파란색 - 더 생동감 있게)
    PRIMARY = "#4f8cff"
    PRIMARY_LIGHT = "#7fb3ff"
    PRIMARY_DARK = "#3a7ae8"
    PRIMARY_GLOW = "rgba(79, 140, 255, 0.4)"
    
    # Semantic Colors (더 선명하게)
    SUCCESS = "#10b981"
    SUCCESS_LIGHT = "#34d399"
    SUCCESS_DARK = "#059669"
    WARNING = "#f59e0b"
    WARNING_LIGHT = "#fbbf24"
    DANGER = "#ef4444"
    DANGER_LIGHT = "#f87171"
    DANGER_DARK = "#dc2626"
    
    # Purple accent for variety
    PURPLE = "#8b5cf6"
    PURPLE_LIGHT = "#a78bfa"
    
    # Dark Theme (더 깊은 톤)
    DARK_BG = "#0a0e14"
    DARK_CARD = "#141922"
    DARK_CARD_HOVER = "#1c2432"
    DARK_BORDER = "#2d3748"
    DARK_TEXT = "#f0f4f8"
    DARK_TEXT_SECONDARY = "#94a3b8"
    DARK_GLASS = "rgba(20, 25, 34, 0.9)"
    
    # Light Theme  
    LIGHT_BG = "#f8fafc"
    LIGHT_CARD = "#ffffff"
    LIGHT_BORDER = "#e2e8f0"
    LIGHT_TEXT = "#1e293b"
    LIGHT_TEXT_SECONDARY = "#64748b"
    LIGHT_GLASS = "rgba(255, 255, 255, 0.92)"


# -------------------------------------------------------------------------
# Dark Theme Stylesheet (v4.1 Premium)
# -------------------------------------------------------------------------
DARK_STYLESHEET = """
/* ===== 기본 스타일 ===== */
QMainWindow, QWidget { 
    background-color: #0a0e14; 
    color: #f0f4f8; 
    font-family: 'Segoe UI', 'Malgun Gothic', -apple-system, sans-serif; 
    font-size: 14px; 
}

/* ===== 탭 위젯 (모던 탭) ===== */
QTabWidget::pane { 
    border: 1px solid #2d3748; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #141922, stop:1 #0f1318);
    border-radius: 12px; 
}
QTabBar::tab { 
    background: transparent;
    color: #94a3b8; 
    padding: 14px 30px; 
    border-top-left-radius: 10px; 
    border-top-right-radius: 10px; 
    margin-right: 4px; 
    font-weight: 600; 
    border: none;
    border-bottom: 3px solid transparent;
}
QTabBar::tab:selected { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    color: #fff; 
    font-weight: 700; 
    border-bottom: 3px solid #4f8cff; 
}
QTabBar::tab:hover:!selected { 
    background: rgba(79, 140, 255, 0.1);
    color: #f0f4f8;
    border-bottom: 3px solid rgba(79, 140, 255, 0.3);
}

/* ===== 버튼 스타일 (3D 효과, 그림자) ===== */
QPushButton { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a95ff, stop:1 #4080f0); 
    color: white; 
    border: none; 
    padding: 12px 24px; 
    border-radius: 8px; 
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7fb3ff, stop:1 #5a95ff); 
}
QPushButton:pressed { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a7ae8, stop:1 #2060c0);
    padding-top: 13px;
    padding-bottom: 11px;
}
QPushButton:disabled { 
    background: #1c2432; 
    color: #4a5568; 
}

/* Secondary Button (아웃라인) */
QPushButton#secondaryBtn { 
    background: transparent; 
    border: 2px solid #4f8cff; 
    color: #4f8cff; 
}
QPushButton#secondaryBtn:hover { 
    background: rgba(79, 140, 255, 0.15);
    border-color: #7fb3ff;
    color: #7fb3ff;
}

/* Action Button (그라데이션 그린) */
QPushButton#actionBtn { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669); 
    font-size: 15px; 
    padding: 16px 28px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton#actionBtn:hover { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981); 
}
QPushButton#actionBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #059669, stop:1 #047857);
}

/* Danger Button */
QPushButton#dangerBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626); 
}
QPushButton#dangerBtn:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #ef4444); 
}

/* Icon Button (작은 아이콘 전용) */
QPushButton#iconBtn {
    background: transparent;
    border: 1px solid #2d3748;
    color: #94a3b8;
    padding: 8px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
    font-size: 16px;
}
QPushButton#iconBtn:hover {
    background: rgba(79, 140, 255, 0.15);
    border-color: #4f8cff;
    color: #4f8cff;
}
QPushButton#iconBtn:pressed {
    background: rgba(79, 140, 255, 0.25);
}

/* Ghost Button (텍스트 전용) */
QPushButton#ghostBtn {
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton#ghostBtn:hover {
    color: #f0f4f8;
    background: rgba(255, 255, 255, 0.05);
}

/* Success Button */
QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981);
}

/* Warning Button */
QPushButton#warningBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
    color: #1a1a2e;
}
QPushButton#warningBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #f59e0b);
}

/* ===== 포커스 링 (접근성) ===== */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    outline: none;
}

/* ===== 입력 위젯 (네온 포커스) ===== */
QListWidget, QLineEdit, QSpinBox, QComboBox, QTextEdit { 
    background-color: #0f1318; 
    border: 2px solid #2d3748; 
    border-radius: 8px; 
    padding: 10px 12px; 
    color: #f0f4f8;
    selection-background-color: #4f8cff;
}
QListWidget::item { 
    padding: 12px; 
    border-bottom: 1px solid #1c2432;
    border-radius: 6px;
    margin: 2px;
}
QListWidget::item:selected { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 6px; 
}
QListWidget::item:hover:!selected { 
    background: #1c2432;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { 
    border: 2px solid #4f8cff;
    background-color: #141922;
}

/* ===== 진행 바 (애니메이션 느낌) ===== */
QProgressBar { 
    border: none; 
    border-radius: 8px; 
    text-align: center; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    color: white; 
    font-weight: 700; 
    height: 24px;
    font-size: 11px;
}
QProgressBar::chunk { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:0.5 #7fb3ff, stop:1 #4f8cff);
    border-radius: 8px; 
}

/* ===== 그룹 박스 (글래스모피즘 강화) ===== */
QGroupBox { 
    border: 1px solid rgba(79, 140, 255, 0.2); 
    border-radius: 16px; 
    margin-top: 16px; 
    padding: 24px 16px 16px 16px;
    font-weight: 700;
    font-size: 13px;
    color: #7fb3ff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 36, 50, 0.95), stop:1 rgba(20, 25, 34, 0.9));
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left; 
    padding: 4px 16px; 
    left: 20px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 6px;
    color: white;
    font-size: 12px;
}

/* ===== 라벨 ===== */
QLabel { 
    background: transparent; 
}
QLabel#header { 
    font-size: 32px; 
    font-weight: 800; 
    color: #4f8cff;
    letter-spacing: -0.5px;
}
QLabel#desc { 
    color: #94a3b8; 
    font-size: 13px;
    line-height: 1.5;
}
QLabel#stepLabel { 
    color: #10b981; 
    font-size: 14px; 
    font-weight: 700;
    letter-spacing: 0.3px;
}

/* ===== 스크롤 영역 ===== */
QScrollArea { 
    border: none; 
    background: transparent; 
}
QScrollBar:vertical {
    background: #0f1318;
    width: 10px;
    border-radius: 5px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #3a7ae8);
    border-radius: 5px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7fb3ff, stop:1 #4f8cff);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0f1318;
    height: 10px;
    border-radius: 5px;
    margin: 4px;
}
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f8cff, stop:1 #3a7ae8);
    border-radius: 5px;
    min-width: 40px;
}

/* ===== 툴팁 (모던) ===== */
QToolTip { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    color: #f0f4f8; 
    border: 1px solid #4f8cff; 
    padding: 10px 14px; 
    border-radius: 8px;
    font-size: 12px;
}

/* ===== 콤보박스 ===== */
QComboBox::drop-down { 
    border: none; 
    width: 32px;
    background: transparent;
}
QComboBox::down-arrow { 
    image: none; 
    border-left: 5px solid transparent; 
    border-right: 5px solid transparent; 
    border-top: 6px solid #4f8cff; 
}
QComboBox QAbstractItemView { 
    background-color: #141922; 
    border: 1px solid #2d3748; 
    selection-background-color: #4f8cff;
    border-radius: 8px;
    padding: 4px;
}

/* ===== 스핀박스 ===== */
QSpinBox::up-button, QSpinBox::down-button { 
    background: #1c2432; 
    border: none; 
    width: 24px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #4f8cff;
}
QSpinBox::up-arrow { 
    border-left: 4px solid transparent; 
    border-right: 4px solid transparent; 
    border-bottom: 5px solid #4f8cff; 
}
QSpinBox::down-arrow { 
    border-left: 4px solid transparent; 
    border-right: 4px solid transparent; 
    border-top: 5px solid #4f8cff; 
}
QSpinBox::up-button:hover QSpinBox::up-arrow,
QSpinBox::down-button:hover QSpinBox::down-arrow {
    border-bottom-color: white;
    border-top-color: white;
}

/* ===== 스플리터 ===== */
QSplitter::handle { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.4 #2d3748, stop:0.6 #2d3748, stop:1 transparent);
    width: 6px;
}
QSplitter::handle:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.4 #4f8cff, stop:0.6 #4f8cff, stop:1 transparent);
}

/* ===== 메뉴 ===== */
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    border-bottom: 1px solid #2d3748;
    padding: 4px;
}
QMenuBar::item {
    padding: 10px 16px;
    background: transparent;
    border-radius: 6px;
    margin: 2px;
}
QMenuBar::item:selected {
    background: rgba(79, 140, 255, 0.2);
}
QMenu { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    border: 1px solid #2d3748; 
    border-radius: 12px;
    padding: 8px;
}
QMenu::item { 
    padding: 10px 28px;
    border-radius: 6px;
    margin: 2px 4px;
}
QMenu::item:selected { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
}
QMenu::separator {
    height: 1px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.2 #2d3748, stop:0.8 #2d3748, stop:1 transparent);
    margin: 8px 16px;
}

/* ===== 프레임 ===== */
QFrame#statusFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    border-top: 1px solid #2d3748;
    border-radius: 0px;
}

/* ===== 네비게이션 버튼 ===== */
QPushButton#navBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a95ff, stop:1 #4080f0);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 8px 14px;
}
QPushButton#navBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7fb3ff, stop:1 #5a95ff);
}

/* ===== 액센트 버튼 (헤더) ===== */
QPushButton#accentBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f8cff, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 10px 18px;
}
QPushButton#accentBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7fb3ff, stop:1 #a78bfa);
}

/* ===== 텍스트 에디트 ===== */
QTextEdit {
    background: #0f1318;
    border: 2px solid #2d3748;
    border-radius: 8px;
    padding: 12px;
    color: #f0f4f8;
    line-height: 1.6;
}
QTextEdit:focus {
    border-color: #4f8cff;
}

/* ===== 슬라이더 ===== */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #1c2432;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f8cff, stop:1 #3a7ae8);
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7fb3ff, stop:1 #4f8cff);
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 3px;
}
"""

# -------------------------------------------------------------------------
# Light Theme Stylesheet (v4.1 Premium)
# -------------------------------------------------------------------------
LIGHT_STYLESHEET = """
/* ===== 기본 스타일 ===== */
QMainWindow, QWidget { 
    background-color: #f8fafc; 
    color: #1e293b; 
    font-family: 'Segoe UI', 'Malgun Gothic', -apple-system, sans-serif; 
    font-size: 14px; 
}

/* ===== 탭 위젯 ===== */
QTabWidget::pane { 
    border: 1px solid #e2e8f0; 
    background: #ffffff; 
    border-radius: 12px; 
}
QTabBar::tab { 
    background: transparent;
    color: #64748b; 
    padding: 14px 30px; 
    border-top-left-radius: 10px; 
    border-top-right-radius: 10px; 
    margin-right: 4px; 
    font-weight: 600;
    border: none;
    border-bottom: 3px solid transparent;
}
QTabBar::tab:selected { 
    background: #ffffff;
    color: #1e293b; 
    font-weight: 700; 
    border-bottom: 3px solid #4f8cff; 
}
QTabBar::tab:hover:!selected { 
    background: rgba(79, 140, 255, 0.08);
    border-bottom: 3px solid rgba(79, 140, 255, 0.3);
}

/* ===== 버튼 스타일 ===== */
QPushButton { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a95ff, stop:1 #4080f0); 
    color: white; 
    border: none; 
    padding: 12px 24px; 
    border-radius: 8px; 
    font-weight: 600; 
}
QPushButton:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7fb3ff, stop:1 #5a95ff); 
}
QPushButton:disabled { 
    background: #e2e8f0; 
    color: #94a3b8; 
}

/* Secondary Button */
QPushButton#secondaryBtn { 
    background: #ffffff; 
    border: 2px solid #e2e8f0; 
    color: #475569; 
}
QPushButton#secondaryBtn:hover { 
    background: #f1f5f9;
    border-color: #4f8cff;
    color: #4f8cff;
}

/* Action Button */
QPushButton#actionBtn { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669); 
    font-size: 15px; 
    padding: 16px 28px;
    font-weight: 700;
}

/* Danger Button */
QPushButton#dangerBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626); 
}

/* Icon Button (작은 아이콘 전용) */
QPushButton#iconBtn {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    color: #64748b;
    padding: 8px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
    font-size: 16px;
}
QPushButton#iconBtn:hover {
    background: rgba(79, 140, 255, 0.1);
    border-color: #4f8cff;
    color: #4f8cff;
}

/* Ghost Button (텍스트 전용) */
QPushButton#ghostBtn {
    background: transparent;
    border: none;
    color: #64748b;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton#ghostBtn:hover {
    color: #1e293b;
    background: rgba(0, 0, 0, 0.05);
}

/* Success Button */
QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
}

/* Warning Button */
QPushButton#warningBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
    color: #1a1a2e;
}

/* ===== 입력 위젯 ===== */
QListWidget, QLineEdit, QSpinBox, QComboBox, QTextEdit { 
    background-color: #ffffff; 
    border: 2px solid #e2e8f0; 
    border-radius: 8px; 
    padding: 10px 12px; 
    color: #1e293b; 
}
QListWidget::item:selected { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    color: white; 
}
QListWidget::item:hover:!selected {
    background: #f1f5f9;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { 
    border: 2px solid #4f8cff; 
}

/* ===== 진행 바 ===== */
QProgressBar { 
    border: none; 
    border-radius: 8px; 
    text-align: center; 
    background-color: #e2e8f0; 
    color: #1e293b; 
    font-weight: 700; 
    height: 24px;
}
QProgressBar::chunk { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:0.5 #7fb3ff, stop:1 #4f8cff);
    border-radius: 8px; 
}

/* ===== 그룹 박스 ===== */
QGroupBox { 
    border: 1px solid #e2e8f0; 
    border-radius: 16px; 
    margin-top: 16px; 
    padding: 24px 16px 16px 16px;
    font-weight: 700; 
    color: #4f8cff; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.98), stop:1 rgba(248, 250, 252, 0.95));
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left; 
    padding: 4px 16px; 
    left: 20px; 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 6px;
    color: white;
    font-size: 12px;
}

/* ===== 라벨 ===== */
QLabel { 
    color: #1e293b; 
    background: transparent; 
}
QLabel#header { 
    font-size: 32px; 
    font-weight: 800; 
    color: #4f8cff; 
}
QLabel#desc { 
    color: #64748b; 
    font-size: 13px; 
}
QLabel#stepLabel { 
    color: #059669; 
    font-size: 14px; 
    font-weight: 700; 
}

/* ===== 스크롤 영역 ===== */
QScrollArea { 
    background: #ffffff; 
    border: none; 
}
QScrollArea > QWidget > QWidget { 
    background: #ffffff; 
}
QScrollBar:vertical {
    background: #f1f5f9;
    width: 10px;
    border-radius: 5px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 5px;
    min-height: 40px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== 툴팁 ===== */
QToolTip { 
    background-color: #ffffff; 
    color: #1e293b; 
    border: 1px solid #4f8cff; 
    padding: 10px 14px; 
    border-radius: 8px; 
}

/* ===== 콤보박스 ===== */
QComboBox QAbstractItemView { 
    background-color: #ffffff; 
    border: 1px solid #e2e8f0; 
    selection-background-color: #4f8cff; 
    color: #1e293b; 
    border-radius: 8px;
}

/* ===== 스플리터 ===== */
QSplitter::handle { 
    background: #e2e8f0; 
}
QSplitter::handle:hover {
    background: #4f8cff;
}

/* ===== 메뉴 ===== */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
}
QMenuBar::item {
    padding: 10px 16px;
    border-radius: 6px;
    margin: 2px;
}
QMenuBar::item:selected {
    background: rgba(79, 140, 255, 0.1);
}
QMenu { 
    background-color: #ffffff; 
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 8px;
}
QMenu::item { 
    padding: 10px 28px; 
    color: #1e293b;
    border-radius: 6px;
    margin: 2px 4px;
}
QMenu::item:selected { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    color: white; 
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 8px 16px;
}

/* ===== 툴버튼 ===== */
QToolButton { 
    background: #ffffff; 
    border: 2px solid #e2e8f0; 
    border-radius: 8px; 
    padding: 8px; 
    color: #475569; 
    font-size: 16px; 
}
QToolButton:hover { 
    background: #f1f5f9; 
    border-color: #4f8cff;
    color: #4f8cff;
}

/* ===== 프레임 ===== */
QFrame { 
    background-color: #ffffff; 
    border: none;
}
QFrame#statusFrame {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
}

/* ===== 네비게이션 버튼 ===== */
QPushButton#navBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a95ff, stop:1 #4080f0);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 8px 14px;
}

/* ===== 액센트 버튼 ===== */
QPushButton#accentBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f8cff, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 10px 18px;
}

/* ===== 슬라이더 ===== */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f8cff, stop:1 #3a7ae8);
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7fb3ff);
    border-radius: 3px;
}
"""
