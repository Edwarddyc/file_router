from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import BatchStatus
from app.domain.models import BatchDetail
from app.schemas.files import FileRecordDto


class IngestBatchDto(BaseModel):
    batch_id: str
    project_id: str
    source_kind: str
    source_description: str | None
    submitted_by: str | None
    status: BatchStatus
    total_count: int
    registered_count: int
    failed_count: int
    created_at: datetime
    completed_at: datetime | None
    files: list[FileRecordDto]
    duplicates: list[FileRecordDto]

    @classmethod
    def from_domain(cls, detail: BatchDetail) -> "IngestBatchDto":
        batch = detail.batch
        return cls(
            batch_id=batch.batch_id,
            project_id=batch.project_id,
            source_kind=batch.source_kind.value,
            source_description=batch.source_description,
            submitted_by=batch.submitted_by,
            status=batch.status,
            total_count=batch.total_count,
            registered_count=batch.registered_count,
            failed_count=batch.failed_count,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
            files=[FileRecordDto.from_domain(item) for item in detail.files],
            duplicates=[FileRecordDto.from_domain(item) for item in detail.duplicates],
        )
