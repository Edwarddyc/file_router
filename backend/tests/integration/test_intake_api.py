import hashlib
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def upload(
    client: TestClient,
    *,
    key: str,
    files: list[tuple[str, bytes, str]],
    project_id: str = "project-1",
):
    return client.post(
        "/api/v1/intake/batches",
        headers={"Idempotency-Key": key},
        data={"project_id": project_id, "source_kind": "user-upload"},
        files=[("files", item) for item in files],
    )


def test_upload_query_and_download(client: TestClient, runtime_root: Path) -> None:
    content = b"# Project background\nsource material"
    response = upload(client, key="upload-1", files=[("notes.md", content, "text/markdown")])
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["registered_count"] == 1
    item = payload["files"][0]
    assert item["status"] == "registered"
    assert item["sha256"] == hashlib.sha256(content).hexdigest()

    details = client.get(f"/api/v1/files/{item['file_id']}")
    assert details.status_code == 200
    assert details.json()["blob_integrity_status"] == "available"

    downloaded = client.get(f"/api/v1/files/{item['file_id']}/content")
    assert downloaded.status_code == 200
    assert downloaded.content == content

    blobs = [path for path in (runtime_root / "originals").rglob("*") if path.is_file()]
    assert len(blobs) == 1
    assert "notes.md" not in str(blobs[0])


def test_duplicate_content_reuses_blob_without_creating_a_second_file_record(
    client: TestClient,
    runtime_root: Path,
) -> None:
    content = b"same-content"
    first = upload(client, key="duplicate-1", files=[("first.txt", content, "text/plain")]).json()
    second = upload(client, key="duplicate-2", files=[("second.txt", content, "text/plain")]).json()

    first_file = first["files"][0]
    assert first_file["is_content_duplicate"] is False
    assert second["status"] == "failed"
    assert second["registered_count"] == 0
    assert second["failed_count"] == 1
    assert second["files"] == []
    assert len(second["duplicates"]) == 1
    duplicate = second["duplicates"][0]
    assert duplicate["display_name"] == "second.txt"
    assert duplicate["duplicate_of_file_id"] == first_file["file_id"]
    assert duplicate["is_content_duplicate"] is True
    assert len([path for path in (runtime_root / "originals").rglob("*") if path.is_file()]) == 1

    listed = client.get("/api/v1/files", params={"project_id": "project-1"})
    assert listed.status_code == 200
    listed_items = listed.json()["items"]
    assert len(listed_items) == 1
    assert listed_items[0]["file_id"] == first_file["file_id"]
    assert listed_items[0]["is_content_duplicate"] is False
    assert listed_items[0]["duplicate_of_file_id"] is None

    with sqlite3.connect(runtime_root / "registry" / "test.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM file_records").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM ingest_batches").fetchone()[0] == 1


def test_backend_does_not_expose_duplicate_reset_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/files/duplicates/reset")
    assert response.status_code == 404


def test_idempotent_retry_returns_original_batch(client: TestClient) -> None:
    args = {"key": "same-request", "files": [("data.csv", b"a,b\n1,2\n", "text/csv")]}
    first = upload(client, **args)
    second = upload(client, **args)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["batch_id"] == second.json()["batch_id"]
    assert first.json()["files"][0]["file_id"] == second.json()["files"][0]["file_id"]


def test_idempotency_conflict(client: TestClient) -> None:
    assert upload(client, key="conflict", files=[("one.txt", b"one", "text/plain")]).status_code == 201
    response = upload(client, key="conflict", files=[("two.txt", b"two", "text/plain")])
    assert response.status_code == 409
    assert response.json()["code"] == "idempotency-conflict"


def test_partial_batch_records_failure(client: TestClient) -> None:
    response = upload(
        client,
        key="partial",
        files=[
            ("valid.txt", b"ok", "text/plain"),
            ("blocked.exe", b"MZ", "application/octet-stream"),
        ],
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["registered_count"] == 1
    assert payload["failed_count"] == 1
    failed = next(item for item in payload["files"] if item["status"] == "failed")
    assert failed["failure_code"] == "unsupported-extension"


def test_missing_idempotency_key_uses_problem_details(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intake/batches",
        data={"project_id": "project-1"},
        files=[("files", ("notes.txt", b"ok", "text/plain"))],
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "missing-idempotency-key"
