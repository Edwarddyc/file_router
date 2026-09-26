from pathlib import Path
from typing import Protocol

from app.domain.models import StoredBlob


class AsyncUpload(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class OriginalFileStore(Protocol):
    async def store(
        self,
        *,
        batch_id: str,
        file_id: str,
        source: AsyncUpload,
        max_bytes: int,
        chunk_bytes: int,
    ) -> StoredBlob: ...

    async def cleanup_batch(self, batch_id: str) -> None: ...

    def resolve(self, storage_key: str) -> Path: ...

    def is_ready(self) -> bool: ...

