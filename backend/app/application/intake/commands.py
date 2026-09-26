from dataclasses import dataclass

from app.domain.enums import SourceKind
from app.domain.ports.original_file_store import AsyncUpload


@dataclass(frozen=True, slots=True)
class IntakeFile:
    filename: str
    content_type: str | None
    stream: AsyncUpload


@dataclass(frozen=True, slots=True)
class CreateIntakeBatch:
    project_id: str
    source_kind: SourceKind
    source_description: str | None
    submitted_by: str | None
    idempotency_key: str
    files: tuple[IntakeFile, ...]

