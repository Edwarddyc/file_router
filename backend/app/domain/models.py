from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import BatchStatus, FileStatus, IntegrityStatus, SourceKind


@dataclass(frozen=True, slots=True)
class StoredBlob:
    sha256: str
    size_bytes: int
    storage_key: str
    created_new: bool
    detected_media_type: str | None = None


@dataclass(frozen=True, slots=True)
class OriginalBlob:
    sha256: str
    size_bytes: int
    storage_key: str
    detected_media_type: str | None
    integrity_status: IntegrityStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FileRecord:
    file_id: str
    batch_id: str
    project_id: str
    original_name: str
    display_name: str
    client_media_type: str | None
    detected_media_type: str | None
    extension: str | None
    size_bytes: int | None
    sha256: str | None
    duplicate_of_file_id: str | None
    source_uri: str | None
    status: FileStatus
    failure_code: str | None
    failure_message: str | None
    registered_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IngestBatch:
    batch_id: str
    project_id: str
    source_kind: SourceKind
    source_description: str | None
    submitted_by: str | None
    idempotency_key: str
    request_fingerprint: str
    status: BatchStatus
    total_count: int
    registered_count: int
    failed_count: int
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class BatchDetail:
    batch: IngestBatch
    files: tuple[FileRecord, ...]
    duplicates: tuple[FileRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class FileDetail:
    file: FileRecord
    batch: IngestBatch
    blob: OriginalBlob | None


@dataclass(frozen=True, slots=True)
class FilePage:
    items: tuple[FileRecord, ...]
    next_cursor: str | None
