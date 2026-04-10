from _deps import require_pyqt6


class _DummyHost:
    def __init__(self, last_output_dir: str):
        self.settings = {"last_output_dir": last_output_dir}
        self.saved_delays = []

    def _schedule_settings_save(self, delay_ms: int = 400):
        self.saved_delays.append(delay_ms)

    def _get_output_dialog_dir(self):
        import src.ui.window_core.state as state

        return state._get_output_dialog_dir(self)

    def _remember_output_location(self, selected_path: str):
        import src.ui.window_core.state as state

        return state._remember_output_location(self, selected_path)


def test_choose_save_file_uses_last_output_dir_and_updates_setting(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.window_core.state as state

    start_dir = tmp_path / "exports"
    start_dir.mkdir()
    selected = start_dir / "merged.pdf"
    seen = {}

    def _fake_get_save_file_name(_parent, title, initial_path, file_filter):
        seen["title"] = title
        seen["initial_path"] = initial_path
        seen["file_filter"] = file_filter
        return str(selected), file_filter

    monkeypatch.setattr(state.QFileDialog, "getSaveFileName", _fake_get_save_file_name)

    dummy = _DummyHost(str(start_dir))
    path, selected_filter = state._choose_save_file(dummy, "Save PDF", "default.pdf", "PDF (*.pdf)")

    assert path == str(selected)
    assert selected_filter == "PDF (*.pdf)"
    assert seen["initial_path"] == str(start_dir / "default.pdf")
    assert dummy.settings["last_output_dir"] == str(start_dir)
    assert dummy.saved_delays == [400]


def test_choose_output_directory_uses_last_output_dir_and_updates_setting(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.window_core.state as state

    start_dir = tmp_path / "exports"
    chosen_dir = tmp_path / "other"
    start_dir.mkdir()
    chosen_dir.mkdir()
    seen = {}

    def _fake_get_existing_directory(_parent, title, initial_dir):
        seen["title"] = title
        seen["initial_dir"] = initial_dir
        return str(chosen_dir)

    monkeypatch.setattr(state.QFileDialog, "getExistingDirectory", _fake_get_existing_directory)

    dummy = _DummyHost(str(start_dir))
    selected = state._choose_output_directory(dummy, "Select output")

    assert selected == str(chosen_dir)
    assert seen["initial_dir"] == str(start_dir)
    assert dummy.settings["last_output_dir"] == str(chosen_dir)
    assert dummy.saved_delays == [400]
