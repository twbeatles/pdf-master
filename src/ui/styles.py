
# -------------------------------------------------------------------------
# UI Colors & Fonts Constants
# -------------------------------------------------------------------------
class ThemeColors:
    # Common
    DARK_BG = "#1a1a2e"
    DARK_PANE = "#16213e"
    DARK_ACCENT = "#e94560"
    DARK_TEXT = "#eaeaea"
    
    LIGHT_BG = "#f5f5f5"
    LIGHT_PANE = "#fff"
    LIGHT_ACCENT = "#e94560"
    LIGHT_TEXT = "#333"
    
    BTN_GRADIENT_START = "#e94560"
    BTN_GRADIENT_END = "#c73e54"
    BTN_HOVER_START = "#ff5a7a"

# -------------------------------------------------------------------------
# Stylesheets
# -------------------------------------------------------------------------
DARK_STYLESHEET = """
QMainWindow, QWidget { background-color: #1a1a2e; color: #eaeaea; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 14px; }
QTabWidget::pane { border: 1px solid #16213e; background: #16213e; border-radius: 8px; }
QTabBar::tab { background: #0f3460; color: #aaa; padding: 12px 28px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 500; }
QTabBar::tab:selected { background: #16213e; color: #fff; font-weight: bold; border-bottom: 3px solid #e94560; }
QTabBar::tab:hover { background: #1a4a7a; }
QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e94560, stop:1 #c73e54); color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5a7a, stop:1 #e94560); }
QPushButton:pressed { background: #c73e54; }
QPushButton:disabled { background: #555; color: #888; }
QPushButton#secondaryBtn { background: #0f3460; border: 1px solid #1a4a7a; color: white; }
QPushButton#secondaryBtn:hover { background: #1a4a7a; color: white; }
QPushButton#actionBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); font-size: 16px; padding: 14px; }
QPushButton#actionBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00f0b0, stop:1 #00d9a0); }
QListWidget, QLineEdit, QSpinBox, QComboBox { background-color: #0f0f23; border: 2px solid #16213e; border-radius: 6px; padding: 8px; color: #eaeaea; }
QListWidget::item { padding: 10px; border-bottom: 1px solid #1a1a2e; }
QListWidget::item:selected { background: #e94560; border-radius: 4px; }
QListWidget::item:hover { background: #16213e; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #e94560; }
QProgressBar { border: none; border-radius: 6px; text-align: center; background-color: #0f0f23; color: white; font-weight: bold; height: 20px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff7b9a); border-radius: 6px; }
QGroupBox { border: 2px solid #16213e; border-radius: 10px; margin-top: 12px; padding-top: 18px; font-weight: bold; color: #e94560; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 15px; }
QLabel#header { font-size: 29px; font-weight: 800; color: #e94560; }
QLabel#desc { color: #888; font-size: 13px; }
QLabel#stepLabel { color: #00d9a0; font-size: 14px; font-weight: bold; }
QScrollArea { border: none; background: transparent; }
QToolTip { background-color: #16213e; color: #eaeaea; border: 1px solid #e94560; padding: 8px; border-radius: 4px; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #e94560; }
QComboBox QAbstractItemView { background-color: #0f0f23; border: 1px solid #16213e; selection-background-color: #e94560; }
QSpinBox::up-button, QSpinBox::down-button { background: #16213e; border: none; width: 20px; }
QSpinBox::up-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #e94560; }
QSpinBox::down-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #e94560; }
QSplitter::handle { background: #16213e; }
QMenu { background-color: #16213e; border: 1px solid #0f3460; border-radius: 6px; }
QMenu::item { padding: 8px 25px; }
QMenu::item:selected { background-color: #e94560; }
"""

LIGHT_STYLESHEET = """
QMainWindow, QWidget { background-color: #f5f5f5; color: #333; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 14px; }
QTabWidget::pane { border: 1px solid #ddd; background: #fff; border-radius: 8px; }
QTabBar::tab { background: #e8e8e8; color: #666; padding: 12px 28px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 500; }
QTabBar::tab:selected { background: #fff; color: #333; font-weight: bold; border-bottom: 3px solid #e94560; }
QTabBar::tab:hover { background: #f0f0f0; }
QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e94560, stop:1 #c73e54); color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5a7a, stop:1 #e94560); }
QPushButton#secondaryBtn { background: #fff; border: 2px solid #ddd; color: #333; }
QPushButton#secondaryBtn:hover { background: #f8f8f8; border-color: #e94560; }
QPushButton#actionBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); font-size: 16px; padding: 14px; }
QListWidget, QLineEdit, QSpinBox, QComboBox { background-color: #fff; border: 2px solid #ddd; border-radius: 6px; padding: 8px; color: #333; }
QListWidget::item:selected { background: #e94560; color: white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #e94560; }
QProgressBar { border: none; border-radius: 6px; text-align: center; background-color: #e8e8e8; color: #333; font-weight: bold; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff7b9a); border-radius: 6px; }
QGroupBox { border: 2px solid #ddd; border-radius: 10px; margin-top: 12px; padding-top: 18px; font-weight: bold; color: #e94560; background-color: #fff; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 15px; background-color: #fff; }
QLabel { color: #333; background: transparent; }
QLabel#header { font-size: 29px; font-weight: 800; color: #e94560; }
QLabel#desc { color: #666; font-size: 13px; }
QLabel#stepLabel { color: #00a080; font-size: 14px; font-weight: bold; }
QFrame { background-color: #fff; border: 2px dashed #ccc; border-radius: 8px; }
QScrollArea { background: #fff; border: none; }
QScrollArea > QWidget > QWidget { background: #fff; }
QToolTip { background-color: #fff; color: #333; border: 1px solid #e94560; padding: 8px; border-radius: 4px; }
QComboBox QAbstractItemView { background-color: #fff; border: 1px solid #ddd; selection-background-color: #e94560; color: #333; }
QSplitter::handle { background: #ddd; }
QMenu { background-color: #fff; border: 1px solid #ddd; }
QMenu::item { padding: 8px 25px; color: #333; }
QMenu::item:selected { background-color: #e94560; color: white; }
QToolButton { background: #fff; border: 2px solid #ddd; border-radius: 6px; padding: 6px; color: #333; font-size: 16px; }
QToolButton:hover { background: #f0f0f0; border-color: #e94560; }
"""
