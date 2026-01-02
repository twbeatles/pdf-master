
# -------------------------------------------------------------------------
# UI Colors & Fonts Constants
# -------------------------------------------------------------------------
class ThemeColors:
    """향상된 색상 팔레트 (v3.3 통일 테마)"""
    # Primary Accent (통일된 파란색)
    PRIMARY = "#4f8cff"
    PRIMARY_LIGHT = "#6ba0ff"
    PRIMARY_DARK = "#3a7ae8"
    
    # Semantic Colors
    SUCCESS = "#00d9a0"
    SUCCESS_DARK = "#00b886"
    WARNING = "#f0a020"
    DANGER = "#ff6b6b"
    DANGER_DARK = "#dc2626"
    
    # Dark Theme
    DARK_BG = "#0d1117"
    DARK_CARD = "#161b22"
    DARK_BORDER = "#30363d"
    DARK_TEXT = "#e6edf3"
    DARK_TEXT_SECONDARY = "#8b949e"
    DARK_GLASS = "rgba(22, 27, 34, 0.85)"
    
    # Light Theme
    LIGHT_BG = "#f6f8fa"
    LIGHT_CARD = "#ffffff"
    LIGHT_BORDER = "#d0d7de"
    LIGHT_TEXT = "#1f2328"
    LIGHT_TEXT_SECONDARY = "#656d76"
    LIGHT_GLASS = "rgba(255, 255, 255, 0.85)"
    
    # Button Gradients (v3.3)
    BTN_GRADIENT_START = "#4f8cff"
    BTN_GRADIENT_END = "#3a7ae8"
    BTN_HOVER_START = "#6ba0ff"


# -------------------------------------------------------------------------
# Dark Theme Stylesheet
# -------------------------------------------------------------------------
DARK_STYLESHEET = """
/* ===== 기본 스타일 ===== */
QMainWindow, QWidget { 
    background-color: #0d1117; 
    color: #e6edf3; 
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; 
    font-size: 14px; 
}

/* ===== 탭 위젯 ===== */
QTabWidget::pane { 
    border: 1px solid #30363d; 
    background: #161b22; 
    border-radius: 8px; 
}
QTabBar::tab { 
    background: #21262d; 
    color: #8b949e; 
    padding: 12px 28px; 
    border-top-left-radius: 8px; 
    border-top-right-radius: 8px; 
    margin-right: 3px; 
    font-weight: 500; 
    border: 1px solid transparent;
    border-bottom: none;
}
QTabBar::tab:selected { 
    background: #161b22; 
    color: #fff; 
    font-weight: bold; 
    border: 1px solid #30363d;
    border-bottom: 3px solid #4f8cff; 
}
QTabBar::tab:hover:!selected { 
    background: #30363d; 
    color: #e6edf3;
}

/* ===== 버튼 스타일 ===== */
QPushButton { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f8cff, stop:1 #3a7ae8); 
    color: white; 
    border: none; 
    padding: 10px 20px; 
    border-radius: 6px; 
    font-weight: 600; 
}
QPushButton:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6ba0ff, stop:1 #4f8cff); 
}
QPushButton:pressed { 
    background: #3a7ae8; 
}
QPushButton:disabled { 
    background: #21262d; 
    color: #484f58; 
}

/* Secondary Button */
QPushButton#secondaryBtn { 
    background: #21262d; 
    border: 1px solid #30363d; 
    color: #e6edf3; 
}
QPushButton#secondaryBtn:hover { 
    background: #30363d; 
    border-color: #8b949e;
}

/* Action Button (Green) */
QPushButton#actionBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); 
    font-size: 15px; 
    padding: 14px;
    font-weight: bold;
}
QPushButton#actionBtn:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00f0b0, stop:1 #00d9a0); 
}

/* Danger Button (Red) */
QPushButton#dangerBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b6b, stop:1 #dc2626); 
}
QPushButton#dangerBtn:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff8787, stop:1 #ff6b6b); 
}

/* ===== 입력 위젯 ===== */
QListWidget, QLineEdit, QSpinBox, QComboBox { 
    background-color: #0d1117; 
    border: 1px solid #30363d; 
    border-radius: 6px; 
    padding: 8px; 
    color: #e6edf3;
    selection-background-color: #4f8cff;
}
QListWidget::item { 
    padding: 10px; 
    border-bottom: 1px solid #21262d;
    border-radius: 4px;
}
QListWidget::item:selected { 
    background: #4f8cff; 
    border-radius: 4px; 
}
QListWidget::item:hover:!selected { 
    background: #21262d; 
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { 
    border: 1px solid #4f8cff;
    background-color: #161b22;
}

/* ===== 진행 바 ===== */
QProgressBar { 
    border: none; 
    border-radius: 6px; 
    text-align: center; 
    background-color: #21262d; 
    color: white; 
    font-weight: bold; 
    height: 20px; 
}
QProgressBar::chunk { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #6ba0ff); 
    border-radius: 6px; 
}

/* ===== 그룹 박스 (글래스모피즘) ===== */
QGroupBox { 
    border: 1px solid #30363d; 
    border-radius: 12px; 
    margin-top: 12px; 
    padding: 20px 14px 14px 14px;
    font-weight: bold; 
    color: #4f8cff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(22, 27, 34, 0.95), stop:1 rgba(13, 17, 23, 0.9));
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left; 
    padding: 2px 12px; 
    left: 15px;
    background: #161b22;
    border-radius: 4px;
}

/* ===== 라벨 ===== */
QLabel#header { 
    font-size: 28px; 
    font-weight: 800; 
    color: #4f8cff; 
}
QLabel#desc { 
    color: #8b949e; 
    font-size: 13px; 
}
QLabel#stepLabel { 
    color: #00d9a0; 
    font-size: 14px; 
    font-weight: bold; 
}

/* ===== 스크롤 영역 ===== */
QScrollArea { 
    border: none; 
    background: transparent; 
}
QScrollBar:vertical {
    background: #161b22;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #161b22;
    height: 12px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 6px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #484f58;
}

/* ===== 툴팁 ===== */
QToolTip { 
    background-color: #161b22; 
    color: #e6edf3; 
    border: 1px solid #4f8cff; 
    padding: 8px; 
    border-radius: 6px;
    font-size: 12px;
}

/* ===== 콤보박스 ===== */
QComboBox::drop-down { 
    border: none; 
    width: 30px; 
}
QComboBox::down-arrow { 
    image: none; 
    border-left: 5px solid transparent; 
    border-right: 5px solid transparent; 
    border-top: 6px solid #4f8cff; 
}
QComboBox QAbstractItemView { 
    background-color: #161b22; 
    border: 1px solid #30363d; 
    selection-background-color: #4f8cff;
    border-radius: 6px;
}

/* ===== 스핀박스 ===== */
QSpinBox::up-button, QSpinBox::down-button { 
    background: #21262d; 
    border: none; 
    width: 20px; 
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #30363d;
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

/* ===== 스플리터 ===== */
QSplitter::handle { 
    background: #30363d;
    width: 2px;
}
QSplitter::handle:hover {
    background: #4f8cff;
}

/* ===== 메뉴 ===== */
QMenuBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
}
QMenuBar::item {
    padding: 8px 12px;
    background: transparent;
}
QMenuBar::item:selected {
    background: #30363d;
    border-radius: 4px;
}
QMenu { 
    background-color: #161b22; 
    border: 1px solid #30363d; 
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { 
    padding: 8px 25px;
    border-radius: 4px;
    margin: 2px 4px;
}
QMenu::item:selected { 
    background-color: #4f8cff; 
}
QMenu::separator {
    height: 1px;
    background: #30363d;
    margin: 4px 10px;
}

/* ===== 프레임 ===== */
QFrame#statusFrame {
    background-color: #161b22;
    border-top: 1px solid #30363d;
}
"""

# -------------------------------------------------------------------------
# Light Theme Stylesheet
# -------------------------------------------------------------------------
LIGHT_STYLESHEET = """
/* ===== 기본 스타일 ===== */
QMainWindow, QWidget { 
    background-color: #f6f8fa; 
    color: #1f2328; 
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; 
    font-size: 14px; 
}

/* ===== 탭 위젯 ===== */
QTabWidget::pane { 
    border: 1px solid #d0d7de; 
    background: #fff; 
    border-radius: 8px; 
}
QTabBar::tab { 
    background: #f6f8fa; 
    color: #656d76; 
    padding: 12px 28px; 
    border-top-left-radius: 8px; 
    border-top-right-radius: 8px; 
    margin-right: 3px; 
    font-weight: 500;
    border: 1px solid #d0d7de;
    border-bottom: none;
}
QTabBar::tab:selected { 
    background: #fff; 
    color: #1f2328; 
    font-weight: bold; 
    border-bottom: 3px solid #4f8cff; 
}
QTabBar::tab:hover:!selected { 
    background: #eaeef2; 
}

/* ===== 버튼 스타일 ===== */
QPushButton { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f8cff, stop:1 #3a7ae8); 
    color: white; 
    border: none; 
    padding: 10px 20px; 
    border-radius: 6px; 
    font-weight: 600; 
}
QPushButton:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6ba0ff, stop:1 #4f8cff); 
}
QPushButton:disabled { 
    background: #eaeef2; 
    color: #8c959f; 
}

/* Secondary Button */
QPushButton#secondaryBtn { 
    background: #fff; 
    border: 1px solid #d0d7de; 
    color: #1f2328; 
}
QPushButton#secondaryBtn:hover { 
    background: #f6f8fa; 
    border-color: #4f8cff; 
}

/* Action Button (Green) */
QPushButton#actionBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); 
    font-size: 15px; 
    padding: 14px; 
}

/* Danger Button */
QPushButton#dangerBtn { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b6b, stop:1 #dc2626); 
}

/* ===== 입력 위젯 ===== */
QListWidget, QLineEdit, QSpinBox, QComboBox { 
    background-color: #fff; 
    border: 1px solid #d0d7de; 
    border-radius: 6px; 
    padding: 8px; 
    color: #1f2328; 
}
QListWidget::item:selected { 
    background: #4f8cff; 
    color: white; 
}
QListWidget::item:hover:!selected {
    background: #f6f8fa;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { 
    border: 1px solid #4f8cff; 
}

/* ===== 진행 바 ===== */
QProgressBar { 
    border: none; 
    border-radius: 6px; 
    text-align: center; 
    background-color: #eaeef2; 
    color: #1f2328; 
    font-weight: bold; 
}
QProgressBar::chunk { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #6ba0ff); 
    border-radius: 6px; 
}

/* ===== 그룹 박스 (글래스모피즘) ===== */
QGroupBox { 
    border: 1px solid #d0d7de; 
    border-radius: 12px; 
    margin-top: 12px; 
    padding: 20px 14px 14px 14px;
    font-weight: bold; 
    color: #4f8cff; 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(246, 248, 250, 0.9));
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left; 
    padding: 2px 12px; 
    left: 15px; 
    background: #fff;
    border-radius: 4px;
}

/* ===== 라벨 ===== */
QLabel { 
    color: #1f2328; 
    background: transparent; 
}
QLabel#header { 
    font-size: 28px; 
    font-weight: 800; 
    color: #4f8cff; 
}
QLabel#desc { 
    color: #656d76; 
    font-size: 13px; 
}
QLabel#stepLabel { 
    color: #00a080; 
    font-size: 14px; 
    font-weight: bold; 
}

/* ===== 스크롤 영역 ===== */
QScrollArea { 
    background: #fff; 
    border: none; 
}
QScrollArea > QWidget > QWidget { 
    background: #fff; 
}
QScrollBar:vertical {
    background: #f6f8fa;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #d0d7de;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #8c959f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== 툴팁 ===== */
QToolTip { 
    background-color: #fff; 
    color: #1f2328; 
    border: 1px solid #4f8cff; 
    padding: 8px; 
    border-radius: 6px; 
}

/* ===== 콤보박스 ===== */
QComboBox QAbstractItemView { 
    background-color: #fff; 
    border: 1px solid #d0d7de; 
    selection-background-color: #4f8cff; 
    color: #1f2328; 
}

/* ===== 스플리터 ===== */
QSplitter::handle { 
    background: #d0d7de; 
}
QSplitter::handle:hover {
    background: #4f8cff;
}

/* ===== 메뉴 ===== */
QMenuBar {
    background-color: #fff;
    border-bottom: 1px solid #d0d7de;
}
QMenuBar::item {
    padding: 8px 12px;
}
QMenuBar::item:selected {
    background: #f6f8fa;
    border-radius: 4px;
}
QMenu { 
    background-color: #fff; 
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { 
    padding: 8px 25px; 
    color: #1f2328;
    border-radius: 4px;
    margin: 2px 4px;
}
QMenu::item:selected { 
    background-color: #4f8cff; 
    color: white; 
}
QMenu::separator {
    height: 1px;
    background: #d0d7de;
    margin: 4px 10px;
}

/* ===== 툴버튼 ===== */
QToolButton { 
    background: #fff; 
    border: 1px solid #d0d7de; 
    border-radius: 6px; 
    padding: 6px; 
    color: #1f2328; 
    font-size: 16px; 
}
QToolButton:hover { 
    background: #f6f8fa; 
    border-color: #4f8cff; 
}

/* ===== 프레임 ===== */
QFrame { 
    background-color: #fff; 
    border: none;
}
QFrame#statusFrame {
    background-color: #fff;
    border-top: 1px solid #d0d7de;
}
"""
