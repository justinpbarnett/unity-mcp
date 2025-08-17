import pytest


@pytest.mark.skip(reason="TODO: ensure server logs only to stderr and rotating file")
def test_no_stdout_output_from_tools():
    pass


@pytest.mark.skip(reason="TODO: sweep for accidental print statements in codebase")
def test_no_print_statements_in_codebase():
    pass
