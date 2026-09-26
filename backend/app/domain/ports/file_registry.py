from datetime import datetime
from typing import Protocol

from app.domain.enums import BatchStatus, FileStatus, SourceKind
from app.domain.models import BatchDetail, FileDetail, FilePage, FileRecord, IngestBatch, StoredBlob


class FileRegistry(Protocol):
    def create_batch(
        self,
        *,
        batch_id: str,
        project_id: str,
        source_kind: SourceKind,
        source_description: str | None,
        submitted_by: str | None,
        idempotency_key: str,
        request_fingerprint: str,
        total_count: int,
        created_at: datetime,
    ) -> IngestBatch: ...

    def get_batch_by_idempotency_key(self, key: str) -> IngestBatch | None: ...

    def register_file(
        self,
        *,
        file_id: str,
        batch_id: str,
        project_id: str,
        original_name: str,
        display_name: str,
        client_media_type: str | None,
        extension: str | None,
        blob: StoredBlob,
        registered_at: datetime,
    ) -> FileRecord | None: ...

    def record_failed_file(
        self,
        *,
        file_id: str,
        batch_id: str,
        project_id: str,
        original_name: str,
        display_name: str,
        client_media_type: str | None,
        extension: str | None,
        failure_code: str,
        failure_message: str,
        created_at: datetime,
    ) -> None: ...

    def complete_batch(
        self,
        *,
        batch_id: str,
        status: BatchStatus,
        registered_count: int,
        failed_count: int,
        completed_at: datetime,
    ) -> None: ...

    def get_batch_detail(self, batch_id: str) -> BatchDetail | None: ...

    def get_file_detail(self, file_id: str) -> FileDetail | None: ...

    def list_files(
        self,
        *,
        project_id: str | None,
        status: FileStatus | None,
        sha256: str | None,
        limit: int,
        cursor: str | None,
    ) -> FilePage: ...

    def delete_empty_batch(self, batch_id: str) -> None: ...

    def is_ready(self) -> bool: ...
