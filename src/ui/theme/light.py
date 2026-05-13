from __future__ import annotations

LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI', 'Malgun Gothic', -apple-system, sans-serif;
    font-size: 14px;
}

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

QToolTip {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #4f8cff;
    padding: 10px 14px;
    border-radius: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    selection-background-color: #4f8cff;
    color: #1e293b;
    border-radius: 8px;
}

QSplitter::handle {
    background: #e2e8f0;
}
QSplitter::handle:hover {
    background: #4f8cff;
}

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

QFrame {
    background-color: #ffffff;
    border: none;
}
QFrame#statusFrame {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
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

QPushButton#accentBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f8cff, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 10px 18px;
}

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
