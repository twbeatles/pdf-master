from __future__ import annotations

from src.core import update_installer


def test_invalid_update_paths_write_a_consumable_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert update_installer.apply_update("missing.exe", "staged.exe", 0) == 2
    result = update_installer.consume_update_result()
    assert result is not None
    assert result["status"] == "failed"
    assert update_installer.consume_update_result() is None


def test_stage_root_is_scoped_to_local_app_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert update_installer.update_root() == tmp_path / "PDFMaster" / "updates"
