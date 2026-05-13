from __future__ import annotations

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0a0e14;
    color: #f0f4f8;
    font-family: 'Segoe UI', 'Malgun Gothic', -apple-system, sans-serif;
    font-size: 14px;
}

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

QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    outline: none;
}

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

QToolTip {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    color: #f0f4f8;
    border: 1px solid #4f8cff;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
}

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

QSplitter::handle {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.4 #2d3748, stop:0.6 #2d3748, stop:1 transparent);
    width: 6px;
}
QSplitter::handle:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.4 #4f8cff, stop:0.6 #4f8cff, stop:1 transparent);
}

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

QFrame#statusFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c2432, stop:1 #141922);
    border-top: 1px solid #2d3748;
    border-radius: 0px;
}

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
