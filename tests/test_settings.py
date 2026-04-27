import json
from pathlib import Path


def test_load_settings_defaults_not_shared(tmp_path, monkeypatch):
    from src.core import settings as st

    monkeypatch.setattr(st, "SETTINGS_FILE", str(tmp_path / "settings.json"))

    a = st.load_settings()
    assert a["preview_search_expanded"] is True
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
                "theme": "invalid-theme",
                "recent_files": "not-a-list",
                "chat_histories": ["not-a-dict"],
                "splitter_sizes": ["bad", 10],
                "language": "jp",
                "window_geometry": 123,
                "last_output_dir": ["bad"],
                "preview_search_expanded": "false",
            }
        ),
        encoding="utf-8",
    )

    loaded = st.load_settings()
    assert isinstance(loaded["recent_files"], list)
    assert isinstance(loaded["chat_histories"], dict)
    assert loaded["splitter_sizes"] is None
    assert loaded["theme"] == "dark"
    assert loaded["language"] == "auto"
    assert loaded["window_geometry"] is None
    assert loaded["last_output_dir"] == ""
    assert loaded["preview_search_expanded"] is False


def test_load_settings_preserves_valid_normalized_values(tmp_path, monkeypatch):
    from src.core import settings as st
    from src.core.path_utils import make_chat_history_key, normalize_path_key

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(st, "SETTINGS_FILE", str(settings_file))
    existing_pdf = tmp_path / "a.pdf"
    existing_pdf.write_text("pdf", encoding="utf-8")
    normalized_path = normalize_path_key(str(existing_pdf))
    chat_key = make_chat_history_key(str(existing_pdf))

    settings_file.write_text(
        json.dumps(
            {
                "theme": "light",
                "recent_files": [str(existing_pdf), "", 3],
                "chat_histories": {str(existing_pdf): [{"role": "user", "content": "hi"}]},
                "splitter_sizes": [100, 200.8],
                "language": "en",
                "window_geometry": {"x": 10, "y": 20, "width": 100, "height": 200},
                "last_output_dir": str(tmp_path / "exports"),
                "preview_search_expanded": 0,
            }
        ),
        encoding="utf-8",
    )

    loaded = st.load_settings()
    assert loaded["theme"] == "light"
    assert loaded["recent_files"] == [normalized_path]
    assert loaded["chat_histories"] == {chat_key: [{"role": "user", "content": "hi"}]}
    assert loaded["splitter_sizes"] == [100, 200]
    assert loaded["language"] == "en"
    assert loaded["window_geometry"] == {"x": 10, "y": 20, "width": 100, "height": 200}
    assert loaded["last_output_dir"] == str(tmp_path / "exports")
    assert loaded["preview_search_expanded"] is False


def test_load_settings_merges_duplicate_normalized_chat_history_keys(tmp_path, monkeypatch):
    from src.core import settings as st
    from src.core.path_utils import make_chat_history_key, normalize_path_key

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(st, "SETTINGS_FILE", str(settings_file))

    existing_pdf = tmp_path / "chat.pdf"
    existing_pdf.write_text("pdf", encoding="utf-8")
    normalized_path = normalize_path_key(str(existing_pdf))
    chat_key = make_chat_history_key(str(existing_pdf))

    settings_file.write_text(
        json.dumps(
            {
                "chat_histories": {
                    str(existing_pdf): [{"role": "user", "content": "one"}],
                    normalized_path: [{"role": "assistant", "content": "two"}],
                },
                "recent_files": [str(existing_pdf), normalized_path, ""],
            }
        ),
        encoding="utf-8",
    )

    loaded = st.load_settings()

    assert loaded["recent_files"] == [normalized_path]
    assert loaded["chat_histories"] == {
        chat_key: [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
        ]
    }


def test_chat_history_key_changes_when_same_path_file_is_replaced(tmp_path):
    import os

    from src.core.path_utils import make_chat_history_key, parse_chat_history_key

    pdf_path = tmp_path / "same.pdf"
    pdf_path.write_text("old", encoding="utf-8")
    first_key = make_chat_history_key(str(pdf_path))

    first_mtime = parse_chat_history_key(first_key)[1]
    assert first_mtime is not None
    os.utime(pdf_path, ns=(first_mtime + 10_000_000, first_mtime + 10_000_000))
    second_key = make_chat_history_key(str(pdf_path))

    assert first_key != second_key


def test_load_settings_corrupt_file_creates_backup(tmp_path, monkeypatch):
    from src.core import settings as st

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(st, "SETTINGS_FILE", str(settings_file))

    settings_file.write_text("{ this is not json", encoding="utf-8")
    loaded = st.load_settings()

    assert isinstance(loaded, dict)
    backups = list(tmp_path.glob("settings.json.backup_*"))
    assert len(backups) == 1

