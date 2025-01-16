from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.exceptions import HTTPException
from fastapi.testclient import TestClient

# TODO: Fix import. webapp doesn't have an init, and mypy has implicit namespacing disabled.
from webapp.agentserver import server as agentserver  # type: ignore

test_client: TestClient = TestClient(agentserver.app)


@pytest.fixture
def setenv(monkeypatch):
    monkeypatch.setenv("ENV", "test")


@pytest.fixture
def mock_operator():
    ids = []

    def _create_operator():
        operator_id = uuid4()
        ids.append(operator_id)
        mock_operator = MagicMock()
        agentserver.operators[operator_id] = mock_operator
        return operator_id, mock_operator

    yield _create_operator

    for operator_id in ids:
        if operator_id in agentserver.operators:  # Check because endpoint can also delete.
            agentserver.operators.pop(operator_id)


def test_operator_chat_endpoint(mock_operator, setenv):
    """
    Tests /chat/{operator_id} endpoint to ensure that the chat method is called.
    TODO: Update return value for endpoint, and test that as well.
    """
    operator_id, mock_operator = mock_operator()

    payload = "Mocked chat request"

    mock_operator.chat.return_value.text = "Mocked chat response"

    response = test_client.post(f"/chat/{operator_id}", json={"message": payload})

    assert response.status_code == 200

    mock_operator.chat.assert_called_once_with("Mocked chat request")


def test_operator_delete_endpoint(mock_operator, setenv):
    """
    Tests delete /operators/{operator_id} endpoint to ensure that the operator is deleted.
    TODO: Check db to make sure operator is deleted post stateful PR.
    """
    operator_id, mock_operator = mock_operator()

    response = test_client.delete(f"/operators/{operator_id}")

    assert response.status_code == 200

    assert operator_id not in agentserver.operators


def test_operator_get_endpoint(mock_operator, setenv):
    """
    Tests get /operators/{operator_id} endpoint to make sure the right information is retrieved.
    """
    operator_id, mock_operator = mock_operator()
    mock_operator.instructions = "Mocked instructions"

    mock_tool1 = MagicMock()
    mock_tool1.__name__ = "mock_tool1"
    mock_tool2 = MagicMock()
    mock_tool2.__name__ = "mock_tool2"
    mock_operator.tools = [mock_tool1, mock_tool2]

    response = test_client.get(f"/operators/{operator_id}").json()

    assert UUID(response['operator_id']) == operator_id
    assert response['instructions'] == "Mocked instructions"
    assert response['tools'] == ["mock_tool1", "mock_tool2"]


def test_operator_list_endpoint(mock_operator, setenv):
    """
    Tests get /operators endpoint to make sure all uuids are returned.
    """
    operator_id1, mock_operator1 = mock_operator()
    operator_id2, mock_operator2 = mock_operator()

    response = test_client.get("/operators").json()

    assert str(operator_id1) in response['operators']
    assert str(operator_id2) in response['operators']


def test_operator_create_endpoint(setenv):
    """
    Tests post /operators endpoint to make sure a new operator is created.
    """
    response = test_client.post(
        "/operators",
        json={'instructions': 'Mocked instructions'},
    ).json()

    assert response['instructions'] == 'Mocked instructions'
    assert UUID(response['operator_id']) in agentserver.operators


def test_operator_update_endpoint(mock_operator, setenv):
    """
    Tests patch /operators/{operator_id} endpoint to ensure that the operator is updated."""
    operator_id, mock_operator = mock_operator()

    response = test_client.patch(
        f"/operators/{operator_id}",
        json={'instructions': 'Updated mock instructions'},
    ).json()

    assert response['instructions'] == 'Updated mock instructions'
    assert UUID(response['operator_id']) in agentserver.operators

    try:
        response = test_client.patch(
            f"/operators/{uuid4()}",
            json={'instructions': 'Updated mock instructions'},
        ).json()
    except HTTPException as e:
        assert e.status_code == 404
