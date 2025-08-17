import pytest


@pytest.mark.skip(reason="TODO: resource.list returns only Assets/**/*.cs and rejects traversal")
def test_resource_list_filters_and_rejects_traversal():
    pass


@pytest.mark.skip(reason="TODO: resource.list rejects file:// paths outside project, including drive letters and symlinks")
def test_resource_list_rejects_outside_paths():
    pass
