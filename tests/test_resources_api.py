import pytest


@pytest.mark.xfail(strict=False, reason="resource.list should return only Assets/**/*.cs and reject traversal")
def test_resource_list_filters_and_rejects_traversal():
    pass


@pytest.mark.xfail(strict=False, reason="resource.list should reject outside paths including drive letters and symlinks")
def test_resource_list_rejects_outside_paths():
    pass
