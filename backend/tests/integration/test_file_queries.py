from fastapi.testclient import TestClient

from tests.integration.test_intake_api import upload


def test_file_list_filters_and_paginates(client: TestClient) -> None:
    upload(client, key="list-1", project_id="alpha", files=[("a.txt", b"a", "text/plain")])
    upload(client, key="list-2", project_id="alpha", files=[("b.txt", b"b", "text/plain")])
    upload(client, key="list-3", project_id="beta", files=[("c.txt", b"c", "text/plain")])

    first = client.get("/api/v1/files", params={"project_id": "alpha", "limit": 1})
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["items"]) == 1
    assert first_payload["next_cursor"]

    second = client.get(
        "/api/v1/files",
        params={"project_id": "alpha", "limit": 1, "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    assert len(second.json()["items"]) == 1
    assert second.json()["items"][0]["file_id"] != first_payload["items"][0]["file_id"]


def test_invalid_cursor_is_problem(client: TestClient) -> None:
    response = client.get("/api/v1/files", params={"cursor": "not-a-cursor"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid-request"


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"registry": True, "original_file_store": True}

