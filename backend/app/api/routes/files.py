import logging
from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.dependencies import Container, get_container
from app.core.logging import event
from app.domain.enums import FileStatus, IntegrityStatus
from app.domain.errors import FileNotFoundError, InvalidRequestError
from app.schemas.files import FileDetailDto, FileListDto

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)


@router.get("", response_model=FileListDto)
def list_files(
    container: Annotated[Container, Depends(get_container)],
    project_id: str | None = None,
    file_status: Annotated[FileStatus | None, Query(alias="status")] = None,
    sha256: str | None = None,
    limit: Annotated[int, Query(ge=1)] = 50,
    cursor: str | None = None,
) -> FileListDto:
    effective_limit = min(limit, container.settings.list_max_limit)
    try:
        page = container.registry.list_files(
            project_id=project_id,
            status=file_status,
            sha256=sha256,
            limit=effective_limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise InvalidRequestError("分页 cursor 无效。") from exc
    return FileListDto.from_domain(page)


@router.get("/{file_id}", response_model=FileDetailDto)
def get_file(
    file_id: str,
    container: Annotated[Container, Depends(get_container)],
) -> FileDetailDto:
    detail = container.registry.get_file_detail(file_id)
    if detail is None:
        raise FileNotFoundError("未找到指定文件。")
    if detail.blob and not container.file_store.resolve(detail.blob.storage_key).is_file():
        detail = replace(detail, blob=replace(detail.blob, integrity_status=IntegrityStatus.MISSING))
    return FileDetailDto.from_detail(detail)


@router.get("/{file_id}/content", response_class=FileResponse)
def download_file(
    file_id: str,
    container: Annotated[Container, Depends(get_container)],
) -> FileResponse:
    detail = container.registry.get_file_detail(file_id)
    if detail is None or detail.blob is None or detail.file.status is not FileStatus.REGISTERED:
        raise FileNotFoundError("文件内容不存在。")
    path = container.file_store.resolve(detail.blob.storage_key)
    if not path.is_file():
        raise FileNotFoundError("文件内容不存在。")
    event(logger, "original_file_downloaded", file_id=file_id, batch_id=detail.file.batch_id)
    return FileResponse(
        path=path,
        filename=detail.file.display_name,
        media_type=detail.file.detected_media_type or detail.file.client_media_type or "application/octet-stream",
    )
