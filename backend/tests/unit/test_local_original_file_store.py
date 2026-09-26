import hashlib
from pathlib import Path

import pytest

from app.domain.errors import EmptyFileError, FileTooLargeError
from app.infrastructure.storage.local_original_file_store import LocalOriginalFileStore


class MemoryUpload:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._content)
        chunk = self._content[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


@pytest.mark.asyncio
async def test_store_hashes_stream_and_reuses_blob(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    (runtime / "staging").mkdir(parents=True)
    (runtime / "originals" / "sha256").mkdir(parents=True)
    store = LocalOriginalFileStore(runtime)
    content = b"streamed-content"

    first = await store.store(
        batch_id="batch-a",
        file_id="file-a",
        source=MemoryUpload(content),
        max_bytes=1024,
        chunk_bytes=3,
    )
    second = await store.store(
        batch_id="batch-b",
        file_id="file-b",
        source=MemoryUpload(content),
        max_bytes=1024,
        chunk_bytes=4,
    )

    assert first.sha256 == hashlib.sha256(content).hexdigest()
    assert first.created_new is True
    assert second.created_new is False
    assert store.resolve(first.storage_key).read_bytes() == content


@pytest.mark.asyncio
async def test_store_rejects_empty_and_oversized_files(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    (runtime / "staging").mkdir(parents=True)
    (runtime / "originals" / "sha256").mkdir(parents=True)
    store = LocalOriginalFileStore(runtime)

    with pytest.raises(EmptyFileError):
        await store.store(
            batch_id="empty",
            file_id="empty",
            source=MemoryUpload(b""),
            max_bytes=10,
            chunk_bytes=2,
        )
    with pytest.raises(FileTooLargeError):
        await store.store(
            batch_id="large",
            file_id="large",
            source=MemoryUpload(b"12345"),
            max_bytes=4,
            chunk_bytes=2,
        )

    assert not [path for path in (runtime / "staging").rglob("*.upload")]

