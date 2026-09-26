import base64
import json
from datetime import UTC, datetime

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.enums import BatchStatus, FileStatus, IntegrityStatus, SourceKind
from app.domain.errors import IdempotencyConflictError
from app.domain.models import (
    BatchDetail,
    FileDetail,
    FilePage,
    FileRecord,
    IngestBatch,
    OriginalBlob,
    StoredBlob,
)
from app.infrastructure.database.tables import FileRecordRow, IngestBatchRow, OriginalBlobRow


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _batch(row: IngestBatchRow) -> IngestBatch:
    return IngestBatch(
        batch_id=row.batch_id,
        project_id=row.project_id,
        source_kind=SourceKind(row.source_kind),
        source_description=row.source_description,
        submitted_by=row.submitted_by,
        idempotency_key=row.idempotency_key,
        request_fingerprint=row.request_fingerprint,
        status=BatchStatus(row.status),
        total_count=row.total_count,
        registered_count=row.registered_count,
        failed_count=row.failed_count,
        created_at=_as_utc(row.created_at),  # type: ignore[arg-type]
        completed_at=_as_utc(row.completed_at),
    )


def _file(row: FileRecordRow) -> FileRecord:
    return FileRecord(
        file_id=row.file_id,
        batch_id=row.batch_id,
        project_id=row.project_id,
        original_name=row.original_name,
        display_name=row.display_name,
        client_media_type=row.client_media_type,
        detected_media_type=row.detected_media_type,
        extension=row.extension,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        duplicate_of_file_id=row.duplicate_of_file_id,
        source_uri=row.source_uri,
        status=FileStatus(row.status),
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        registered_at=_as_utc(row.registered_at),
        created_at=_as_utc(row.created_at),  # type: ignore[arg-type]
    )


def _blob(row: OriginalBlobRow) -> OriginalBlob:
    return OriginalBlob(
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        storage_key=row.storage_key,
        detected_media_type=row.detected_media_type,
        integrity_status=IntegrityStatus(row.integrity_status),
        created_at=_as_utc(row.created_at),  # type: ignore[arg-type]
    )


def _encode_cursor(created_at: datetime, file_id: str) -> str:
    payload = json.dumps([created_at.isoformat(), file_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created, file_id = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(created), str(file_id)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid cursor") from exc


class SqlAlchemyFileRegistry:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

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
    ) -> IngestBatch:
        row = IngestBatchRow(
            batch_id=batch_id,
            project_id=project_id,
            source_kind=source_kind.value,
            source_description=source_description,
            submitted_by=submitted_by,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            status=BatchStatus.RECEIVING.value,
            total_count=total_count,
            registered_count=0,
            failed_count=0,
            created_at=created_at,
            completed_at=None,
        )
        try:
            with self._sessions.begin() as session:
                session.add(row)
        except IntegrityError as exc:
            raise IdempotencyConflictError("该幂等键已经被另一个请求使用。") from exc
        return _batch(row)

    def get_batch_by_idempotency_key(self, key: str) -> IngestBatch | None:
        with self._sessions() as session:
            row = session.scalar(select(IngestBatchRow).where(IngestBatchRow.idempotency_key == key))
            return _batch(row) if row else None

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
    ) -> FileRecord | None:
        with self._sessions.begin() as session:
            blob_row = session.get(OriginalBlobRow, blob.sha256)
            if blob_row is None:
                blob_row = OriginalBlobRow(
                    sha256=blob.sha256,
                    size_bytes=blob.size_bytes,
                    storage_key=blob.storage_key,
                    detected_media_type=blob.detected_media_type,
                    integrity_status=IntegrityStatus.AVAILABLE.value,
                    created_at=registered_at,
                )
                session.add(blob_row)
                session.flush()
            elif blob_row.size_bytes != blob.size_bytes:
                raise ValueError("Existing blob metadata conflicts with uploaded content")

            duplicate = session.scalar(
                select(FileRecordRow)
                .where(FileRecordRow.sha256 == blob.sha256, FileRecordRow.status == FileStatus.REGISTERED.value)
                .order_by(FileRecordRow.created_at.asc(), FileRecordRow.file_id.asc())
                .limit(1)
            )
            if duplicate is not None:
                return _file(duplicate)
            session.add(
                FileRecordRow(
                    file_id=file_id,
                    batch_id=batch_id,
                    project_id=project_id,
                    original_name=original_name,
                    display_name=display_name,
                    client_media_type=client_media_type,
                    detected_media_type=blob.detected_media_type,
                    extension=extension,
                    size_bytes=blob.size_bytes,
                    sha256=blob.sha256,
                    duplicate_of_file_id=None,
                    source_uri=None,
                    status=FileStatus.REGISTERED.value,
                    failure_code=None,
                    failure_message=None,
                    registered_at=registered_at,
                    created_at=registered_at,
                )
            )
            return None

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
    ) -> None:
        with self._sessions.begin() as session:
            session.add(
                FileRecordRow(
                    file_id=file_id,
                    batch_id=batch_id,
                    project_id=project_id,
                    original_name=original_name,
                    display_name=display_name,
                    client_media_type=client_media_type,
                    detected_media_type=None,
                    extension=extension,
                    size_bytes=None,
                    sha256=None,
                    duplicate_of_file_id=None,
                    source_uri=None,
                    status=FileStatus.FAILED.value,
                    failure_code=failure_code,
                    failure_message=failure_message,
                    registered_at=None,
                    created_at=created_at,
                )
            )

    def complete_batch(
        self,
        *,
        batch_id: str,
        status: BatchStatus,
        registered_count: int,
        failed_count: int,
        completed_at: datetime,
    ) -> None:
        with self._sessions.begin() as session:
            row = session.get(IngestBatchRow, batch_id)
            if row is None:
                raise KeyError(batch_id)
            row.status = status.value
            row.registered_count = registered_count
            row.failed_count = failed_count
            row.completed_at = completed_at

    def get_batch_detail(self, batch_id: str) -> BatchDetail | None:
        with self._sessions() as session:
            batch_row = session.get(IngestBatchRow, batch_id)
            if batch_row is None:
                return None
            file_rows = session.scalars(
                select(FileRecordRow)
                .where(FileRecordRow.batch_id == batch_id)
                .order_by(FileRecordRow.created_at.asc(), FileRecordRow.file_id.asc())
            ).all()
            return BatchDetail(_batch(batch_row), tuple(_file(row) for row in file_rows))

    def get_file_detail(self, file_id: str) -> FileDetail | None:
        with self._sessions() as session:
            file_row = session.get(FileRecordRow, file_id)
            if file_row is None:
                return None
            batch_row = session.get(IngestBatchRow, file_row.batch_id)
            if batch_row is None:
                return None
            blob_row = session.get(OriginalBlobRow, file_row.sha256) if file_row.sha256 else None
            return FileDetail(_file(file_row), _batch(batch_row), _blob(blob_row) if blob_row else None)

    def list_files(
        self,
        *,
        project_id: str | None,
        status: FileStatus | None,
        sha256: str | None,
        limit: int,
        cursor: str | None,
    ) -> FilePage:
        with self._sessions() as session:
            statement = select(FileRecordRow)
            if project_id:
                statement = statement.where(FileRecordRow.project_id == project_id)
            if status:
                statement = statement.where(FileRecordRow.status == status.value)
            if sha256:
                statement = statement.where(FileRecordRow.sha256 == sha256)
            if cursor:
                cursor_time, cursor_id = _decode_cursor(cursor)
                statement = statement.where(
                    or_(
                        FileRecordRow.created_at < cursor_time,
                        and_(FileRecordRow.created_at == cursor_time, FileRecordRow.file_id < cursor_id),
                    )
                )
            rows = session.scalars(
                statement.order_by(FileRecordRow.created_at.desc(), FileRecordRow.file_id.desc()).limit(limit + 1)
            ).all()
            has_more = len(rows) > limit
            page_rows = rows[:limit]
            next_cursor = None
            if has_more and page_rows:
                last = page_rows[-1]
                next_cursor = _encode_cursor(_as_utc(last.created_at), last.file_id)  # type: ignore[arg-type]
            return FilePage(tuple(_file(row) for row in page_rows), next_cursor)

    def delete_empty_batch(self, batch_id: str) -> None:
        with self._sessions.begin() as session:
            file_count = session.scalar(
                select(func.count()).select_from(FileRecordRow).where(FileRecordRow.batch_id == batch_id)
            )
            if file_count:
                raise ValueError("Cannot delete a batch that contains file records")
            session.execute(delete(IngestBatchRow).where(IngestBatchRow.batch_id == batch_id))

    def is_ready(self) -> bool:
        try:
            with self._sessions() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
