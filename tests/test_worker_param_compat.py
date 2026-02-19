import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def _make_pdf(path, texts):
    import fitz

    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def _make_png(path):
    import fitz

    doc = fitz.open()
    doc.new_page(width=40, height=20)
    pix = doc[0].get_pixmap()
    pix.save(str(path))
    doc.close()


def test_draw_shapes_accepts_ui_style_params(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src, ["base"])

    worker = WorkerThread(
        "draw_shapes",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        shape_type="rect",
        x=30,
        y=40,
        width=120,
        height=80,
        line_color=(1, 0, 0),
    )
    worker.draw_shapes()

    doc = fitz.open(str(out))
    drawings = doc[0].get_drawings()
    doc.close()
    assert drawings


def test_add_link_accepts_page_alias_and_zero_based_target(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src, ["p1", "p2"])

    worker = WorkerThread(
        "add_link",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        link_type="page",
        target=0,  # UI에서 전달 가능한 0-index 값
        rect=[50, 50, 150, 80],
    )
    worker.add_link()

    doc = fitz.open(str(out))
    links = doc[0].get_links()
    doc.close()

    assert links
    assert links[0]["kind"] == fitz.LINK_GOTO
    assert links[0]["page"] == 0


def test_insert_textbox_uses_xy_when_rect_missing(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src, ["base"])

    worker = WorkerThread(
        "insert_textbox",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        x=420,
        y=650,
        text="HELLO_BOX",
        fontsize=12,
        color=(0, 0, 0),
    )
    worker.insert_textbox()

    doc = fitz.open(str(out))
    words = doc[0].get_text("words")
    doc.close()
    hit = [w for w in words if "HELLO_BOX" in w[4]]
    assert hit
    # x/y 전달값이 반영되었는지 확인 (기본 rect(100,100,...)를 벗어나야 함)
    assert hit[0][0] >= 400
    assert hit[0][1] >= 620


def test_copy_page_between_docs_accepts_file_path_and_page_range(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    target = tmp_path / "target.pdf"
    source = tmp_path / "source.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(target, ["TARGET_1", "TARGET_2"])
    _make_pdf(source, ["SOURCE_1", "SOURCE_2"])

    worker = WorkerThread(
        "copy_page_between_docs",
        file_path=str(target),  # target_path alias
        source_path=str(source),
        page_range="2",  # source_pages alias
        insert_at=-1,
        output_path=str(out),
    )
    worker.copy_page_between_docs()

    doc = fitz.open(str(out))
    texts = [doc[i].get_text().strip() for i in range(len(doc))]
    doc.close()

    assert len(texts) == 3
    assert "TARGET_1" in texts[0]
    assert "TARGET_2" in texts[1]
    assert "SOURCE_2" in texts[2]


def test_image_watermark_accepts_scale_and_top_center_alias(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    img = tmp_path / "wm.png"
    out = tmp_path / "out.pdf"
    _make_pdf(src, ["base"])
    _make_png(img)

    worker = WorkerThread(
        "image_watermark",
        file_path=str(src),
        output_path=str(out),
        image_path=str(img),
        position="top-center",
        scale=0.5,
        opacity=0.5,
    )
    worker.image_watermark()

    doc = fitz.open(str(out))
    page = doc[0]
    image_list = page.get_images(full=True)
    assert image_list
    xref = image_list[0][0]
    rects = page.get_image_rects(xref)
    doc.close()

    assert rects
    rect = rects[0]
    center_x = (rect.x0 + rect.x1) / 2.0
    assert 280 <= center_x <= 320  # top-center 배치
    assert rect.y0 <= 30
