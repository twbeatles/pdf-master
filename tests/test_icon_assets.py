from pathlib import Path


def test_app_icon_assets_exist_and_are_compact():
    png = Path("assets/app_icon.png")
    ico = Path("assets/app_icon.ico")

    assert png.is_file(), "assets/app_icon.png is required for runtime and packaging"
    assert ico.is_file(), "assets/app_icon.ico is required for the Windows executable icon"

    assert png.stat().st_size < 512 * 1024, "PNG icon should stay compact for bundling"
    assert ico.stat().st_size < 512 * 1024, "ICO icon should stay compact for bundling"


def test_spec_references_app_icon_assets():
    spec_text = Path("pdf_master.spec").read_text(encoding="utf-8")

    assert 'assets", "app_icon.ico"' in spec_text
    assert 'assets", "app_icon.png"' in spec_text
    assert "icon=EXE_ICON" in spec_text