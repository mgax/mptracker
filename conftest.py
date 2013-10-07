import pytest
from mock import Mock


class MockSession:

    def __init__(self):
        self.url_map = {}
        self.hooks = []

    def get(self, url, hooks=[]):
        file_path = self.url_map[url]
        content = file_path.bytes()
        return Mock(content=content)


@pytest.fixture
def session():
    return MockSession()
