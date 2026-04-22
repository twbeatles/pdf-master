from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import tm


def action_extract_links(self):
    """PDF 留곹겕 異붿텧"""
    path = self.sel_links.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "links.txt", "Text (*.txt)")
    if s:
        self.run_worker("extract_links", file_path=path, output_path=s)


def action_extract_images(self):
    """?대?吏 異붿텧"""
    path = self.sel_extract.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    out_dir = self._choose_output_directory(tm.get("dlg_select_output_dir"))
    if out_dir:
        self.run_worker("extract_images", file_path=path, output_dir=out_dir)


def action_get_bookmarks(self):
    """遺곷쭏??異붿텧"""
    path = self.sel_bm.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "bookmarks.txt", "Text (*.txt)")
    if s:
        self.run_worker("get_bookmarks", file_path=path, output_path=s)


def action_search_text(self):
    """?띿뒪??寃??"""
    path = self.sel_search.get_path()
    term = self.inp_search.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_keyword"))

    s, _ = self._choose_save_file(tm.get("save"), "search_results.txt", "Text (*.txt)")
    if s:
        self.run_worker("search_text", file_path=path, output_path=s, search_term=term)


def action_extract_tables(self):
    """?뚯씠釉?異붿텧"""
    path = self.sel_table.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "tables.csv", "CSV (*.csv)")
    if s:
        self.run_worker("extract_tables", file_path=path, output_path=s)


def action_extract_markdown(self):
    """Markdown 異붿텧"""
    path = self.sel_md.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "output.md", "Markdown (*.md)")
    if s:
        self.run_worker(
            "extract_markdown",
            file_path=path,
            output_path=s,
            markdown_mode=self.cmb_md_mode.currentData() or "auto",
            include_front_matter=self.chk_md_front_matter.isChecked(),
            include_page_markers=self.chk_md_page_markers.isChecked(),
            include_asset_placeholders=self.chk_md_asset_placeholders.isChecked(),
        )
