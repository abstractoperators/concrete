from unittest.mock import Mock, patch

import pytest

from concrete.tools import HTTPTool


def test_http_tool_process_response():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.content = 'example content'
    assert HTTPTool._process_response(mock_response) == 'example content'
