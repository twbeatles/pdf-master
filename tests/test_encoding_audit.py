from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".spec",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {
    ".editorconfig",
    ".gitignore",
}
REPLACEMENT_GUARD_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".py",
    ".spec",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
REPLACEMENT_GUARD_FILENAMES = {
    ".editorconfig",
    ".gitignore",
}


def _is_tracked_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_FILENAMES


def _should_forbid_replacement_chars(path: Path) -> bool:
    return path.suffix.lower() in REPLACEMENT_GUARD_SUFFIXES or path.name in REPLACEMENT_GUARD_FILENAMES


def _tracked_text_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        rel_paths = [Path(item) for item in proc.stdout.decode("utf-8").split("\0") if item]
    except Exception:
        rel_paths = [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()]

    return sorted(
        ROOT / rel_path
        for rel_path in rel_paths
        if (ROOT / rel_path).is_file() and _is_tracked_text_file(ROOT / rel_path)
    )


def test_tracked_text_files_use_utf8_without_bom_or_replacement_chars():
    violations: list[str] = []

    for path in _tracked_text_files():
        raw = path.read_bytes()
        rel = path.relative_to(ROOT).as_posix()

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            violations.append(f"{rel}: utf-8 decode failed ({exc})")
            continue

        if text.startswith("\ufeff"):
            violations.append(f"{rel}: contains UTF-8 BOM")

        if _should_forbid_replacement_chars(path) and "\ufffd" in text:
            violations.append(f"{rel}: contains U+FFFD replacement character")

    assert not violations, "Encoding audit failures:\n" + "\n".join(violations)
