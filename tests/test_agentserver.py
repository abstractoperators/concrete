from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from webapp.daemons import server as agentserver

test_client: TestClient = TestClient(agentserver.app)


@pytest.fixture
def mock_operator():
    operator_id = uuid4()
    mock_operator = MagicMock()
    agentserver.operators = {operator_id: mock_operator}
    return operator_id, mock_operator


def test_operator_chat_endpoint(mock_operator):
    operator_id, mock_operator = mock_operator

    chat_response = "Mocked chat response"
    payload = "Mocked chat request"

    mock_operator.chat.return_value.text = chat_response

    response = test_client.post(f"/chat/{operator_id}", json={"message": payload})

    assert response.status_code == 200
    assert response.json() == {"message": chat_response}

    mock_operator.chat.assert_called_once_with("Mocked chat request")

    agentserver.operators.pop(operator_id)
