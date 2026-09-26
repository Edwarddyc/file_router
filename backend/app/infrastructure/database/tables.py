from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class IngestBatchRow(Base):
    __tablename__ = "ingest_batches"

    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(200), index=True)
    source_kind: Mapped[str] = mapped_column(String(30))
    source_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), index=True)
    total_count: Mapped[int] = mapped_column(Integer)
    registered_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    files: Mapped[list["FileRecordRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class OriginalBlobRow(Base):
    __tablename__ = "original_blobs"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(300), unique=True)
    detected_media_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    integrity_status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    files: Mapped[list["FileRecordRow"]] = relationship(back_populates="blob")


class FileRecordRow(Base):
    __tablename__ = "file_records"

    file_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingest_batches.batch_id"), index=True)
    project_id: Mapped[str] = mapped_column(String(200), index=True)
    original_name: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(500))
    client_media_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detected_media_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(ForeignKey("original_blobs.sha256"), nullable=True, index=True)
    duplicate_of_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("file_records.file_id"), nullable=True
    )
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    batch: Mapped[IngestBatchRow] = relationship(back_populates="files")
    blob: Mapped[OriginalBlobRow | None] = relationship(back_populates="files")


Index("ix_file_records_created_file", FileRecordRow.created_at.desc(), FileRecordRow.file_id.desc())
