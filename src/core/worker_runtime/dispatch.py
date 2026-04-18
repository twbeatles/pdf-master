from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperationSpec:
    mode: str
    handler: str
    undo_eligible: bool
    same_path_safe: bool
    output_kind: str
    result_kind: str
    title_key: str
    required_kwargs: tuple[str, ...]
    result_payload_keys: tuple[str, ...]
    refresh_preview: bool
    cancel_cleanup: str
    output_extensions: tuple[str, ...]


_DEFAULT_OUTPUT_EXTENSIONS = {
    "none": (),
    "memory": (),
    "pdf": (".pdf",),
    "text": (".txt",),
    "directory": (),
}


def _default_cancel_cleanup(output_kind: str, same_path_safe: bool) -> str:
    if output_kind in {"none", "memory"}:
        return "none"
    if same_path_safe and output_kind == "pdf":
        return "same_path_restore"
    return "created_outputs"


def _spec(
    mode: str,
    *,
    handler: str | None = None,
    undo_eligible: bool = False,
    same_path_safe: bool = False,
    output_kind: str = "none",
    result_kind: str = "message",
    title_key: str | None = None,
    required_kwargs: tuple[str, ...] = (),
    result_payload_keys: tuple[str, ...] = (),
    refresh_preview: bool | None = None,
    cancel_cleanup: str | None = None,
    output_extensions: tuple[str, ...] | None = None,
) -> OperationSpec:
    resolved_refresh_preview = output_kind == "pdf" if refresh_preview is None else refresh_preview
    resolved_cancel_cleanup = cancel_cleanup or _default_cancel_cleanup(output_kind, same_path_safe)
    if resolved_cancel_cleanup not in {"none", "created_outputs", "same_path_restore"}:
        raise ValueError(f"Invalid cancel_cleanup policy: {resolved_cancel_cleanup}")
    return OperationSpec(
        mode=mode,
        handler=handler or mode,
        undo_eligible=undo_eligible,
        same_path_safe=same_path_safe,
        output_kind=output_kind,
        result_kind=result_kind,
        title_key=title_key or mode,
        required_kwargs=required_kwargs,
        result_payload_keys=result_payload_keys,
        refresh_preview=resolved_refresh_preview,
        cancel_cleanup=resolved_cancel_cleanup,
        output_extensions=output_extensions if output_extensions is not None else _DEFAULT_OUTPUT_EXTENSIONS.get(output_kind, ()),
    )


OPERATION_SPECS: dict[str, OperationSpec] = {
    "add_annotation": _spec("add_annotation", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_annotation"),
    "add_attachment": _spec("add_attachment", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_attachment", required_kwargs=("attach_path",)),
    "add_background": _spec("add_background", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_background"),
    "add_freehand_signature": _spec("add_freehand_signature", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_freehand_signature"),
    "add_ink_annotation": _spec("add_ink_annotation", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_ink"),
    "add_link": _spec("add_link", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_link"),
    "add_page_numbers": _spec("add_page_numbers", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_add_page_numbers"),
    "add_stamp": _spec("add_stamp", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_stamp"),
    "add_sticky_note": _spec("add_sticky_note", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_sticky_note"),
    "add_text_markup": _spec("add_text_markup", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_add_text_markup", required_kwargs=("search_term",)),
    "ai_ask_question": _spec(
        "ai_ask_question",
        output_kind="memory",
        result_kind="answer",
        title_key="mode_ai_ask",
        required_kwargs=("api_key", "question"),
        result_payload_keys=("answer",),
        refresh_preview=False,
    ),
    "ai_extract_keywords": _spec(
        "ai_extract_keywords",
        output_kind="memory",
        result_kind="keywords",
        title_key="mode_ai_keywords",
        required_kwargs=("api_key",),
        result_payload_keys=("keywords",),
        refresh_preview=False,
    ),
    "ai_summarize": _spec(
        "ai_summarize",
        output_kind="text",
        result_kind="summary",
        title_key="mode_ai_summarize",
        required_kwargs=("api_key",),
        result_payload_keys=("title", "summary", "key_points"),
        refresh_preview=False,
    ),
    "batch": _spec("batch", output_kind="directory", title_key="mode_batch", required_kwargs=("output_dir", "operation")),
    "compare_pdfs": _spec("compare_pdfs", output_kind="text", result_kind="report", title_key="mode_compare_pdfs"),
    "compress": _spec("compress", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_compress"),
    "convert_to_img": _spec("convert_to_img", output_kind="directory", title_key="action_convert_to_img"),
    "copy_page_between_docs": _spec("copy_page_between_docs", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_copy_pages"),
    "crop_pdf": _spec("crop_pdf", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_crop_pdf"),
    "decrypt_pdf": _spec("decrypt_pdf", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_decrypt_pdf", required_kwargs=("password",)),
    "delete_pages": _spec("delete_pages", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_delete_pages", required_kwargs=("page_range",)),
    "draw_shapes": _spec("draw_shapes", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_draw_shapes"),
    "duplicate_page": _spec("duplicate_page", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="btn_duplicate"),
    "extract_attachments": _spec("extract_attachments", output_kind="directory", title_key="mode_extract_attachments"),
    "extract_images": _spec("extract_images", output_kind="directory", title_key="mode_extract_images"),
    "extract_links": _spec("extract_links", output_kind="text", title_key="mode_extract_links"),
    "extract_markdown": _spec("extract_markdown", output_kind="text", title_key="mode_extract_markdown", output_extensions=(".md",)),
    "extract_tables": _spec("extract_tables", output_kind="text", title_key="mode_extract_tables"),
    "extract_text": _spec("extract_text", output_kind="text", title_key="action_extract_text"),
    "fill_form": _spec("fill_form", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_fill_form"),
    "get_bookmarks": _spec("get_bookmarks", output_kind="text", title_key="mode_get_bookmarks"),
    "get_form_fields": _spec(
        "get_form_fields",
        output_kind="memory",
        result_kind="form_fields",
        title_key="mode_get_form_fields",
        result_payload_keys=("fields",),
        refresh_preview=False,
    ),
    "get_pdf_info": _spec("get_pdf_info", output_kind="text", title_key="mode_get_pdf_info"),
    "highlight_text": _spec("highlight_text", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_highlight_text", required_kwargs=("search_term",)),
    "image_watermark": _spec("image_watermark", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_image_watermark", required_kwargs=("image_path",)),
    "images_to_pdf": _spec("images_to_pdf", output_kind="pdf", title_key="action_images_to_pdf"),
    "insert_blank_page": _spec("insert_blank_page", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="btn_insert_blank"),
    "insert_signature": _spec("insert_signature", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_insert_signature", required_kwargs=("signature_path",)),
    "insert_textbox": _spec("insert_textbox", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_insert_textbox"),
    "list_annotations": _spec(
        "list_annotations",
        output_kind="memory",
        result_kind="annotations",
        title_key="mode_list_annotations",
        result_payload_keys=("annotations",),
        refresh_preview=False,
    ),
    "list_attachments": _spec(
        "list_attachments",
        output_kind="memory",
        result_kind="attachments",
        title_key="mode_list_attachments",
        result_payload_keys=("attachments",),
        refresh_preview=False,
    ),
    "merge": _spec("merge", output_kind="pdf", title_key="action_merge"),
    "metadata_update": _spec("metadata_update", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_metadata_update"),
    "protect": _spec("protect", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_encrypt", required_kwargs=("password",)),
    "redact_text": _spec("redact_text", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="btn_redact", required_kwargs=("search_term",)),
    "remove_annotations": _spec("remove_annotations", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_remove_annotations"),
    "reorder": _spec("reorder", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_reorder"),
    "replace_page": _spec("replace_page", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_replace_page"),
    "resize_pages": _spec("resize_pages", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_resize_pages"),
    "reverse_pages": _spec("reverse_pages", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="btn_reverse_page"),
    "rotate": _spec("rotate", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_rotate"),
    "search_text": _spec("search_text", output_kind="text", title_key="mode_search_text"),
    "set_bookmarks": _spec("set_bookmarks", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="mode_set_bookmarks"),
    "split": _spec("split", output_kind="directory", title_key="action_split", required_kwargs=("output_dir", "page_range")),
    "split_by_pages": _spec("split_by_pages", output_kind="directory", title_key="mode_split_by_pages", required_kwargs=("output_dir", "pages_per_file")),
    "watermark": _spec("watermark", undo_eligible=True, same_path_safe=True, output_kind="pdf", title_key="action_watermark", required_kwargs=("text",)),
}

MODE_TO_HANDLER = {mode: spec.handler for mode, spec in OPERATION_SPECS.items()}


def get_operation_spec(mode: str) -> OperationSpec | None:
    return OPERATION_SPECS.get(mode)


def get_handler_method_name(mode: str) -> str | None:
    spec = get_operation_spec(mode)
    return spec.handler if spec is not None else None
