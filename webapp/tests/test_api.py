import pytest
from fastapi.testclient import TestClient

from ..api.server import app


@pytest.mark.parametrize("client", [app], indirect=True)
def test_initialize_project(client: TestClient):
    response = client.post(
        "/projects/dag/",
        json={
            "name": "test_project",
        },
    )

    assert response.status_code == 401
    # TODO: remove auth or add to request body above
    # data = response.json()

    # assert response.status_code == 200
    # assert data["name"] == "test_project"
    # assert "id" in data
    # assert data["created_at"] is not None
    # assert data["modified_at"] is not None
