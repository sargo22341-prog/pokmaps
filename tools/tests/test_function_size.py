import ast
import os
from pathlib import Path


def _oversized_functions(source: str) -> list[str]:
    tree = ast.parse(source)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            start = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
            assert node.end_lineno is not None
            lines = node.end_lineno - start + 1
            if lines > 60:
                offenders.append(f"{node.name} ({lines} lignes)")
    return offenders


def test_python_functions_stay_under_60_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    excluded = {"build", ".venv", ".cache", "__pycache__", ".ruff_cache", ".pytest_cache"}
    files = []
    for directory, children, names in os.walk(root):
        children[:] = [child for child in children if child not in excluded]
        files.extend(Path(directory) / name for name in names if name.endswith(".py"))
    assert len(files) > 100
    offenders = [
        f"{file.relative_to(root)}:{function}"
        for file in files
        for function in _oversized_functions(file.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_counts_decorators_and_async_functions_at_the_limit() -> None:
    valid = "@decorator\nasync def valid():\n" + "    pass\n" * 58
    assert _oversized_functions(valid) == []
    assert _oversized_functions(valid + "    pass\n") == ["valid (61 lignes)"]


def test_counts_nested_functions_without_parsing_text_in_strings() -> None:
    source = "def outer():\n    def local():\n" + "        pass\n" * 60
    assert _oversized_functions(source) == ["outer (62 lignes)", "local (61 lignes)"]
    assert _oversized_functions('def valid():\n    return "def fake():"') == []
