import hashlib
import os
from pathlib import Path

import anyio

from app.domain.errors import EmptyFileError, FileTooLargeError, IntegrityConflictError
from app.domain.models import StoredBlob
from app.domain.ports.original_file_store import AsyncUpload


class LocalOriginalFileStore:
    def __init__(self, runtime_root: Path) -> None:
        self._runtime_root = runtime_root.resolve()
        self._staging_root = (self._runtime_root / "staging").resolve()
        self._originals_root = (self._runtime_root / "originals" / "sha256").resolve()

    async def store(
        self,
        *,
        batch_id: str,
        file_id: str,
        source: AsyncUpload,
        max_bytes: int,
        chunk_bytes: int,
    ) -> StoredBlob:
        batch_dir = (self._staging_root / batch_id).resolve()
        self._ensure_within(batch_dir, self._staging_root)
        batch_dir.mkdir(parents=True, exist_ok=True)
        temporary = (batch_dir / f"{file_id}.upload").resolve()
        self._ensure_within(temporary, batch_dir)

        digest = hashlib.sha256()
        size = 0
        try:
            async with await anyio.open_file(temporary, "xb") as target:
                while chunk := await source.read(chunk_bytes):
                    size += len(chunk)
                    if size > max_bytes:
                        raise FileTooLargeError("文件超过当前允许的大小限制。")
                    digest.update(chunk)
                    await target.write(chunk)
                await target.flush()

            if size == 0:
                raise EmptyFileError("空文件不能登记。")

            sha256 = digest.hexdigest()
            storage_key = f"sha256/{sha256[:2]}/{sha256[2:4]}/{sha256}"
            destination = (self._runtime_root / "originals" / storage_key).resolve()
            self._ensure_within(destination, self._originals_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            created_new = await anyio.to_thread.run_sync(self._promote, temporary, destination, size)
            return StoredBlob(
                sha256=sha256,
                size_bytes=size,
                storage_key=storage_key,
                created_new=created_new,
            )
        except Exception:
            await self._unlink_if_exists(temporary)
            raise

    async def cleanup_batch(self, batch_id: str) -> None:
        batch_dir = (self._staging_root / batch_id).resolve()
        self._ensure_within(batch_dir, self._staging_root)
        if batch_dir.exists():
            await anyio.to_thread.run_sync(self._remove_empty_directory, batch_dir)

    def resolve(self, storage_key: str) -> Path:
        path = (self._runtime_root / "originals" / storage_key).resolve()
        self._ensure_within(path, self._originals_root)
        return path

    def is_ready(self) -> bool:
        return self._staging_root.is_dir() and self._originals_root.is_dir()

    @staticmethod
    def _ensure_within(path: Path, root: Path) -> None:
        if not path.is_relative_to(root):
            raise ValueError("Resolved path escapes configured storage root")

    @staticmethod
    def _promote(temporary: Path, destination: Path, expected_size: int) -> bool:
        try:
            os.link(temporary, destination)
            temporary.unlink()
            try:
                destination.chmod(0o444)
            except OSError:
                pass
            return True
        except FileExistsError as exc:
            if destination.stat().st_size != expected_size:
                raise IntegrityConflictError("已存在的 Blob 与上传内容大小不一致。") from exc
            temporary.unlink(missing_ok=True)
            return False

    @staticmethod
    def _remove_empty_directory(path: Path) -> None:
        try:
            path.rmdir()
        except OSError:
            pass

    @staticmethod
    async def _unlink_if_exists(path: Path) -> None:
        if path.exists():
            await anyio.to_thread.run_sync(path.unlink, True)
