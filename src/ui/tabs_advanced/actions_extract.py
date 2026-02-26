from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import tm


def action_extract_links(self):
    """PDF 링크 추출"""
    path = self.sel_links.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "links.txt", "Text (*.txt)")
    if s:
        self.run_worker("extract_links", file_path=path, output_path=s)

def action_extract_images(self):
    """이미지 추출"""
    path = self.sel_extract.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    out_dir = QFileDialog.getExistingDirectory(self, tm.get("dlg_select_output_dir"))
    if out_dir:
        self.run_worker("extract_images", file_path=path, output_dir=out_dir)

def action_get_bookmarks(self):
    """북마크 추출"""
    path = self.sel_bm.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "bookmarks.txt", "Text (*.txt)")
    if s:
        self.run_worker("get_bookmarks", file_path=path, output_path=s)

def action_search_text(self):
    """텍스트 검색"""
    path = self.sel_search.get_path()
    term = self.inp_search.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_keyword"))

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "search_results.txt", "Text (*.txt)")
    if s:
        self.run_worker("search_text", file_path=path, output_path=s, search_term=term)

def action_extract_tables(self):
    """테이블 추출"""
    path = self.sel_table.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "tables.csv", "CSV (*.csv)")
    if s:
        self.run_worker("extract_tables", file_path=path, output_path=s)

def action_extract_markdown(self):
    """Markdown 추출"""
    path = self.sel_md.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "output.md", "Markdown (*.md)")
    if s:
        self.run_worker("extract_markdown", file_path=path, output_path=s)
