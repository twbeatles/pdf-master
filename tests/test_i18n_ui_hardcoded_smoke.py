import re
import ast
from pathlib import Path


EXCLUDED_UI_FILES = {
    "src/ui/progress_overlay.py",
    "src/ui/styles.py",
    "src/ui/widgets.py",
}


def test_no_hardcoded_korean_string_literals_in_runtime_ui_files():
    pattern = re.compile(r"[가-힣]")
    violations = []

    for path in Path("src/ui").rglob("*.py"):
        rel = path.as_posix()
        if rel in EXCLUDED_UI_FILES:
            continue
        path = Path(rel)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)

        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if not pattern.search(node.value):
                continue

            p = parent.get(node)

            # 모듈/클래스/함수 docstring 무시
            if isinstance(p, ast.Expr):
                gp = parent.get(p)
                if isinstance(gp, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue

            # i18n key/format은 허용 (tm.get("..."))
            if isinstance(p, ast.Call):
                fn = p.func
                if isinstance(fn, ast.Attribute) and fn.attr == "get" and isinstance(fn.value, ast.Name) and fn.value.id == "tm":
                    continue

            violations.append(f"{rel}:{getattr(node, 'lineno', '?')}")

    assert not violations, "Hardcoded Korean string literals found:\n" + "\n".join(violations)


def test_tm_get_keys_used_in_src_exist_in_both_languages():
    import src.core.i18n as i18n

    get_key_pattern = re.compile(r"tm\.get\(\s*['\"]([^'\"]+)['\"]")
    used_keys = set()

    for py in Path("src").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        used_keys.update(m.group(1) for m in get_key_pattern.finditer(text))

    ko = i18n.TRANSLATIONS["ko"]
    en = i18n.TRANSLATIONS["en"]

    missing_ko = sorted(k for k in used_keys if k not in ko)
    missing_en = sorted(k for k in used_keys if k not in en)

    assert not missing_ko, f"Missing KO i18n keys: {missing_ko}"
    assert not missing_en, f"Missing EN i18n keys: {missing_en}"
