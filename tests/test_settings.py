import json
from pathlib import Path


def test_load_settings_defaults_not_shared(tmp_path, monkeypatch):
    from src.core import settings as st

    monkeypatch.setattr(st, "SETTINGS_FILE", str(tmp_path / "settings.json"))

    a = st.load_settings()
    a["recent_files"].append("x.pdf")
    a["chat_histories"]["x.pdf"] = [{"role": "user", "content": "hi"}]

    b = st.load_settings()
    assert b["recent_files"] == []
    assert b["chat_histories"] == {}


def test_load_settings_type_defense(tmp_path, monkeypatch):
    from src.core import settings as st

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(st, "SETTINGS_FILE", str(settings_file))

    settings_file.write_text(
        json.dumps(
            {
                "theme": "dark",
                "recent_files": "not-a-list",
                "chat_histories": ["not-a-dict"],
            }
        ),
        encoding="utf-8",
    )

    loaded = st.load_settings()
    assert isinstance(loaded["recent_files"], list)
    assert isinstance(loaded["chat_histories"], dict)


def test_load_settings_corrupt_file_creates_backup(tmp_path, monkeypatch):
    from src.core import settings as st

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(st, "SETTINGS_FILE", str(settings_file))

    settings_file.write_text("{ this is not json", encoding="utf-8")
    loaded = st.load_settings()

    assert isinstance(loaded, dict)
    backups = list(tmp_path.glob("settings.json.backup_*"))
    assert len(backups) == 1

