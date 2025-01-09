from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from webapp.daemons import server as agentserver

test_client: TestClient = TestClient(agentserver.app)


@pytest.fixture
def setenv(monkeypatch):
    monkeypatch.setenv("ENV", "test")


@pytest.fixture
def mock_operator():
    operator_id = uuid4()
    mock_operator = MagicMock()
    agentserver.operators = {operator_id: mock_operator}
    return operator_id, mock_operator


def test_operator_chat_endpoint(mock_operator, setenv):
    """
    Tests /chat/{operator_id} endpoint to ensure that the chat method is called.
    TODO: Finalize return value for endpoint, and test that as well.
    """
    operator_id, mock_operator = mock_operator

    payload = "Mocked chat request"

    mock_operator.chat.return_value.text = "Mocked chat response"

    response = test_client.post(f"/chat/{operator_id}", json={"message": payload})

    assert response.status_code == 200

    mock_operator.chat.assert_called_once_with("Mocked chat request")

    agentserver.operators.pop(operator_id)


def test_operator_delete_endpoint(mock_operator, setenv):
    """
    Tests /delete/{operator_id} endpoint to ensure that the operator is deleted.
    TODO: Check db to make sure operator is deleted post stateful PR.
    """
    operator_id, mock_operator = mock_operator

    response = test_client.delete(f"/operators/{operator_id}")

    assert response.status_code == 200

    assert operator_id not in agentserver.operators
