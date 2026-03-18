import ast
from pathlib import Path


TARGET_METHODS = [
    "get_pdf_info",
    "get_bookmarks",
    "set_bookmarks",
    "search_text",
    "extract_tables",
    "decrypt_pdf",
    "list_annotations",
    "add_annotation",
    "remove_annotations",
    "add_attachment",
    "extract_attachments",
]


def test_target_worker_methods_have_try_finally_for_resource_cleanup():
    methods = {}
    for path in Path("src/core/worker_ops").glob("*.py"):
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.setdefault(node.name, []).append(node)

    missing = []
    for method in TARGET_METHODS:
        nodes = methods.get(method)
        if not nodes:
            missing.append(method)
            continue
        has_try_finally = any(
            isinstance(child, ast.Try) and bool(child.finalbody)
            for node in nodes
            for child in ast.walk(node)
        )
        if not has_try_finally:
            missing.append(method)

    assert not missing, f"Missing try/finally resource cleanup: {missing}"
