"""Scoped native-widget stylesheets for Fluent-active mode (P4a).

전역 레거시 QSS(DARK/LIGHT_STYLESHEET)는 타입 셀렉터가 Fluent 위젯
(Qt 서브클래스 + 내부 Qt 자식)까지 관통해 외관을 깨고, 누적 시
`app.setStyleSheet`에서 네이티브 크래시를 유발한다.
Fluent 활성 시에는 이 스코프드 시트만 적용한다:

- 허용: ID 셀렉터(#objectName), Fluent가 서브클래싱하지 않는 네이티브
  컨테이너(QTabWidget/QGroupBox/QListWidget/QSplitter/QProgressBar/
  QMenuBar/QMenu/QToolTip/QScrollBar/QSlider/QScrollArea/QDialog),
  QComboBox 계열(Fluent ComboBox는 QComboBox 서브클래스가 아님).
- 금지: QWidget/QMainWindow/QPushButton/QLineEdit/QSpinBox/QCheckBox/
  QTextEdit/QLabel 베이스 및 QSpinBox 서브컨트롤 (Fluent와 충돌).

DARK/LIGHT_STYLESHEET 문자열은 폴백 경로·계약 테스트용으로 유지한다.
"""

from __future__ import annotations

NATIVE_DARK_STYLESHEET = """
QWidget#advancedPage, QWidget#advancedContent {
    background-color: #141922;
    color: #f0f4f8;
}
QDialog {
    background-color: #141922;
    color: #f0f4f8;
}
QTabWidget::pane {
    border: 1px solid #2d3748;
    background: #141922;
    border-radius: 12px;
}
QTabBar::tab {
    background: transparent;
    color: #94a3b8;
    padding: 14px 30px;
    margin-right: 4px;
    font-weight: 600;
    border: none;
    border-bottom: 3px solid transparent;
}
QTabBar::tab:selected {
    background: #1c2432;
    color: #fff;
    font-weight: 700;
    border-bottom: 3px solid #4f8cff;
}
QTabBar::tab:hover:!selected {
    background: rgba(79, 140, 255, 0.1);
    color: #f0f4f8;
}
QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 12px;
    margin-top: 16px;
    padding: 24px 16px 16px 16px;
    font-weight: 700;
    font-size: 13px;
    color: #7fb3ff;
    background: #141922;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 16px;
    left: 20px;
    background: #4f8cff;
    border-radius: 6px;
    color: white;
    font-size: 12px;
}
QListWidget {
    background-color: #0f1318;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 6px;
    color: #f0f4f8;
    selection-background-color: #4f8cff;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px;
}
QListWidget::item:selected {
    background: #4f8cff;
}
QListWidget::item:hover:!selected {
    background: #1c2432;
}
QComboBox {
    background-color: #0f1318;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 10px;
    color: #f0f4f8;
    selection-background-color: #4f8cff;
}
QComboBox:focus {
    border: 1px solid #4f8cff;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
    background: transparent;
}
QComboBox QAbstractItemView {
    background-color: #141922;
    border: 1px solid #2d3748;
    selection-background-color: #4f8cff;
    border-radius: 8px;
    padding: 4px;
}
QSplitter::handle {
    background: transparent;
    width: 6px;
}
QSplitter::handle:hover {
    background: #4f8cff;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background: #1c2432;
    color: white;
    font-weight: 700;
    height: 24px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: #4f8cff;
    border-radius: 8px;
}
QMenuBar {
    background: #141922;
    color: #f0f4f8;
    border-bottom: 1px solid #2d3748;
    padding: 4px;
}
QMenuBar::item {
    padding: 10px 16px;
    background: transparent;
    color: #f0f4f8;
    border-radius: 6px;
    margin: 2px;
}
QMenuBar::item:selected {
    background: rgba(79, 140, 255, 0.2);
    color: #ffffff;
}
QMenu {
    background: #141922;
    color: #f0f4f8;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 8px;
}
QMenu::item {
    padding: 10px 28px;
    color: #f0f4f8;
    border-radius: 6px;
    margin: 2px 4px;
}
QMenu::item:selected {
    background: #4f8cff;
    color: #ffffff;
}
QMenu::item:disabled {
    background: transparent;
    color: #5b6b7f;
}
QMenu::separator {
    height: 1px;
    background: #2d3748;
    margin: 8px 16px;
}
QToolTip {
    background: #1c2432;
    color: #f0f4f8;
    border: 1px solid #4f8cff;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
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
    background: #4f8cff;
    border-radius: 5px;
    min-height: 40px;
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
    background: #4f8cff;
    border-radius: 5px;
    min-width: 40px;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #1c2432;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4f8cff;
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::sub-page:horizontal {
    background: #4f8cff;
    border-radius: 3px;
}
/* App shell containers (main_window objectNames) */
QMainWindow#appWindow, QWidget#appCentral, QWidget#appSide {
    background-color: #0a0e14;
    color: #f0f4f8;
}
QFrame#statusFrame {
    background: #141922;
    border-top: 1px solid #2d3748;
    border-radius: 0px;
}
/* Preview search input (Qt QLineEdit subclass instance) */
QLineEdit#previewSearchEdit {
    background-color: #0f1318;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 10px;
    color: #f0f4f8;
    selection-background-color: #4f8cff;
}
QLineEdit#previewSearchEdit:focus {
    border: 1px solid #4f8cff;
}
/* Role buttons that remain Qt (Destructive + toolbars) */
QPushButton#dangerBtn {
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#dangerBtn:hover {
    background: #ef4444;
}
QPushButton#warningBtn {
    background: #d97706;
    color: #1a1a2e;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#warningBtn:hover {
    background: #f59e0b;
}
QPushButton#toolbarBtn {
    padding: 4px 10px;
    min-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#toolbarIconBtn {
    padding: 0px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#toolbarSecondaryBtn {
    background: transparent;
    border: 1px solid #4f8cff;
    color: #4f8cff;
    padding: 4px 10px;
    min-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#toolbarSecondaryBtn:hover {
    background: rgba(79, 140, 255, 0.15);
    border-color: #7fb3ff;
    color: #7fb3ff;
}
QPushButton#toolbarSecondaryBtn:disabled {
    border-color: #4a5568;
    color: #4a5568;
    background: transparent;
}
QPushButton#accentBtn {
    background: #4f8cff;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 10px 18px;
}
QPushButton#accentBtn:hover {
    background: #7fb3ff;
}
QPushButton#secondaryBtn {
    background: transparent;
    border: 1px solid #4f8cff;
    color: #4f8cff;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#secondaryBtn:hover {
    background: rgba(79, 140, 255, 0.15);
}
QLabel#header {
    font-size: 28px;
    font-weight: 800;
    color: #4f8cff;
}
QLabel#desc {
    color: #94a3b8;
    font-size: 13px;
}
QLabel#stepLabel {
    color: #10b981;
    font-size: 14px;
    font-weight: 700;
}
"""

NATIVE_LIGHT_STYLESHEET = """
/* Scroll contents auto-fill from the OS palette unless explicitly scoped.
   Keep explicit light mode white even when Windows uses a dark palette. */
QWidget#advancedPage, QWidget#advancedContent {
    background-color: #ffffff;
    color: #1e293b;
}
QDialog {
    background-color: #ffffff;
    color: #1e293b;
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
}
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 16px;
    padding: 24px 16px 16px 16px;
    font-weight: 700;
    font-size: 13px;
    color: #3a7ae8;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 16px;
    left: 20px;
    background: #4f8cff;
    border-radius: 6px;
    color: white;
    font-size: 12px;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px;
    color: #1e293b;
    selection-background-color: #4f8cff;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px;
}
QListWidget::item:selected {
    background: #4f8cff;
    color: white;
}
QListWidget::item:hover:!selected {
    background: #f1f5f9;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 10px;
    color: #1e293b;
    selection-background-color: #4f8cff;
}
QComboBox:focus {
    border: 1px solid #4f8cff;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
    background: transparent;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    selection-background-color: #4f8cff;
    border-radius: 8px;
    padding: 4px;
}
QSplitter::handle {
    background: transparent;
    width: 6px;
}
QSplitter::handle:hover {
    background: #4f8cff;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background: #e2e8f0;
    color: #1e293b;
    font-weight: 700;
    height: 24px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: #4f8cff;
    border-radius: 8px;
}
QMenuBar {
    background: #ffffff;
    color: #1e293b;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
}
QMenuBar::item {
    padding: 10px 16px;
    background: transparent;
    color: #1e293b;
    border-radius: 6px;
    margin: 2px;
}
QMenuBar::item:selected {
    background: rgba(79, 140, 255, 0.15);
    color: #1e293b;
}
QMenu {
    background: #ffffff;
    color: #1e293b;
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
    background: #4f8cff;
    color: white;
}
QMenu::item:disabled {
    background: transparent;
    color: #64748b;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 8px 16px;
}
QToolTip {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #4f8cff;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #f1f5f9;
    width: 10px;
    border-radius: 5px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #94a3b8;
    border-radius: 5px;
    min-height: 40px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f1f5f9;
    height: 10px;
    border-radius: 5px;
    margin: 4px;
}
QScrollBar::handle:horizontal {
    background: #94a3b8;
    border-radius: 5px;
    min-width: 40px;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4f8cff;
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::sub-page:horizontal {
    background: #4f8cff;
    border-radius: 3px;
}
QMainWindow#appWindow, QWidget#appCentral, QWidget#appSide {
    background-color: #f8fafc;
    color: #1e293b;
}
QFrame#statusFrame {
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    border-radius: 0px;
}
QLineEdit#previewSearchEdit {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 10px;
    color: #1e293b;
    selection-background-color: #4f8cff;
}
QLineEdit#previewSearchEdit:focus {
    border: 1px solid #4f8cff;
}
QPushButton#dangerBtn {
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#dangerBtn:hover {
    background: #ef4444;
}
QPushButton#warningBtn {
    background: #d97706;
    color: #1a1a2e;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#warningBtn:hover {
    background: #f59e0b;
}
QPushButton#toolbarBtn {
    padding: 4px 10px;
    min-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#toolbarIconBtn {
    padding: 0px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#toolbarSecondaryBtn {
    background: transparent;
    border: 1px solid #4f8cff;
    color: #3a7ae8;
    padding: 4px 10px;
    min-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#toolbarSecondaryBtn:hover {
    background: rgba(79, 140, 255, 0.12);
}
QPushButton#toolbarSecondaryBtn:disabled {
    border-color: #cbd5e1;
    color: #94a3b8;
    background: transparent;
}
QPushButton#accentBtn {
    background: #4f8cff;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
    padding: 10px 18px;
}
QPushButton#accentBtn:hover {
    background: #3a7ae8;
}
QPushButton#secondaryBtn {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    color: #475569;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#secondaryBtn:hover {
    border-color: #4f8cff;
    color: #4f8cff;
}
QLabel#header {
    font-size: 28px;
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
"""

__all__ = ["NATIVE_DARK_STYLESHEET", "NATIVE_LIGHT_STYLESHEET"]
