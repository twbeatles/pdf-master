"""PROJECT_AUDIT.md (2026-09-23) 제안 반영 회귀 테스트.

ISSUE-001 매니페스트 게시 재시도 / ISSUE-002 조용한 실패 표면화 /
ISSUE-003 다운로드 재시도 / ISSUE-004 비모달 대기열 + 만료 정책 표면화,
E2E 시뮬레이션, 문서 정합성을 검증한다.
"""
from __future__ import annotations

import base64
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _deps import require_pyqt6

from src.core.update_manifest import (
    NoUpdateAvailableError,
    ReleaseManifest,
    days_until_expiry,
    manifest_expiry_status,
    verify_release_manifest,
)


def _signed_document(payload: dict) -> tuple[dict, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    from src.core.update_manifest import canonical_manifest_payload

    document = {
        "payload": payload,
        "signature": base64.b64encode(private.sign(canonical_manifest_payload(payload))).decode(),
    }
    public = base64.b64encode(
        private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    return document, public


def _payload(**overrides) -> dict:
    base = {
        "version": "9.0.0",
        "artifact_url": "https://github.com/twbeatles/pdf-master/releases/download/v9/PDF_Master_v9.exe",
        "sha256": "0" * 64,
        "size": 1,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=100)).isoformat(),
    }
    base.update(overrides)
    return base


def test_manifest_expiry_status_classification() -> None:
    now = datetime.now(timezone.utc)
    assert manifest_expiry_status(now - timedelta(days=1)) == "expired"
    assert manifest_expiry_status(now + timedelta(days=10)) == "expiring_soon"
    assert manifest_expiry_status(now + timedelta(days=400)) == "valid"
    # naive datetime도 UTC로 간주
    assert manifest_expiry_status(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)) == "expired"
    assert days_until_expiry(now + timedelta(days=10, hours=12)) == 10


def test_verify_expired_manifest_rejected() -> None:
    document, public = _signed_document(_payload(expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()))
    try:
        verify_release_manifest(document, public_key=public, current_version="1.0.0")
    except ValueError as exc:
        assert "expired" in str(exc).lower()
    else:
        raise AssertionError("expired manifest must be rejected")


def test_stage_update_retries_then_succeeds(monkeypatch, tmp_path) -> None:
    from src.core import update_installer as installer

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    data = b"x" * 4096
    manifest = ReleaseManifest(
        version="9.9.9",
        artifact_url="https://example.com/PDF_Master_v9.9.9.exe",
        artifact_sha256=hashlib.sha256(data).hexdigest(),
        artifact_size=len(data),
        expires_at=datetime.now(timezone.utc) + timedelta(days=100),
    )

    from urllib.error import URLError

    calls = {"count": 0}

    class _Response:
        def __init__(self, payload: bytes):
            self._payload = payload
            self._offset = 0

        def geturl(self):
            return "https://example.com/PDF_Master_v9.9.9.exe"

        def read(self, size: int = -1):
            if self._offset >= len(self._payload):
                return b""
            chunk = self._payload[self._offset : self._offset + 512]
            self._offset += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _flaky_urlopen(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise URLError("transient cut")
        return _Response(data)

    monkeypatch.setattr(installer, "urlopen", _flaky_urlopen)
    monkeypatch.setattr(installer.time, "sleep", lambda *_a, **_k: None)

    staged = installer.stage_update(manifest, max_retries=3, retry_backoff=0)
    assert staged.is_file()
    assert hashlib.sha256(staged.read_bytes()).hexdigest() == manifest.artifact_sha256
    assert calls["count"] == 3


def test_stage_update_failure_cleans_staging(monkeypatch, tmp_path) -> None:
    from src.core import update_installer as installer

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    manifest = ReleaseManifest(
        version="9.9.9",
        artifact_url="https://example.com/x.exe",
        artifact_sha256="0" * 64,
        artifact_size=8,
        expires_at=datetime.now(timezone.utc) + timedelta(days=100),
    )

    from urllib.error import URLError

    monkeypatch.setattr(installer, "urlopen", lambda *a, **k: (_ for _ in ()).throw(URLError("down")))
    monkeypatch.setattr(installer.time, "sleep", lambda *_a, **_k: None)
    try:
        installer.stage_update(manifest, max_retries=2, retry_backoff=0)
    except OSError:
        pass
    else:
        raise AssertionError("download failure must raise")
    assert list(installer.update_root().glob("PDF_Master_v*.exe")) == []


def test_stage_update_policy_error_does_not_retry(monkeypatch, tmp_path) -> None:
    from src.core import update_installer as installer

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    manifest = ReleaseManifest(
        version="9.9.9",
        artifact_url="https://example.com/x.exe",
        artifact_sha256="0" * 64,
        artifact_size=8,
        expires_at=datetime.now(timezone.utc) + timedelta(days=100),
    )
    calls = {"count": 0}

    class _RedirectResponse:
        def geturl(self):
            return "http://example.com/x.exe"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _redirect(*args, **kwargs):
        calls["count"] += 1
        return _RedirectResponse()

    monkeypatch.setattr(installer, "urlopen", _redirect)
    try:
        installer.stage_update(manifest, max_retries=3, retry_backoff=0)
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("policy error must raise")
    assert calls["count"] == 1


def test_update_service_delegates(monkeypatch) -> None:
    from src.core import update_service as service

    sentinel = ReleaseManifest("9.0.0", "https://example.com/x.exe", "0" * 64, 1,
                               datetime.now(timezone.utc) + timedelta(days=10))
    monkeypatch.setattr(service, "download_release_manifest", lambda url: b"doc")
    monkeypatch.setattr(service, "verify_release_manifest", lambda doc, **kw: sentinel)
    assert service.check_for_update(manifest_url="https://m", public_key="k", current_version="1") is sentinel

    staged = Path("/tmp/staged.exe")
    monkeypatch.setattr(service, "stage_update", lambda manifest, progress, max_retries=3: staged)
    assert service.download_update(sentinel) == staged


class _EmitStub:
    def __init__(self):
        self.values: list = []

    def emit(self, value=None):
        self.values.append(value)


class _UpdateSignalsStub:
    def __init__(self):
        self.ready = _EmitStub(); self.current = _EmitStub(); self.failed = _EmitStub()
        self.staged = _EmitStub(); self.progress = _EmitStub(); self.notice = _EmitStub()


def _update_dummy():
    require_pyqt6()
    import src.ui.update_mixin as mixin_module

    class Dummy(mixin_module.UpdateMixin):
        def __init__(self):
            self._update_state = "checking"
            self._last_update_check_error = None
            self._last_update_check_at = None
            self._update_auto_retry_scheduled = False
            self._update_signals = _UpdateSignalsStub()
            self.status_text = ""

    return mixin_module, Dummy()


def test_silent_check_failure_records_and_hints(monkeypatch) -> None:
    mixin_module, dummy = _update_dummy()
    monkeypatch.setattr(mixin_module.QTimer, "singleShot", lambda *_a, **_k: None)
    outcome = dummy._handle_check_failure(RuntimeError("dns down"), silent=True)
    assert outcome == "failed"
    assert dummy._update_state == "idle"
    assert dummy._last_update_check_error == "dns down"
    assert dummy._last_update_check_at is not None
    assert len(dummy._update_signals.notice.values) == 1
    assert dummy._update_signals.failed.values == []
    assert dummy._update_auto_retry_scheduled is True


def test_manual_check_failure_emits_failed(monkeypatch) -> None:
    mixin_module, dummy = _update_dummy()
    monkeypatch.setattr(mixin_module.QTimer, "singleShot", lambda *_a, **_k: None)
    outcome = dummy._handle_check_failure(RuntimeError("500"), silent=False)
    assert outcome == "failed"
    assert dummy._update_signals.failed.values == ["500"]
    assert dummy._update_signals.notice.values == []


def test_manual_current_includes_last_error(monkeypatch) -> None:
    mixin_module, dummy = _update_dummy()
    dummy._last_update_check_error = "dns down"
    shown = {}
    monkeypatch.setattr(mixin_module.QMessageBox, "information", lambda *a, **k: shown.setdefault("text", a[2]))
    dummy._show_update_current()
    assert "dns down" in shown["text"]


def test_offer_update_includes_expiry_warning(monkeypatch) -> None:
    mixin_module, dummy = _update_dummy()
    manifest = ReleaseManifest(
        version="9.1.0",
        artifact_url="https://example.com/x.exe",
        artifact_sha256="0" * 64,
        artifact_size=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=10, hours=1),
    )
    captured = {}

    def _fake_question(*args, **kwargs):
        captured["text"] = args[2]
        return mixin_module.QMessageBox.StandardButton.No

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(mixin_module.QMessageBox, "question", _fake_question)
    dummy._offer_update(manifest)
    assert dummy._update_state == "idle"
    assert dummy._last_update_check_error is None
    assert "10" in captured["text"]


def test_run_worker_queues_without_modal(monkeypatch) -> None:
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    class _SignalStub:
        def connect(self, *_a, **_k):
            return None

    class _RunningWorkerStub:
        def __init__(self, mode, **kwargs):
            self.mode = mode
            self.kwargs = kwargs
            self.progress_signal = _SignalStub(); self.finished_signal = _SignalStub()
            self.error_signal = _SignalStub(); self.cancelled_signal = _SignalStub()

        def start(self):
            return None

        def isRunning(self):
            return True

        def wait(self, _timeout):
            return False

    class _ToastStub:
        shown: list = []

        def __init__(self, *args, **kwargs):
            self.args = args

        def show_toast(self, *_a, **_k):
            _ToastStub.shown.append(self.args)

    class _LabelStub:
        def __init__(self):
            self.text = ""

        def setText(self, text):
            self.text = text

    class _ProgressBarStub:
        def setValue(self, _value):
            return None

    class _OverlayStub:
        def show_progress(self, *_a, **_k):
            return None

    class Dummy(worker_module.MainWindowWorkerMixin):
        def __init__(self):
            self.worker = _RunningWorkerStub("rotate", file_path="a.pdf", output_path="out.pdf")
            self._pending_workers = []
            self.status_label = _LabelStub()
            self.progress_bar = _ProgressBarStub()
            self.progress_overlay = _OverlayStub()

        def set_ui_busy(self, _busy):
            return None

        def _prepare_preview_for_same_path_output(self, *_a, **_k):
            return None

        def _augment_worker_passwords_from_preview(self, *_a, **_k):
            return None

        def _finalize_worker(self):
            return None

    def _forbidden_question(*_a, **_k):
        raise AssertionError("run_worker must not open a modal dialog")

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "question", _forbidden_question)
    _ToastStub.shown.clear()

    dummy = Dummy()
    dummy.run_worker("merge", file_paths=["a.pdf", "b.pdf"], output_path="merged.pdf")
    dummy.run_worker("compress", file_path="a.pdf", output_path="compressed.pdf")

    assert len(dummy._pending_workers) == 2
    assert len(_ToastStub.shown) == 2
    assert "2" in dummy.status_label.text


def test_pending_queue_cap_still_enforced(monkeypatch) -> None:
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    class _SignalStub:
        def connect(self, *_a, **_k):
            return None

    class _RunningWorkerStub:
        def __init__(self):
            self.progress_signal = _SignalStub(); self.finished_signal = _SignalStub()
            self.error_signal = _SignalStub(); self.cancelled_signal = _SignalStub()

        def isRunning(self):
            return True

    toasts: list = []

    class _ToastStub:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def show_toast(self, *_a, **_k):
            toasts.append((self.args, self.kwargs))

    class _LabelStub:
        def setText(self, _text):
            return None

    class Dummy(worker_module.MainWindowWorkerMixin):
        def __init__(self):
            self.worker = _RunningWorkerStub()
            self._pending_workers = [
                {"mode": f"m{i}", "output_path": None, "kwargs": {}} for i in range(8)
            ]
            self.status_label = _LabelStub()

    from src.ui.window_worker import lifecycle as lifecycle_module

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    # 큐 상한 토스트는 lifecycle 모듈의 ToastWidget을 직접 사용한다
    monkeypatch.setattr(lifecycle_module, "ToastWidget", _ToastStub)
    dummy = Dummy()
    dummy.run_worker("merge", output_path="merged.pdf")
    assert len(dummy._pending_workers) == 8
    assert toasts and toasts[-1][1].get("toast_type") == "warning"


def test_apply_update_e2e_success_and_rollback(monkeypatch, tmp_path) -> None:
    from src.core import update_installer as installer

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))

    pops: list = []

    class _Completed:
        def __init__(self, returncode: int):
            self.returncode = returncode

    # 성공 경로
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: _Completed(0))
    monkeypatch.setattr(installer.subprocess, "Popen", lambda *a, **k: pops.append(a) or None)
    assert installer.apply_update(str(target), str(staged), 123456) == 0
    assert target.read_bytes() == b"new-exe"
    _applied = installer.consume_update_result()
    assert _applied is not None and _applied["status"] == "applied"

    # 실패 경로: smoke 실패 → 롤백
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"bad-exe")
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: _Completed(1))
    assert installer.apply_update(str(target), str(staged), 123456) == 4
    assert target.read_bytes() == b"old-exe"
    result = installer.consume_update_result()
    assert result is not None and result["status"] == "rolled_back"


def test_release_workflow_has_publish_retry() -> None:
    text = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "for ($attempt = 1" in text
    assert "Start-Sleep" in text


def test_spec_comment_uses_version_source() -> None:
    import re

    text = Path("pdf_master.spec").read_text(encoding="utf-8")
    # 빌드 결과물 예시가 구버전에 고정되면 안 된다 (연혁 주석의 과거 버전 언급은 허용)
    assert not re.search(r"dist/PDF_Master_v\d", text)
    assert "APP_VERSION" in text


def test_guides_have_no_stale_spec_pointers() -> None:
    for name in ("CLAUDE.md", "GEMINI.md"):
        text = Path(name).read_text(encoding="utf-8")
        assert ".specify/ 있음" not in text
        assert "specs/001-pdf-master-release-ux" not in text or "미초기화" in text


def test_new_i18n_keys_present() -> None:
    from src.core.i18n_catalogs import TRANSLATIONS

    for key in (
        "update_check_failed_hint",
        "update_last_error",
        "update_expires_soon",
        "update_not_supported",
        "msg_worker_queued_auto",
    ):
        assert TRANSLATIONS["ko"].get(key), key
        assert TRANSLATIONS["en"].get(key), key


def test_release_checklist_documents_expiry() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")
    assert "365" in text
    assert "--expires-days" in text
    assert "E2E" in text
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "365" in readme
    assert "release-checklist" in readme


def test_manifest_expiry_watch_workflow_exists() -> None:
    text = Path(".github/workflows/update-manifest-expiry.yml").read_text(encoding="utf-8")
    assert "cron:" in text
    assert "check_update_manifest_expiry.py" in text


def _write_manifest_doc(path: Path, expires_at: str) -> None:
    import json

    path.write_text(
        json.dumps({"payload": {"version": "9.0.0", "expires_at": expires_at}, "signature": "x"}),
        encoding="utf-8",
    )


def test_check_manifest_expiry_states(tmp_path) -> None:
    import sys

    sys.path.insert(0, ".")
    from scripts.check_update_manifest_expiry import check_manifest

    manifest = tmp_path / "latest.json"
    _write_manifest_doc(manifest, (datetime.now(timezone.utc) + timedelta(days=100)).isoformat())
    assert check_manifest(manifest, 30)[0] == 0
    _write_manifest_doc(manifest, (datetime.now(timezone.utc) + timedelta(days=10)).isoformat())
    code, message = check_manifest(manifest, 30)
    assert code == 2
    assert "10" in message
    _write_manifest_doc(manifest, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert check_manifest(manifest, 30)[0] == 1
    assert check_manifest(tmp_path / "missing.json", 30)[0] == 1
