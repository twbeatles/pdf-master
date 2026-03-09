from .batch import (
    _batch_add_files,
    _batch_add_folder,
    action_batch,
    setup_batch_tab,
)
from .convert import (
    _add_images,
    _add_pdf_for_img,
    _add_pdf_for_txt,
    action_img,
    action_img_to_pdf,
    action_txt,
    setup_convert_tab,
)
from .merge import (
    _confirm_clear_merge,
    _merge_add_files,
    _update_merge_count,
    action_merge,
    setup_merge_tab,
)
from .page import (
    action_delete_pages,
    action_page_numbers,
    action_rotate,
    action_split,
    setup_page_tab,
)
from .reorder import (
    _load_pages_for_reorder,
    _reverse_pages,
    action_reorder,
    setup_reorder_tab,
)
from .security import (
    _load_metadata,
    action_compress,
    action_metadata,
    action_protect,
    action_unlock,
    action_watermark,
    setup_edit_sec_tab,
)
from .._typing import MainWindowHost


class MainWindowTabsBasicMixin(MainWindowHost):
    setup_merge_tab = setup_merge_tab
    _merge_add_files = _merge_add_files
    _update_merge_count = _update_merge_count
    _confirm_clear_merge = _confirm_clear_merge
    action_merge = action_merge

    setup_convert_tab = setup_convert_tab
    _add_images = _add_images
    _add_pdf_for_img = _add_pdf_for_img
    _add_pdf_for_txt = _add_pdf_for_txt
    action_img = action_img
    action_img_to_pdf = action_img_to_pdf
    action_txt = action_txt

    setup_page_tab = setup_page_tab
    action_split = action_split
    action_delete_pages = action_delete_pages
    action_rotate = action_rotate
    action_page_numbers = action_page_numbers

    setup_edit_sec_tab = setup_edit_sec_tab
    _load_metadata = _load_metadata
    action_metadata = action_metadata
    action_watermark = action_watermark
    action_protect = action_protect
    action_unlock = action_unlock
    action_compress = action_compress

    setup_reorder_tab = setup_reorder_tab
    _load_pages_for_reorder = _load_pages_for_reorder
    _reverse_pages = _reverse_pages
    action_reorder = action_reorder

    setup_batch_tab = setup_batch_tab
    _batch_add_files = _batch_add_files
    _batch_add_folder = _batch_add_folder
    action_batch = action_batch
