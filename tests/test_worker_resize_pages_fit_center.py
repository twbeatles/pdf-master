from _deps import require_pyqt6_and_pymupdf
from src.core.constants import PAGE_SIZES
from src.core.optional_deps import fitz


def _make_bordered_landscape_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=800, height=400)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(10, 10, 790, 390))
    shape.finish(color=(0, 0, 0), width=12)
    shape.commit()
    doc.save(str(path))
    doc.close()


def _count_dark_pixels_in_strip(pix, x_start, x_end):
    count = 0
    channels = pix.n
    samples = memoryview(pix.samples)
    for y in range(pix.height):
        row_offset = y * pix.stride
        for x in range(x_start, x_end):
            offset = row_offset + (x * channels)
            if samples[offset] < 80 and samples[offset + 1] < 80 and samples[offset + 2] < 80:
                count += 1
    return count


def test_resize_pages_fit_center_preserves_full_page_content(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "landscape.pdf"
    out = tmp_path / "resized.pdf"
    _make_bordered_landscape_pdf(src)

    worker = WorkerThread(
        "resize_pages",
        file_path=str(src),
        output_path=str(out),
        target_size="A4",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.resize_pages()

    assert not errors
    doc = fitz.open(str(out))
    page = doc[0]
    target_w, target_h = PAGE_SIZES["A4"]
    assert abs(page.rect.width - target_w) < 0.5
    assert abs(page.rect.height - target_h) < 0.5

    pix = page.get_pixmap(alpha=False)
    left_dark = _count_dark_pixels_in_strip(pix, 0, 40)
    right_dark = _count_dark_pixels_in_strip(pix, max(0, pix.width - 40), pix.width)
    doc.close()

    assert left_dark > 20
    assert right_dark > 20
