import re
from pathlib import Path

import pytest


@pytest.mark.skip(reason="TODO: ensure server logs only to stderr and rotating file")
def test_no_stdout_output_from_tools():
    pass


def test_no_print_statements_in_codebase():
    """Ensure no stray print statements remain in server source."""
    src = Path(__file__).resolve().parents[1] / "UnityMcpBridge" / "UnityMcpServer~" / "src"
    assert src.exists(), f"Server source directory not found: {src}"
    offenders = []
    for py_file in src.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if re.search(r"^\s*print\(", text, re.MULTILINE):
            offenders.append(py_file.relative_to(src))
    assert not offenders, f"print statements found in: {offenders}"
