"""의존성 없는 PyMuPDF 확장 기능 회귀 테스트."""

from pathlib import Path

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz
from src.core.worker_runtime.dispatch import get_operation_spec


def _text_pdf(path: Path, pages: list[str], *, title_sizes: list[float] | None = None) -> None:
    doc = fitz.open()
    for i, text in enumerate(pages):
        page = doc.new_page(width=300, height=400)
        size = 11.0
        if title_sizes and i < len(title_sizes):
            size = title_sizes[i]
        page.insert_text((40, 60), text, fontsize=size)
    doc.save(str(path))
    doc.close()


def _blank_and_content_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 40), "KEEP")
    doc.new_page(width=200, height=200)
    doc.save(str(path))
    doc.close()


def test_new_operation_specs_registered():
    for mode in (
        "split_by_bookmarks",
        "remove_blank_pages",
        "dedupe_pages",
        "auto_bookmarks",
        "sanitize_pdf",
        "impose_nup",
        "convert_to_svg",
        "flatten_form",
        "redact_area",
    ):
        spec = get_operation_spec(mode)
        assert spec is not None, mode
        assert spec.handler == mode


def test_remove_blank_pages(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _blank_and_content_pdf(src)

    worker = WorkerThread("remove_blank_pages", file_path=str(src), output_path=str(out))
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.remove_blank_pages()

    assert not errors
    doc = fitz.open(str(out))
    try:
        assert len(doc) == 1
        assert "KEEP" in doc[0].get_text()
    finally:
        doc.close()


def test_dedupe_pages(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _text_pdf(src, ["A", "A", "B"])

    worker = WorkerThread("dedupe_pages", file_path=str(src), output_path=str(out))
    worker.dedupe_pages()

    doc = fitz.open(str(out))
    try:
        texts = [doc[i].get_text().strip() for i in range(len(doc))]
        assert texts == ["A", "B"] or (len(texts) == 2 and "A" in texts[0] and "B" in texts[1])
    finally:
        doc.close()


def test_split_by_bookmarks(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "parts"
    out_dir.mkdir()
    doc = fitz.open()
    for text in ["Ch1", "more1", "Ch2", "more2"]:
        page = doc.new_page(width=300, height=400)
        page.insert_text((40, 60), text)
    doc.set_toc([[1, "Chapter 1", 1], [1, "Chapter 2", 3]])
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "split_by_bookmarks",
        file_path=str(src),
        output_dir=str(out_dir),
        max_level=1,
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.split_by_bookmarks()

    assert not errors
    parts = list(out_dir.glob("*.pdf"))
    assert len(parts) == 2


def test_auto_bookmarks(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    for title, body in (("Title One", "body text here"), ("Title Two", "more body")):
        page = doc.new_page(width=400, height=500)
        page.insert_text((40, 50), title, fontsize=18)
        page.insert_text((40, 90), body, fontsize=11)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread("auto_bookmarks", file_path=str(src), output_path=str(out))
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.auto_bookmarks()

    assert not errors, errors
    doc = fitz.open(str(out))
    try:
        toc = doc.get_toc()
        assert len(toc) >= 1
    finally:
        doc.close()


def test_sanitize_clears_metadata(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), "hello")
    doc.set_metadata({"title": "Secret", "author": "Someone"})
    doc.save(str(src))
    doc.close()

    worker = WorkerThread("sanitize_pdf", file_path=str(src), output_path=str(out))
    worker.sanitize_pdf()

    doc = fitz.open(str(out))
    try:
        meta = doc.metadata or {}
        assert not (meta.get("title") or "").strip()
        assert not (meta.get("author") or "").strip()
    finally:
        doc.close()


def test_impose_nup_2(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _text_pdf(src, ["P1", "P2", "P3"])

    worker = WorkerThread("impose_nup", file_path=str(src), output_path=str(out), nup=2)
    worker.impose_nup()

    doc = fitz.open(str(out))
    try:
        assert len(doc) == 2  # 3 pages -> 2 sheets of 2-up
    finally:
        doc.close()


def test_crop_content_mode(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    page = doc.new_page(width=500, height=700)
    page.insert_text((100, 120), "CONTENT", fontsize=20)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "crop_pdf",
        file_path=str(src),
        output_path=str(out),
        crop_mode="content",
        content_pad=2,
    )
    worker.crop_pdf()

    doc = fitz.open(str(out))
    try:
        crop = doc[0].cropbox
        assert crop.width < 500
        assert crop.height < 700
    finally:
        doc.close()


def test_redact_area(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _text_pdf(src, ["SECRET DATA"])

    worker = WorkerThread(
        "redact_area",
        file_path=str(src),
        output_path=str(out),
        rects=[{"page": 1, "rect": [30, 40, 200, 80]}],
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.redact_area()
    assert not errors
    assert out.exists()


def test_protect_permissions_kwargs(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _text_pdf(src, ["x"])

    worker = WorkerThread(
        "protect",
        file_path=str(src),
        output_path=str(out),
        password="secret",
        permissions=["print", "accessibility"],
    )
    worker.protect()
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")


def test_flatten_form(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    widget = fitz.Widget()
    widget.field_name = "name"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(50, 50, 200, 80)
    widget.field_value = "Alice"
    page.add_widget(widget)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread("flatten_form", file_path=str(src), output_path=str(out))
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.flatten_form()
    assert not errors, errors

    doc = fitz.open(str(out))
    try:
        widgets = list(doc[0].widgets() or [])
        assert widgets == []
    finally:
        doc.close()


def test_convert_to_svg(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "svg"
    out_dir.mkdir()
    _text_pdf(src, ["SVG"])

    worker = WorkerThread("convert_to_svg", file_path=str(src), output_dir=str(out_dir))
    worker.convert_to_svg()
    svgs = list(out_dir.glob("*.svg"))
    assert len(svgs) == 1
    assert "<svg" in svgs[0].read_text(encoding="utf-8", errors="ignore").lower()


def test_visual_compare_detects_image_only_diff(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    left = tmp_path / "left.pdf"
    right = tmp_path / "right.pdf"
    report = tmp_path / "cmp.txt"

    def make(path: Path, color: int):
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 40), 0)
        pix.clear_with(color)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(str(path))
        doc.close()

    make(left, 40)
    make(right, 220)

    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(left),
        file_path2=str(right),
        output_path=str(report),
        compare_mode="visual",
        generate_visual_diff=False,
        visual_threshold=0.01,
    )
    worker.compare_pdfs()
    assert worker.result_payload.get("diff_count", 0) >= 1
