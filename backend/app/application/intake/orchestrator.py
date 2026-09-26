import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import replace
from pathlib import PurePath

from app.application.intake.commands import CreateIntakeBatch, IntakeFile
from app.core.clock import utc_now
from app.core.config import Settings
from app.core.ids import new_id
from app.core.logging import event
from app.domain.enums import BatchStatus
from app.domain.errors import (
    BatchTooLargeError,
    DomainError,
    IdempotencyConflictError,
    InvalidRequestError,
    MissingIdempotencyKeyError,
    TooManyFilesError,
    UnsupportedExtensionError,
)
from app.domain.models import BatchDetail, FileRecord
from app.domain.ports.file_registry import FileRegistry
from app.domain.ports.original_file_store import OriginalFileStore

logger = logging.getLogger(__name__)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def display_name(filename: str) -> str:
    name = PurePath(filename.replace("\\", "/")).name
    name = _CONTROL_CHARACTERS.sub("", unicodedata.normalize("NFC", name)).strip()
    return (name or "unnamed-file")[:500]


def extension_of(filename: str) -> str | None:
    suffix = PurePath(filename).suffix.lower().removeprefix(".")
    return suffix or None


def request_fingerprint(command: CreateIntakeBatch) -> str:
    payload = {
        "project_id": command.project_id,
        "source_kind": command.source_kind.value,
        "source_description": command.source_description,
        "submitted_by": command.submitted_by,
        "files": [display_name(item.filename) for item in command.files],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class IntakeOrchestrator:
    def __init__(
        self,
        *,
        registry: FileRegistry,
        file_store: OriginalFileStore,
        settings: Settings,
    ) -> None:
        self._registry = registry
        self._file_store = file_store
        self._settings = settings

    async def execute(self, command: CreateIntakeBatch) -> BatchDetail:
        self._validate(command)
        fingerprint = request_fingerprint(command)
        existing = self._registry.get_batch_by_idempotency_key(command.idempotency_key)
        if existing:
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError("相同幂等键已用于不同的摄取请求。")
            detail = self._registry.get_batch_detail(existing.batch_id)
            if detail is None:
                raise RuntimeError("Existing batch cannot be loaded")
            return detail

        batch_id = new_id()
        created_at = utc_now()
        self._registry.create_batch(
            batch_id=batch_id,
            project_id=command.project_id.strip(),
            source_kind=command.source_kind,
            source_description=command.source_description,
            submitted_by=command.submitted_by,
            idempotency_key=command.idempotency_key,
            request_fingerprint=fingerprint,
            total_count=len(command.files),
            created_at=created_at,
        )
        event(logger, "intake_batch_created", batch_id=batch_id, file_count=len(command.files))

        registered_count = 0
        failed_count = 0
        consumed_bytes = 0
        duplicates: list[FileRecord] = []
        try:
            for upload in command.files:
                file_id = new_id()
                succeeded, size, duplicate = await self._process_file(
                    batch_id=batch_id,
                    file_id=file_id,
                    project_id=command.project_id.strip(),
                    upload=upload,
                    remaining_batch_bytes=max(0, self._settings.max_batch_bytes - consumed_bytes),
                )
                consumed_bytes += size
                if succeeded:
                    registered_count += 1
                else:
                    failed_count += 1
                if duplicate is not None:
                    duplicates.append(duplicate)
        finally:
            await self._file_store.cleanup_batch(batch_id)

        if registered_count == len(command.files):
            status = BatchStatus.COMPLETED
        elif registered_count == 0:
            status = BatchStatus.FAILED
        else:
            status = BatchStatus.PARTIAL
        self._registry.complete_batch(
            batch_id=batch_id,
            status=status,
            registered_count=registered_count,
            failed_count=failed_count,
            completed_at=utc_now(),
        )
        event(
            logger,
            "intake_batch_completed",
            batch_id=batch_id,
            status=status.value,
            registered=registered_count,
            failed=failed_count,
        )
        detail = self._registry.get_batch_detail(batch_id)
        if detail is None:
            raise RuntimeError("Completed batch cannot be loaded")
        result = replace(detail, duplicates=tuple(duplicates))
        if duplicates and not detail.files:
            self._registry.delete_empty_batch(batch_id)
        return result

    def _validate(self, command: CreateIntakeBatch) -> None:
        if not command.idempotency_key.strip():
            raise MissingIdempotencyKeyError("请求必须包含 Idempotency-Key。")
        if not command.project_id.strip():
            raise InvalidRequestError("project_id 不能为空。")
        if not command.files:
            raise InvalidRequestError("至少需要提交一个文件。")
        if len(command.files) > self._settings.max_files_per_batch:
            raise TooManyFilesError("文件数量超过单批次限制。")

    async def _process_file(
        self,
        *,
        batch_id: str,
        file_id: str,
        project_id: str,
        upload: IntakeFile,
        remaining_batch_bytes: int,
    ) -> tuple[bool, int, FileRecord | None]:
        original_name = upload.filename or "unnamed-file"
        safe_name = display_name(original_name)
        extension = extension_of(safe_name)
        try:
            if extension not in self._settings.allowed_extensions:
                raise UnsupportedExtensionError(f"不支持 .{extension or 'unknown'} 文件。")
            if remaining_batch_bytes <= 0:
                raise BatchTooLargeError("批次已经达到大小限制。")
            effective_limit = min(self._settings.max_file_bytes, remaining_batch_bytes)
            blob = await self._file_store.store(
                batch_id=batch_id,
                file_id=file_id,
                source=upload.stream,
                max_bytes=effective_limit,
                chunk_bytes=self._settings.upload_chunk_bytes,
            )
            duplicate = self._registry.register_file(
                file_id=file_id,
                batch_id=batch_id,
                project_id=project_id,
                original_name=original_name,
                display_name=safe_name,
                client_media_type=upload.content_type,
                extension=extension,
                blob=blob,
                registered_at=utc_now(),
            )
            event(
                logger,
                "intake_duplicate_rejected" if duplicate else "intake_file_registered",
                batch_id=batch_id,
                file_id=file_id,
                size_bytes=blob.size_bytes,
                reused_blob=not blob.created_new,
            )
            if duplicate is not None:
                duplicate_attempt = replace(
                    duplicate,
                    file_id=file_id,
                    batch_id=batch_id,
                    project_id=project_id,
                    original_name=original_name,
                    display_name=safe_name,
                    client_media_type=upload.content_type,
                    duplicate_of_file_id=duplicate.file_id,
                    registered_at=utc_now(),
                    created_at=utc_now(),
                )
                return False, blob.size_bytes, duplicate_attempt
            return True, blob.size_bytes, None
        except DomainError as exc:
            failure: DomainError = exc
            if exc.code == "file-too-large" and remaining_batch_bytes < self._settings.max_file_bytes:
                failure = BatchTooLargeError("文件使当前批次超过大小限制。")
            self._record_failure(
                batch_id=batch_id,
                file_id=file_id,
                project_id=project_id,
                original_name=original_name,
                display_name=safe_name,
                content_type=upload.content_type,
                extension=extension,
                code=failure.code,
                message=failure.detail,
            )
            return False, 0, None
        except Exception:
            logger.exception("Unexpected file intake failure", extra={"batch_id": batch_id, "file_id": file_id})
            self._record_failure(
                batch_id=batch_id,
                file_id=file_id,
                project_id=project_id,
                original_name=original_name,
                display_name=safe_name,
                content_type=upload.content_type,
                extension=extension,
                code="storage-unavailable",
                message="文件登记期间发生内部存储错误。",
            )
            return False, 0, None

    def _record_failure(
        self,
        *,
        batch_id: str,
        file_id: str,
        project_id: str,
        original_name: str,
        display_name: str,
        content_type: str | None,
        extension: str | None,
        code: str,
        message: str,
    ) -> None:
        self._registry.record_failed_file(
            file_id=file_id,
            batch_id=batch_id,
            project_id=project_id,
            original_name=original_name,
            display_name=display_name,
            client_media_type=content_type,
            extension=extension,
            failure_code=code,
            failure_message=message,
            created_at=utc_now(),
        )
        event(logger, "intake_file_failed", batch_id=batch_id, file_id=file_id, failure_code=code)
