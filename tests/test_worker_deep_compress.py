"""Deep compress: image downsample + font subset regression tests."""

from pathlib import Path

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz
from src.core.worker_runtime.save_profiles import (
    resolve_image_optimize_options,
)


def _make_large_image_pdf(path: Path, width: int = 1200, height: int = 1600) -> None:
    """표시 크기 대비 고해상도 이미지를 넣어 재압축 효과를 유도한다."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 0)
    pix.clear_with(200)
    # 단순 단색보다 JPEG 재인코딩 이득이 나도록 패턴 삽입
    for y in range(0, height, 8):
        for x in range(0, width, 8):
            pix.set_pixel(x, y, (x % 255, y % 255, (x + y) % 255))
    page.insert_image(page.rect, pixmap=pix)
    page.insert_text((72, 72), "COMPRESS_TEST")
    doc.save(str(path), deflate=True)
    doc.close()


def test_resolve_image_optimize_options_profile_defaults():
    fast = resolve_image_optimize_options("fast")
    assert fast["optimize_images"] is False
    assert fast["subset_fonts"] is False

    compact = resolve_image_optimize_options("compact")
    assert compact["optimize_images"] is True
    assert compact["subset_fonts"] is True
    assert compact["max_dpi"] == 150.0
    assert compact["jpeg_quality"] == 75

    web = resolve_image_optimize_options("web")
    assert web["optimize_images"] is True
    assert web["max_dpi"] == 120.0
    assert web["jpeg_quality"] == 60


def test_resolve_image_optimize_options_kwargs_override():
    opts = resolve_image_optimize_options(
        "fast",
        optimize_images=True,
        max_image_dpi=96,
        jpeg_quality=40,
        grayscale_images=True,
        subset_fonts=True,
    )
    assert opts["optimize_images"] is True
    assert opts["subset_fonts"] is True
    assert opts["max_dpi"] == 96.0
    assert opts["jpeg_quality"] == 40
    assert opts["grayscale"] is True


def test_compress_fast_profile_skips_image_rewrite(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "fast.pdf"
    _make_large_image_pdf(src)

    worker = WorkerThread(
        "compress",
        file_path=str(src),
        output_path=str(out),
        save_profile="fast",
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.compress()

    assert not errors
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")
    assert worker.kwargs.get("compress_images_replaced") == 0


def test_compress_web_profile_rewrites_embedded_images(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "web.pdf"
    _make_large_image_pdf(src)
    original_size = src.stat().st_size

    worker = WorkerThread(
        "compress",
        file_path=str(src),
        output_path=str(out),
        save_profile="web",
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.compress()

    assert not errors
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")
    assert worker.kwargs.get("compress_images_replaced", 0) >= 1
    # 고해상도 임베디드 이미지는 웹 프로필에서 체감 있게 줄어들어야 한다
    assert out.stat().st_size < original_size * 0.85

    # 페이지 텍스트는 유지
    doc = fitz.open(str(out))
    try:
        assert "COMPRESS_TEST" in doc[0].get_text()
        images = doc[0].get_images()
        assert images
        # 다운샘플되어 원본 1200px보다 작아야 함
        xref = images[0][0]
        pix = fitz.Pixmap(doc, xref)
        assert pix.width < 1200 or pix.height < 1600
    finally:
        doc.close()


def test_compress_optimize_images_force_on_fast(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "forced.pdf"
    _make_large_image_pdf(src)

    worker = WorkerThread(
        "compress",
        file_path=str(src),
        output_path=str(out),
        save_profile="fast",
        optimize_images=True,
        max_image_dpi=96,
        jpeg_quality=50,
        subset_fonts=False,
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.compress()

    assert not errors
    assert worker.kwargs.get("compress_images_replaced", 0) >= 1


def test_batch_compress_applies_image_optimize(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _make_large_image_pdf(src)
    original_size = src.stat().st_size

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(out_dir),
        operation="compress",
        save_profile="web",
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.batch()

    assert not errors
    outputs = list(out_dir.glob("*.pdf"))
    assert len(outputs) == 1
    assert outputs[0].stat().st_size < original_size * 0.85
