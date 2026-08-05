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
        "src/core/worker_ops/ai_ops.py": 80,
        "src/core/worker_ops/batch_ops.py": 80,
        "src/core/worker_ops/compose_ops.py": 80,
        "src/core/worker_ops/form_ops.py": 80,
        "src/core/worker_ops/security_ops.py": 80,
        "src/core/worker_ops/_pdf_helpers.py": 80,
        "src/core/ai_service.py": 80,
        "src/core/settings.py": 80,
        "src/core/constants.py": 120,
        "src/core/undo_manager.py": 80,
        "src/ui/widgets.py": 80,
        "src/ui/tabs_advanced/builders.py": 80,
        "src/ui/tabs_advanced/actions_markup.py": 160,  # facade re-export
        "src/ui/tabs_advanced/markup_actions/textbox.py": 120,  # textbox_impl re-export facade
        "src/ui/tabs_advanced/tab_builders/edit.py": 80,
        "src/ui/tabs_advanced/tab_builders/markup.py": 80,
        "src/core/worker_ops/annotation/markup.py": 40,  # composed highlight+textbox facade
        "src/ui/thumbnail_grid.py": 80,
        "src/ui/thumbnail/grid.py": 160,  # shell + mixins
        "src/ui/zoomable_preview.py": 80,
        "src/ui/styles.py": 80,
        "src/ui/progress_overlay.py": 80,
        # main_window_worker keeps run_worker/on_success overrides for ToastWidget monkeypatch 계약
        "src/ui/main_window_worker.py": 320,
        "src/ui/preview_widget/interaction_overlays.py": 40,
        "src/ui/common_widgets/file_selection.py": 40,
        # AI actions keep monkeypatch/__module__ contract (AI_AVAILABLE, QDialog, atomic_text_write source)
        "src/ui/tabs_ai/actions.py": 320,
        "src/ui/tabs_basic/security.py": 80,
        "src/ui/tabs_advanced/tab_builders/misc.py": 80,
        "src/core/i18n_catalogs/shared.py": 80,
        # Track B: 본체 모듈 재비대화 가드 (엄격 facade 보다 여유)
        "src/core/worker_ops/ai/ops.py": 40,  # thin facade after prepare/handlers split
        "src/core/worker_ops/ai/handlers.py": 280,
        "src/core/worker_ops/ai/prepare.py": 160,
        "src/core/worker_ops/ai/temp_acl.py": 80,
        "src/core/worker_ops/annotation/textbox.py": 450,
        "src/core/worker_ops/compare/ops.py": 420,
        "src/core/worker_ops/compare/helpers.py": 120,
        "src/ui/preview_widget/text_placement.py": 500,
        "src/ui/window_worker/lifecycle.py": 280,
        "src/ui/window_worker/helpers.py": 120,
        "src/ui/thumbnail/pixmap_lru.py": 60,
        "src/ui/contracts/monkeypatch_surfaces.py": 80,
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
        "insert_textboxes",
        "replace_text_in_rect",
        "extract_text_in_rect",
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
    # textbox 패키지 분리 surface
    from src.core.worker_ops.annotation.textbox import WorkerAnnotationTextboxMixin
    from src.core.worker_ops.annotation.highlight_markup import WorkerAnnotationHighlightMixin

    assert hasattr(WorkerAnnotationTextboxMixin, "insert_textbox")
    assert hasattr(WorkerAnnotationTextboxMixin, "extract_text_in_rect")
    assert hasattr(WorkerAnnotationHighlightMixin, "highlight_text")
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

    from src.core.worker_ops.ai_ops import WorkerAiOpsMixin
    from src.core.worker_ops.batch_ops import WorkerBatchOpsMixin
    from src.core.worker_ops.compose_ops import WorkerComposeOpsMixin
    from src.core.worker_ops.form_ops import WorkerFormOpsMixin
    from src.core.worker_ops.security_ops import WorkerSecurityOpsMixin, _resolve_permissions
    from src.core.worker_ops._pdf_helpers import text_needs_cjk
    from src.core.worker_ops.annotation.textbox_helpers import (
        ensure_textbox_rect,
        resolve_textbox_fontname,
        write_textbox_content,
    )
    from src.core.worker_ops.compare.helpers import collect_text_blocks, diff_blocks
    from src.ui.tabs_advanced.markup_actions.textbox import (
        action_insert_textbox,
        action_textbox_queue_add,
    )
    from src.ui.preview_widget.text_placement import TextPlacementOverlay, hit_test_handle
    from src.ui.preview_widget.text_placement_geometry import apply_resize
    from src.ui.thumbnail.grid import ThumbnailGridWidget
    from src.ui.thumbnail.grid_loading import ThumbnailGridLoadingMixin
    from src.ui.tabs_advanced.tab_builders.edit import _create_edit_subtab
    from src.ui.tabs_advanced.tab_builders.markup import _create_markup_subtab

    for name in ("ai_summarize", "ai_ask_question", "ai_extract_keywords"):
        assert hasattr(WorkerAiOpsMixin, name), name
    assert hasattr(WorkerBatchOpsMixin, "batch")
    for name in ("merge", "images_to_pdf", "copy_page_between_docs"):
        assert hasattr(WorkerComposeOpsMixin, name), name
    for name in ("get_form_fields", "fill_form", "flatten_form"):
        assert hasattr(WorkerFormOpsMixin, name), name
    for name in ("protect", "decrypt_pdf"):
        assert hasattr(WorkerSecurityOpsMixin, name), name
    assert callable(_resolve_permissions)
    assert callable(text_needs_cjk)
    assert callable(ensure_textbox_rect)
    assert callable(write_textbox_content)
    assert callable(resolve_textbox_fontname)
    assert callable(collect_text_blocks)
    assert callable(diff_blocks)
    assert callable(action_insert_textbox)
    assert callable(action_textbox_queue_add)
    assert callable(TextPlacementOverlay)
    assert callable(hit_test_handle)
    assert callable(apply_resize)
    assert hasattr(ThumbnailGridWidget, "load_pdf")
    assert hasattr(ThumbnailGridLoadingMixin, "load_pdf")
    assert callable(_create_edit_subtab)
    assert callable(_create_markup_subtab)

    from src.ui.preview_widget.interaction_overlays import PreviewInteractionMixin
    from src.ui.preview_widget.interaction_region import PreviewRegionInteractionMixin
    from src.ui.common_widgets.file_selection import DropZoneWidget, FileSelectorWidget
    from src.ui.tabs_ai.actions import action_ai_summarize, _extract_keywords, AI_AVAILABLE
    from src.ui.tabs_basic.security import setup_edit_sec_tab, action_protect
    from src.ui.tabs_advanced.tab_builders.misc import _create_misc_subtab
    from src.ui.main_window_worker import MainWindowWorkerMixin, ToastWidget, WorkerThread
    from src.ui._typing import PreviewWidgetHost, ThumbnailGridHost

    assert hasattr(PreviewInteractionMixin, "set_region_select_mode")
    assert hasattr(PreviewRegionInteractionMixin, "set_region_select_mode")
    assert callable(DropZoneWidget)
    assert callable(FileSelectorWidget)
    assert callable(action_ai_summarize)
    assert callable(_extract_keywords)
    assert isinstance(AI_AVAILABLE, bool)
    assert callable(setup_edit_sec_tab)
    assert callable(action_protect)
    assert callable(_create_misc_subtab)
    assert callable(MainWindowWorkerMixin)
    assert callable(ToastWidget)
    assert callable(WorkerThread)
    assert PreviewWidgetHost is not None
    assert ThumbnailGridHost is not None


def test_worker_domain_modules_do_not_reintroduce_legacy_pdf_aliases():
    offenders = []
    for path in Path("src/core/worker_ops").glob("*.py"):
        if path.name == "_pdf_impl.py":
            continue
        if "_LegacyWorkerPdfOpsMixin" in path.read_text(encoding="utf-8"):
            offenders.append(path.as_posix())
    assert offenders == []
