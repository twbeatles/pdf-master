from pathlib import Path


def _line_count(path: str) -> int:
    return len(Path(path).read_text(encoding="utf-8").splitlines())


def test_legacy_shims_stay_thin_after_refactor():
    budgets = {
        "src/core/worker_ops/_pdf_impl.py": 80,
        "src/core/worker_ops/annotation_ops.py": 80,
        "src/core/worker_ops/extract_ops.py": 80,
        "src/core/worker_ops/cleanup_ops.py": 80,
        "src/core/worker_ops/page_ops.py": 80,
        "src/core/worker_ops/transform_ops.py": 80,
        "src/core/worker_ops/compare_ops.py": 80,
        "src/core/ai_service.py": 80,
        "src/core/settings.py": 80,
        "src/core/constants.py": 120,
        "src/core/undo_manager.py": 80,
        "src/ui/widgets.py": 80,
        "src/ui/tabs_advanced/builders.py": 80,
        "src/ui/thumbnail_grid.py": 80,
        "src/ui/zoomable_preview.py": 80,
        "src/ui/styles.py": 80,
        "src/ui/progress_overlay.py": 80,
        # main_window_worker keeps run_worker/on_success overrides for ToastWidget monkeypatch 계약
        "src/ui/main_window_worker.py": 450,
        "src/core/i18n_catalogs/shared.py": 80,
    }
    for path, max_lines in budgets.items():
        assert _line_count(path) <= max_lines, path


def test_legacy_public_import_paths_still_export_expected_symbols():
    from src.core.ai_service import AIService, GENAI_AVAILABLE, get_ai_service
    from src.core.constants import PAGE_SIZES, VERSION
    from src.core.settings import KEYRING_AVAILABLE, SETTINGS_FILE, load_settings
    from src.core.undo_manager import ActionRecord, UndoManager
    from src.core.worker_ops import WorkerPdfOpsMixin
    from src.core.worker_ops._pdf_impl import WorkerPdfOpsMixin as WorkerPdfOpsMixinFacade
    from src.core.worker_ops.annotation_ops import WorkerAnnotationOpsMixin
    from src.core.worker_ops.cleanup_ops import WorkerCleanupOpsMixin, _content_bbox
    from src.core.worker_ops.extract_ops import WorkerExtractOpsMixin
    from src.ui.progress_overlay import LoadingSpinner, ProgressOverlayWidget
    from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET, ThemeColors
    from src.ui.tabs_advanced.builders import setup_advanced_tab
    from src.ui.thumbnail_grid import ThumbnailGridWidget
    from src.ui.widgets import FileSelectorWidget, ToastWidget, is_valid_pdf
    from src.ui.zoomable_preview import ZoomablePreviewWidget

    assert isinstance(GENAI_AVAILABLE, bool)
    assert callable(get_ai_service)
    assert callable(AIService)
    assert callable(WorkerPdfOpsMixin)
    assert WorkerPdfOpsMixin is WorkerPdfOpsMixinFacade or callable(WorkerPdfOpsMixinFacade)
    assert callable(WorkerAnnotationOpsMixin)
    assert callable(WorkerExtractOpsMixin)
    assert callable(WorkerCleanupOpsMixin)
    assert callable(_content_bbox)
    assert callable(setup_advanced_tab)
    assert callable(FileSelectorWidget)
    assert callable(ToastWidget)
    assert callable(is_valid_pdf)
    assert callable(ThumbnailGridWidget)
    assert callable(ZoomablePreviewWidget)
    assert callable(ProgressOverlayWidget)
    assert callable(LoadingSpinner)
    assert callable(load_settings)
    assert callable(UndoManager)
    assert callable(ActionRecord)
    assert isinstance(KEYRING_AVAILABLE, bool)
    assert isinstance(SETTINGS_FILE, str)
    assert VERSION
    assert PAGE_SIZES["A4"]
    assert ThemeColors.PRIMARY == "#4f8cff"
    assert DARK_STYLESHEET and LIGHT_STYLESHEET


def test_split_domain_packages_export_composed_mixins():
    """분할된 도메인 패키지가 기존 메서드 surface를 보존하는지 확인."""
    from src.core.worker_ops.annotation_ops import WorkerAnnotationOpsMixin
    from src.core.worker_ops.compare_ops import WorkerCompareOpsMixin
    from src.core.worker_ops.extract_ops import WorkerExtractOpsMixin
    from src.core.worker_ops.page_ops import WorkerPageOpsMixin
    from src.core.worker_ops.transform_ops import WorkerTransformOpsMixin

    annotation_methods = {
        "watermark",
        "image_watermark",
        "add_background",
        "add_annotation",
        "remove_annotations",
        "highlight_text",
        "add_text_markup",
        "insert_textbox",
        "add_sticky_note",
        "draw_shapes",
        "add_link",
        "redact_text",
        "redact_area",
        "add_stamp",
        "insert_signature",
        "add_ink_annotation",
        "add_freehand_signature",
    }
    extract_methods = {
        "extract_text",
        "get_pdf_info",
        "get_bookmarks",
        "set_bookmarks",
        "search_text",
        "extract_tables",
        "list_annotations",
        "extract_links",
        "list_attachments",
        "add_attachment",
        "extract_attachments",
        "extract_images",
        "extract_markdown",
    }
    for name in annotation_methods:
        assert hasattr(WorkerAnnotationOpsMixin, name), name
    for name in extract_methods:
        assert hasattr(WorkerExtractOpsMixin, name), name
    for name in ("split", "delete_pages", "rotate", "reorder", "reverse_pages"):
        assert hasattr(WorkerPageOpsMixin, name), name
    for name in ("convert_to_img", "compress", "crop_pdf", "resize_pages", "convert_to_svg"):
        assert hasattr(WorkerTransformOpsMixin, name), name
    assert hasattr(WorkerCompareOpsMixin, "compare_pdfs")
    assert hasattr(WorkerCompareOpsMixin, "_legacy_compare_pdfs")


def test_worker_domain_modules_do_not_reintroduce_legacy_pdf_aliases():
    offenders = []
    for path in Path("src/core/worker_ops").glob("*.py"):
        if path.name == "_pdf_impl.py":
            continue
        if "_LegacyWorkerPdfOpsMixin" in path.read_text(encoding="utf-8"):
            offenders.append(path.as_posix())
    assert offenders == []
