from pathlib import Path


def _line_count(path: str) -> int:
    return len(Path(path).read_text(encoding="utf-8").splitlines())


def test_legacy_shims_stay_thin_after_refactor():
    budgets = {
        "src/core/worker_ops/_pdf_impl.py": 80,
        "src/core/ai_service.py": 80,
        "src/ui/widgets.py": 80,
        "src/ui/tabs_advanced/builders.py": 80,
        "src/ui/thumbnail_grid.py": 80,
        "src/ui/zoomable_preview.py": 80,
        "src/ui/styles.py": 80,
        "src/core/i18n_catalogs/shared.py": 80,
    }
    for path, max_lines in budgets.items():
        assert _line_count(path) <= max_lines, path


def test_legacy_public_import_paths_still_export_expected_symbols():
    from src.core.ai_service import AIService, GENAI_AVAILABLE, get_ai_service
    from src.core.worker_ops._pdf_impl import WorkerPdfOpsMixin
    from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET, ThemeColors
    from src.ui.tabs_advanced.builders import setup_advanced_tab
    from src.ui.thumbnail_grid import ThumbnailGridWidget
    from src.ui.widgets import FileSelectorWidget, ToastWidget, is_valid_pdf
    from src.ui.zoomable_preview import ZoomablePreviewWidget

    assert isinstance(GENAI_AVAILABLE, bool)
    assert callable(get_ai_service)
    assert callable(AIService)
    assert callable(WorkerPdfOpsMixin)
    assert callable(setup_advanced_tab)
    assert callable(FileSelectorWidget)
    assert callable(ToastWidget)
    assert callable(is_valid_pdf)
    assert callable(ThumbnailGridWidget)
    assert callable(ZoomablePreviewWidget)
    assert ThemeColors.PRIMARY == "#4f8cff"
    assert DARK_STYLESHEET and LIGHT_STYLESHEET


def test_worker_domain_modules_do_not_reintroduce_legacy_pdf_aliases():
    offenders = []
    for path in Path("src/core/worker_ops").glob("*.py"):
        if path.name == "_pdf_impl.py":
            continue
        if "_LegacyWorkerPdfOpsMixin" in path.read_text(encoding="utf-8"):
            offenders.append(path.as_posix())
    assert offenders == []
