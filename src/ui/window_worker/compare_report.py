"""PDF 비교 결과 스크롤 리포트 다이얼로그."""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...core.i18n import tm
from .results import _format_compare_summary

logger = logging.getLogger(__name__)


def show_compare_report_dialog(parent, payload: dict) -> None:
    """비교 payload를 스크롤 가능한 다이얼로그로 표시."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tm.get("compare_report_title"))
    dialog.setMinimumSize(520, 420)
    dialog.resize(640, 520)

    layout = QVBoxLayout(dialog)
    header = QLabel(tm.get("compare_summary_title"))
    header.setObjectName("stepLabel")
    layout.addWidget(header)

    body = QTextEdit()
    body.setReadOnly(True)
    body.setPlainText(_format_compare_summary(payload if isinstance(payload, dict) else {}))
    body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
    layout.addWidget(body, 1)

    btn_row = QHBoxLayout()
    visual_path = ""
    if isinstance(payload, dict):
        visual_path = str(payload.get("visual_diff_path", "") or "")
    if visual_path and os.path.isfile(visual_path):
        b_open = QPushButton(tm.get("compare_report_open_visual"))
        b_open.setObjectName("secondaryBtn")

        def _open_visual() -> None:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(visual_path))
            except Exception:
                logger.debug("Failed to open visual diff", exc_info=True)

        b_open.clicked.connect(_open_visual)
        btn_row.addWidget(b_open)
    btn_row.addStretch()
    layout.addLayout(btn_row)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.button(QDialogButtonBox.StandardButton.Close).setText(tm.get("compare_report_close"))
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
    if close_btn is not None:
        close_btn.clicked.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    dialog.exec()
