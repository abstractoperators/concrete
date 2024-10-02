from unittest.mock import Mock, patch

import pytest
from requests.exceptions import HTTPError

from concrete.tools import HTTPTool


def test_http_tool_process_response_ok():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.content = 'example content'

    assert HTTPTool._process_response(mock_response, '') == 'example content'


def test_http_tool_process_response_not_ok():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404

    mock_response.raise_for_status.side_effect = HTTPError
    with pytest.raises(HTTPError):
        HTTPTool._process_response(mock_response, '')


@patch('concrete.tools.HTTPClient')
def test_http_tool_request(mock_http_client):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.content = 'example content'

    mock_client_instance = mock_http_client.return_value
    mock_client_instance.request.return_value = mock_response

    res = HTTPTool.request('GET', 'http://example.com')

    mock_client_instance.request.assert_called_once_with('GET', 'http://example.com')
    assert res == 'example content'


# @patch('concrete.tools.AwsTool.boto3')  # being imported from within AwsTool
# def test_aws_tool_poll_service_status(mock_boto3):
#     mock_client_instance = mock_boto3.client.return_value

#     mock_client_instance.describe_services.side_effect = [
#         {'services': [{'desiredCount': 1, 'runningCount': 0, 'pendingCount': 1}]},
#         {'services': [{'desiredCount': 1, 'runningCount': 1, 'pendingCount': 0}]},
#     ]

#     service_active = AwsTool._poll_service_status("example_service")

#     assert service_active is True
#     assert mock_client_instance.describe_services.call_count == 2
#     mock_client_instance.describe_services.assert_any_call(cluster="DemoCluster", services=["example_service"])
