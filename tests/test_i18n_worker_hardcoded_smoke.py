import ast
import re
from pathlib import Path


TARGET_WORKER_FILES = sorted(Path("src/core/worker_ops").rglob("*.py"))


def test_target_worker_emit_calls_do_not_use_direct_string_literals():
    violations = []

    def is_i18n_message_call(node):
        if not isinstance(node, ast.Call):
            return False
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr in {"_get_msg", "get"}:
            return True
        if isinstance(fn, ast.Name) and fn.id == "get_message":
            return True
        return False

    def contains_direct_string_message(node):
        if is_i18n_message_call(node):
            return False
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if isinstance(node, ast.JoinedStr):
            return True
        return any(contains_direct_string_message(child) for child in ast.iter_child_nodes(node))

    for path in TARGET_WORKER_FILES:
        rel = str(path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)

        function_taints: dict[ast.AST, set[str]] = {}
        for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            tainted: set[str] = set()
            for node in ast.walk(function):
                if isinstance(node, ast.Assign) and contains_direct_string_message(node.value):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            tainted.add(target.id)
                elif isinstance(node, ast.AnnAssign) and node.value and contains_direct_string_message(node.value):
                    if isinstance(node.target, ast.Name):
                        tainted.add(node.target.id)
                elif isinstance(node, ast.AugAssign) and contains_direct_string_message(node.value):
                    if isinstance(node.target, ast.Name):
                        tainted.add(node.target.id)
            function_taints[function] = tainted

        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node

        def owner_function(node):
            current = parent.get(node)
            while current is not None:
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return current
                current = parent.get(current)
            return None

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
            elif isinstance(first_arg, ast.JoinedStr):
                violations.append(f"{rel}:{node.lineno}")
            elif isinstance(first_arg, ast.Name):
                function = owner_function(node)
                if function is not None and first_arg.id in function_taints.get(function, set()):
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
