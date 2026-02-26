from .actions_edit import (
    action_split_adv,
    action_stamp,
    action_crop,
    action_blank_page,
    action_pdf_info,
    action_duplicate_page,
    action_reverse_pages,
    action_resize_pages,
    action_insert_signature,
    action_add_freehand_signature,
)
from .actions_extract import (
    action_extract_links,
    action_extract_images,
    action_get_bookmarks,
    action_search_text,
    action_extract_tables,
    action_extract_markdown,
)
from .actions_markup import (
    action_highlight_text,
    action_list_annotations,
    action_remove_annotations,
    action_redact_text,
    action_add_text_markup,
    action_add_background,
    action_add_sticky_note,
    action_add_ink_annotation,
    action_draw_shape,
    action_add_hyperlink,
    action_insert_textbox,
    action_add_annotation_basic,
)
from .actions_misc import (
    action_detect_fields,
    _edit_form_field,
    action_fill_form,
    action_compare_pdfs,
    action_decrypt_pdf,
    action_list_attachments,
    action_add_attachment,
    action_extract_attachments,
    action_copy_pages,
    action_replace_page,
    action_set_bookmarks,
    action_image_watermark,
)
from .builders import (
    setup_advanced_tab,
    _create_edit_subtab,
    _create_extract_subtab,
    _create_markup_subtab,
    _create_misc_subtab,
)
from .helpers import (
    _normalize_page_input,
    _parse_freehand_strokes,
    _parse_bookmark_lines,
)


class MainWindowTabsAdvancedMixin:
    _normalize_page_input = _normalize_page_input
    _parse_freehand_strokes = _parse_freehand_strokes
    _parse_bookmark_lines = _parse_bookmark_lines
    setup_advanced_tab = setup_advanced_tab
    _create_edit_subtab = _create_edit_subtab
    _create_extract_subtab = _create_extract_subtab
    _create_markup_subtab = _create_markup_subtab
    _create_misc_subtab = _create_misc_subtab
    action_split_adv = action_split_adv
    action_stamp = action_stamp
    action_crop = action_crop
    action_blank_page = action_blank_page
    action_pdf_info = action_pdf_info
    action_duplicate_page = action_duplicate_page
    action_reverse_pages = action_reverse_pages
    action_resize_pages = action_resize_pages
    action_insert_signature = action_insert_signature
    action_add_freehand_signature = action_add_freehand_signature
    action_extract_links = action_extract_links
    action_extract_images = action_extract_images
    action_get_bookmarks = action_get_bookmarks
    action_search_text = action_search_text
    action_extract_tables = action_extract_tables
    action_extract_markdown = action_extract_markdown
    action_highlight_text = action_highlight_text
    action_list_annotations = action_list_annotations
    action_remove_annotations = action_remove_annotations
    action_redact_text = action_redact_text
    action_add_text_markup = action_add_text_markup
    action_add_background = action_add_background
    action_add_sticky_note = action_add_sticky_note
    action_add_ink_annotation = action_add_ink_annotation
    action_draw_shape = action_draw_shape
    action_add_hyperlink = action_add_hyperlink
    action_insert_textbox = action_insert_textbox
    action_add_annotation_basic = action_add_annotation_basic
    action_detect_fields = action_detect_fields
    _edit_form_field = _edit_form_field
    action_fill_form = action_fill_form
    action_compare_pdfs = action_compare_pdfs
    action_decrypt_pdf = action_decrypt_pdf
    action_list_attachments = action_list_attachments
    action_add_attachment = action_add_attachment
    action_extract_attachments = action_extract_attachments
    action_copy_pages = action_copy_pages
    action_replace_page = action_replace_page
    action_set_bookmarks = action_set_bookmarks
    action_image_watermark = action_image_watermark
