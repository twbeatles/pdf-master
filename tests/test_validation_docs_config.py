from pathlib import Path


def test_pytest_config_uses_repo_local_basetemp():
    text = Path("pytest.ini").read_text(encoding="utf-8")
    assert "--basetemp=.pytest_tmp" in text


def test_pyproject_manifest_exists():
    assert Path("pyproject.toml").exists()


def test_requirements_dev_is_dev_extra_shim():
    text = Path("requirements-dev.txt").read_text(encoding="utf-8").strip()
    assert "-e .[dev]" in text


def test_docs_reference_validation_manifest_and_commands():
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_en = Path("README_EN.md").read_text(encoding="utf-8")
    claude = Path("CLAUDE.md").read_text(encoding="utf-8")
    gemini = Path("GEMINI.md").read_text(encoding="utf-8")
    spec_text = Path("pdf_master.spec").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    for text in (readme, readme_en, claude, gemini):
        assert "pyproject.toml" in text
        assert "pip install -e .[dev]" in text
        assert "python -m pyright" in text
        assert "python -m pytest -q" in text
        assert "python -m build" in text
        assert "python -m PyInstaller pdf_master.spec --clean" in text
        assert "google-genai" in text
        assert "google-generativeai" not in text
        assert "auto/native/text" in text
        assert "fast" in text and "compact" in text and "web" in text

    assert "requirements-dev.txt" in readme
    assert "requirements-dev.txt" in readme_en
    assert "requirements-dev.txt" in claude
    assert "requirements-dev.txt" in gemini
    assert "현재 선택한 PDF" in readme
    assert "currently selected PDF" in readme_en
    assert "currently selected PDF" in claude
    assert "currently selected PDF" in gemini
    assert "QFileSystemWatcher" in readme
    assert "auto-reload" in readme_en
    assert "auto-reload" in claude
    assert "auto-reload" in gemini
    assert "typings/" in readme
    assert "typings/" in readme_en
    assert "typings/" in claude
    assert "typings/" in gemini
    assert "python -m PyInstaller pdf_master.spec --clean" in spec_text
    assert ".pytest_tmp/" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "pip-wheel-metadata/" in gitignore
    assert "*.whl" in gitignore
    assert "*.tar.gz" in gitignore
