import ast
from pathlib import Path

import pytest


# locate server src dynamically to avoid hardcoded layout assumptions
ROOT = Path(__file__).resolve().parents[1]
candidates = [
    ROOT / "UnityMcpBridge" / "UnityMcpServer~" / "src",
    ROOT / "UnityMcpServer~" / "src",
]
SRC = next((p for p in candidates if p.exists()), None)
if SRC is None:
    searched = "\n".join(str(p) for p in candidates)
    pytest.skip(
        "Unity MCP server source not found. Tried:\n" + searched,
        allow_module_level=True,
    )


@pytest.mark.skip(reason="TODO: ensure server logs only to stderr and rotating file")
def test_no_stdout_output_from_tools():
    pass


def test_no_print_statements_in_codebase():
    """Ensure no stray print/sys.stdout writes remain in server source."""
    offenders = []
    syntax_errors = []
    for py_file in SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            # Be tolerant of encoding edge cases in source tree
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text, filename=str(py_file))
        except SyntaxError:
            syntax_errors.append(py_file.relative_to(SRC))
            continue

        class StdoutVisitor(ast.NodeVisitor):
            def __init__(self):
                self.hit = False

            def visit_Call(self, node: ast.Call):
                # print(...)
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    self.hit = True
                # builtins.print(...)
                elif (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "print"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "builtins"
                ):
                    self.hit = True
                # sys.stdout.write(...)
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "write"
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "stdout"
                    and isinstance(node.func.value.value, ast.Name)
                    and node.func.value.value.id == "sys"
                ):
                    self.hit = True
                self.generic_visit(node)

        v = StdoutVisitor()
        v.visit(tree)
        if v.hit:
            offenders.append(py_file.relative_to(SRC))

    assert not syntax_errors, "syntax errors in: " + ", ".join(str(e) for e in syntax_errors)
    assert not offenders, "stdout writes found in: " + ", ".join(str(o) for o in offenders)
