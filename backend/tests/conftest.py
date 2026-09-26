from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def runtime_root(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


@pytest.fixture
def settings(runtime_root: Path) -> Settings:
    return Settings(
        runtime_root=runtime_root,
        database_url=f"sqlite:///{(runtime_root / 'registry' / 'test.db').as_posix()}",
        max_file_bytes=1024 * 1024,
        max_batch_bytes=2 * 1024 * 1024,
        max_files_per_batch=5,
        upload_chunk_bytes=7,
        allowed_extensions=("pdf", "docx", "xlsx", "md", "csv", "txt"),
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client

