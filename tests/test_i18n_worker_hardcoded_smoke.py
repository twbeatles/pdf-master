import ast
import re
from pathlib import Path


TARGET_WORKER_FILES = [
    "src/core/worker_ops/ai_ops.py",
    "src/core/worker_ops/batch_ops.py",
    "src/core/worker_ops/annotation_ops.py",
    "src/core/worker_ops/extract_ops.py",
]


def test_target_worker_emit_calls_do_not_use_direct_string_literals():
    violations = []

    for rel in TARGET_WORKER_FILES:
        source = Path(rel).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "emit":
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Attribute) or owner.attr not in {"finished_signal", "error_signal"}:
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                violations.append(f"{rel}:{node.lineno}")

    assert not violations, "Direct string emits found:\n" + "\n".join(violations)


def test_worker_get_msg_keys_exist_in_both_languages():
    import src.core.i18n as i18n

    pattern = re.compile(r'_get_msg\(\s*[\'"]([^\'"]+)[\'"]')
    used_keys = set()

    for py in Path("src/core/worker_ops").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        used_keys.update(match.group(1) for match in pattern.finditer(text))

    ko = i18n.TRANSLATIONS["ko"]
    en = i18n.TRANSLATIONS["en"]

    missing_ko = sorted(key for key in used_keys if key not in ko)
    missing_en = sorted(key for key in used_keys if key not in en)

    assert not missing_ko, f"Missing KO worker i18n keys: {missing_ko}"
    assert not missing_en, f"Missing EN worker i18n keys: {missing_en}"
