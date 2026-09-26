from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status

from app.api.dependencies import Container, get_container
from app.application.intake.commands import CreateIntakeBatch, IntakeFile
from app.domain.enums import SourceKind
from app.domain.errors import BatchNotFoundError, MissingIdempotencyKeyError
from app.schemas.batches import IngestBatchDto

router = APIRouter(prefix="/intake/batches", tags=["intake"])


@router.post("", response_model=IngestBatchDto, status_code=status.HTTP_201_CREATED)
async def create_batch(
    project_id: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    container: Annotated[Container, Depends(get_container)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    source_kind: Annotated[SourceKind, Form()] = SourceKind.USER_UPLOAD,
    source_description: Annotated[str | None, Form()] = None,
    submitted_by: Annotated[str | None, Form()] = None,
) -> IngestBatchDto:
    if idempotency_key is None:
        raise MissingIdempotencyKeyError("请求必须包含 Idempotency-Key。")
    command = CreateIntakeBatch(
        project_id=project_id,
        source_kind=source_kind,
        source_description=source_description,
        submitted_by=submitted_by,
        idempotency_key=idempotency_key,
        files=tuple(
            IntakeFile(
                filename=item.filename or "unnamed-file",
                content_type=item.content_type,
                stream=item,
            )
            for item in files
        ),
    )
    try:
        detail = await container.intake.execute(command)
        return IngestBatchDto.from_domain(detail)
    finally:
        for item in files:
            await item.close()


@router.get("/{batch_id}", response_model=IngestBatchDto)
def get_batch(
    batch_id: str,
    container: Annotated[Container, Depends(get_container)],
) -> IngestBatchDto:
    detail = container.registry.get_batch_detail(batch_id)
    if detail is None:
        raise BatchNotFoundError("未找到指定摄取批次。")
    return IngestBatchDto.from_domain(detail)

