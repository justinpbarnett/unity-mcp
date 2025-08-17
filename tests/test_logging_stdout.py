import re
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
    raise FileNotFoundError(
        "Unity MCP server source not found. Tried:\n" + searched
    )


@pytest.mark.skip(reason="TODO: ensure server logs only to stderr and rotating file")
def test_no_stdout_output_from_tools():
    pass


def test_no_print_statements_in_codebase():
    """Ensure no stray print statements remain in server source."""
    offenders = []
    for py_file in SRC.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if re.search(r"^\s*print\(", text, re.MULTILINE):
            offenders.append(py_file.relative_to(SRC))
    assert not offenders, f"print statements found in: {offenders}"
