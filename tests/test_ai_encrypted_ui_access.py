"""AI 탭: 암호 PDF는 preview 인증 후 Worker로 진행한다."""

from __future__ import annotations

import os

from _deps import require_pyqt6


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


class _LineEditStub:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def strip(self):
        return self._text.strip()

    def clear(self):
        self._text = ""


class _ComboStub:
    def currentData(self):
        return "concise"


class _LangStub:
    def currentData(self):
        return "ko"


class _SpinStub:
    def value(self):
        return 0


class _TextEditStub:
    def __init__(self):
        self.value = ""
        self.placeholder = ""

    def clear(self):
        self.value = ""

    def setPlaceholderText(self, text):
        self.placeholder = text

    def setPlainText(self, text):
        self.value = text


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text

    def clear(self):
        self.text = ""

    def setVisible(self, _v):
        return None


def test_action_ai_summarize_encrypted_with_preview_access_runs_worker(monkeypatch, tmp_path):
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QWidget

    from src.ui import main_window_config
    from src.ui.tabs_ai import actions as ai_actions

    app = QApplication.instance() or QApplication([])
    _ = app

    pdf = tmp_path / "enc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%encrypted-stub\n")

    monkeypatch.setattr(main_window_config, "AI_AVAILABLE", True)
    monkeypatch.setattr(ai_actions, "AI_AVAILABLE", True)
    monkeypatch.setattr(ai_actions, "is_pdf_encrypted", lambda _p: True)

    calls = []

    class Dummy(QWidget):
        def __init__(self):
            super().__init__()
            self.sel_ai_pdf = _PathStub(str(pdf))
            self.txt_api_key = _LineEditStub("x" * 24)
            self.cmb_summary_style = _ComboStub()
            self.cmb_summary_lang = _LangStub()
            self.spn_max_pages = _SpinStub()
            self.txt_summary_result = _TextEditStub()
            self.lbl_summary_meta = _LabelStub()
            self._ai_worker_mode = False
            self.preview_calls = []

        def _ensure_preview_access(self, path):
            self.preview_calls.append(path)
            return True, "secret"

        def run_worker(self, mode, **kwargs):
            calls.append((mode, kwargs))

    dummy = Dummy()
    result = ai_actions.action_ai_summarize(dummy)

    assert result is None
    assert dummy.preview_calls
    assert calls
    assert calls[0][0] == "ai_summarize"
    assert calls[0][1]["file_path"] == str(pdf)
    assert dummy._ai_worker_mode is True


def test_action_ai_summarize_encrypted_without_preview_access_blocks(monkeypatch, tmp_path):
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox

    from src.ui import main_window_config
    from src.ui.tabs_ai import actions as ai_actions

    app = QApplication.instance() or QApplication([])
    _ = app

    pdf = tmp_path / "enc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    monkeypatch.setattr(main_window_config, "AI_AVAILABLE", True)
    monkeypatch.setattr(ai_actions, "AI_AVAILABLE", True)
    monkeypatch.setattr(ai_actions, "is_pdf_encrypted", lambda _p: True)

    warnings = []

    def fake_warning(*args, **kwargs):
        warnings.append(args)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(ai_actions.QMessageBox, "warning", fake_warning)

    calls = []

    class Dummy(QWidget):
        def __init__(self):
            super().__init__()
            self.sel_ai_pdf = _PathStub(str(pdf))
            self.txt_api_key = _LineEditStub("x" * 24)
            self.cmb_summary_style = _ComboStub()
            self.cmb_summary_lang = _LangStub()
            self.spn_max_pages = _SpinStub()
            self.txt_summary_result = _TextEditStub()
            self.lbl_summary_meta = _LabelStub()

        def _ensure_preview_access(self, path):
            return False, None

        def run_worker(self, mode, **kwargs):
            calls.append((mode, kwargs))

    dummy = Dummy()
    ai_actions.action_ai_summarize(dummy)

    assert warnings
    assert not calls
