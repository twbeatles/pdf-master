from pathlib import Path


def test_pytest_config_uses_repo_local_basetemp():
    text = Path("pytest.ini").read_text(encoding="utf-8")
    assert "--basetemp=.pytest_tmp" in text


def test_requirements_dev_lists_core_validation_tools():
    text = Path("requirements-dev.txt").read_text(encoding="utf-8")
    for package_name in ("PyQt6", "PyMuPDF", "pytest", "pyright"):
        assert package_name in text


def test_docs_reference_validation_manifest_and_commands():
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_en = Path("README_EN.md").read_text(encoding="utf-8")
    claude = Path("CLAUDE.md").read_text(encoding="utf-8")
    gemini = Path("GEMINI.md").read_text(encoding="utf-8")
    spec_text = Path("pdf_master.spec").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "pip install -r requirements-dev.txt" in readme
    assert "python -m pyright" in readme
    assert "python -m pytest -q" in readme
    assert "python -m PyInstaller pdf_master.spec --clean" in readme
    assert "typings/" in readme
    assert "pip install -r requirements-dev.txt" in readme_en
    assert "python -m pyright" in readme_en
    assert "python -m pytest -q" in readme_en
    assert "python -m PyInstaller pdf_master.spec --clean" in readme_en
    assert "typings/" in readme_en
    assert "pip install -r requirements-dev.txt" in claude
    assert "python -m pyright" in claude
    assert "python -m pytest -q" in claude
    assert "python -m PyInstaller pdf_master.spec --clean" in claude
    assert "requirements-dev.txt" in claude
    assert "typings/" in claude
    assert "pip install -r requirements-dev.txt" in gemini
    assert "python -m pyright" in gemini
    assert "python -m pytest -q" in gemini
    assert "python -m PyInstaller pdf_master.spec --clean" in gemini
    assert "requirements-dev.txt" in gemini
    assert "typings/" in gemini
    assert "python -m PyInstaller pdf_master.spec --clean" in spec_text
    assert ".pytest_tmp/" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
