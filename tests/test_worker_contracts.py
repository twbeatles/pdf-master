import ast
from pathlib import Path


def test_split_by_pages_contract_matches_current_ui_modes():
    from src.core.worker_runtime.dispatch import OPERATION_SPECS

    assert OPERATION_SPECS["split_by_pages"].required_kwargs == ("output_dir",)


def test_ui_run_worker_calls_satisfy_static_required_kwargs():
    from src.core.worker_runtime.dispatch import OPERATION_SPECS

    violations = []
    for path in Path("src/ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "run_worker":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                continue

            mode = node.args[0].value
            spec = OPERATION_SPECS.get(mode)
            if spec is None or not spec.required_kwargs:
                continue

            if any(keyword.arg is None for keyword in node.keywords):
                continue

            supplied = {keyword.arg for keyword in node.keywords if keyword.arg}
            if len(node.args) >= 2:
                supplied.add("output_path")

            missing = sorted(set(spec.required_kwargs) - supplied)
            if missing:
                violations.append(f"{path}:{node.lineno}: {mode} missing {missing}")

    assert not violations, "run_worker contract violations:\n" + "\n".join(violations)
