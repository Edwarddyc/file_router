from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import FileStatus, IntegrityStatus
from app.domain.models import FileDetail, FilePage, FileRecord


class FileRecordDto(BaseModel):
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
    is_content_duplicate: bool
    status: FileStatus
    failure_code: str | None
    failure_message: str | None
    registered_at: datetime | None
    created_at: datetime

    @classmethod
    def from_domain(cls, item: FileRecord) -> "FileRecordDto":
        values = {
            field: getattr(item, field)
            for field in cls.model_fields
            if field != "is_content_duplicate"
        }
        return cls(**values, is_content_duplicate=item.duplicate_of_file_id is not None)


class FileListDto(BaseModel):
    items: list[FileRecordDto]
    next_cursor: str | None

    @classmethod
    def from_domain(cls, page: FilePage) -> "FileListDto":
        return cls(
            items=[FileRecordDto.from_domain(item) for item in page.items],
            next_cursor=page.next_cursor,
        )


class FileDetailDto(FileRecordDto):
    source_kind: str
    source_description: str | None
    submitted_by: str | None
    blob_integrity_status: IntegrityStatus | None

    @classmethod
    def from_detail(cls, detail: FileDetail) -> "FileDetailDto":
        base = FileRecordDto.from_domain(detail.file).model_dump()
        return cls(
            **base,
            source_kind=detail.batch.source_kind.value,
            source_description=detail.batch.source_description,
            submitted_by=detail.batch.submitted_by,
            blob_integrity_status=detail.blob.integrity_status if detail.blob else None,
        )
