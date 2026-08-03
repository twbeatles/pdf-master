"""마크업 액션 공용 의존성 — 테스트 monkeypatch 대상."""

from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ....core.i18n import tm
from ...widgets import ToastWidget

__all__ = ["QFileDialog", "QMessageBox", "ToastWidget", "tm"]
