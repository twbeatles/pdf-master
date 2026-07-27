import re
from pathlib import Path


CURRENT_AUDIT_FILE = "PROJECT_AUDIT.md"
# 레거시 감사 파일명 — maintained docs에 남아 있으면 존재하는 파일만 허용
LEGACY_AUDIT_FILE_PATTERN = re.compile(r"FUNCTIONAL_IMPLEMENTATION_AUDIT_\d{4}-\d{2}-\d{2}\.md")


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
        assert "scripts/package_smoke.ps1" in text
        assert "main.py --smoke" in text
        assert "src/core/ai/" in text or "src.core.ai" in text
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
    # 현행 기능 감사 SSOT: PROJECT_AUDIT.md
    assert Path(CURRENT_AUDIT_FILE).is_file()
    assert CURRENT_AUDIT_FILE in readme
    assert CURRENT_AUDIT_FILE in readme_en
    assert CURRENT_AUDIT_FILE in claude
    assert CURRENT_AUDIT_FILE in gemini
    assert "python -m PyInstaller pdf_master.spec --clean" in spec_text
    assert ".pytest_tmp/" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "pip-wheel-metadata/" in gitignore
    assert "*.whl" in gitignore
    assert "*.tar.gz" in gitignore


def test_maintained_docs_do_not_reference_missing_functional_audits():
    """레거시 FUNCTIONAL audit 파일명을 가리키면, 해당 파일이 실제로 존재해야 한다."""
    existing = {path.name for path in Path(".").glob("FUNCTIONAL_IMPLEMENTATION_AUDIT_*.md")}
    maintained_docs = [
        Path("README.md"),
        Path("README_EN.md"),
        Path("CLAUDE.md"),
        Path("GEMINI.md"),
        Path("PROJECT_AUDIT.md"),
    ]

    missing = []
    for path in maintained_docs:
        if not path.is_file():
            missing.append(f"{path}: (file missing)")
            continue
        text = path.read_text(encoding="utf-8")
        for match in LEGACY_AUDIT_FILE_PATTERN.findall(text):
            if match not in existing:
                missing.append(f"{path}:{match}")

    assert not missing, "Missing audit files referenced by maintained docs:\n" + "\n".join(missing)


def test_project_audit_is_current_ssot():
    """PROJECT_AUDIT.md가 존재하고 감사 문서 구조를 갖춘다."""
    path = Path(CURRENT_AUDIT_FILE)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "# Project Audit" in text
    assert "## 1. Executive Summary" in text
    assert "## 3. High-Risk Issues" in text
