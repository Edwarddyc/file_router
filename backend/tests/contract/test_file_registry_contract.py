from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.clock import utc_now
from app.domain.enums import BatchStatus, FileStatus, SourceKind
from app.domain.models import StoredBlob
from app.infrastructure.database.migrations import upgrade_database
from app.infrastructure.database.registry_repository import SqlAlchemyFileRegistry
from app.infrastructure.database.session import create_database_engine, create_session_factory


def test_unique_content_migration_cleans_existing_duplicate_records(tmp_path: Path) -> None:
    database = tmp_path / "legacy-registry.db"
    database_url = f"sqlite:///{database.as_posix()}"
    backend_root = Path(__file__).resolve().parents[2]
    configuration = Config(str(backend_root / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend_root / "alembic"))
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(configuration, "0002")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO ingest_batches (
                    batch_id, project_id, source_kind, idempotency_key, request_fingerprint,
                    status, total_count, registered_count, failed_count, created_at
                ) VALUES (
                    'batch-legacy', 'project-1', 'user-upload', 'legacy-key', :fingerprint,
                    'completed', 2, 2, 0, :created_at
                )
                """
            ),
            {"fingerprint": "a" * 64, "created_at": "2026-09-24 00:00:00"},
        )
        connection.execute(
            text(
                """
                INSERT INTO ingest_batches (
                    batch_id, project_id, source_kind, idempotency_key, request_fingerprint,
                    status, total_count, registered_count, failed_count, created_at
                ) VALUES (
                    'batch-duplicate', 'project-1', 'user-upload', 'duplicate-key', :fingerprint,
                    'completed', 1, 1, 0, :created_at
                )
                """
            ),
            {"fingerprint": "c" * 64, "created_at": "2026-09-24 00:00:02"},
        )
        connection.execute(
            text(
                """
                INSERT INTO original_blobs (
                    sha256, size_bytes, storage_key, integrity_status, created_at
                ) VALUES (:sha256, 3, :storage_key, 'available', :created_at)
                """
            ),
            {
                "sha256": "b" * 64,
                "storage_key": f"sha256/bb/bb/{'b' * 64}",
                "created_at": "2026-09-24 00:00:00",
            },
        )
        for index in (1, 2):
            connection.execute(
                text(
                    """
                    INSERT INTO file_records (
                        file_id, batch_id, project_id, original_name, display_name,
                        size_bytes, sha256, duplicate_of_file_id, hidden_from_file_lists,
                        status, registered_at, created_at
                    ) VALUES (
                        :file_id, :batch_id, 'project-1', :name, :name,
                        3, :sha256, :duplicate_of, 0, 'registered', :created_at, :created_at
                    )
                    """
                ),
                {
                    "file_id": f"file-{index}",
                    "batch_id": "batch-legacy" if index == 1 else "batch-duplicate",
                    "name": f"file-{index}.txt",
                    "sha256": "b" * 64,
                    "duplicate_of": "file-1" if index == 2 else None,
                    "created_at": f"2026-09-24 00:00:0{index}",
                },
            )
    engine.dispose()

    command.upgrade(configuration, "0003")

    upgraded_engine = create_engine(database_url)
    with upgraded_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT file_id, sha256, content_duplicate_detected
                FROM file_records
                WHERE sha256 = :sha256
                """
            ),
            {"sha256": "b" * 64},
        ).mappings().all()
        assert rows == [
            {"file_id": "file-1", "sha256": "b" * 64, "content_duplicate_detected": 1}
        ]
        unique_indexes = {
            item["name"] for item in inspect(connection).get_indexes("file_records") if item["unique"]
        }
        assert "uq_file_records_sha256" in unique_indexes
    upgraded_engine.dispose()

    command.upgrade(configuration, "head")
    final_engine = create_engine(database_url)
    final_columns = {item["name"] for item in inspect(final_engine).get_columns("file_records")}
    assert "content_duplicate_detected" not in final_columns
    assert "hidden_from_file_lists" not in final_columns
    with final_engine.connect() as connection:
        remaining_batches = connection.execute(
            text("SELECT batch_id FROM ingest_batches ORDER BY batch_id")
        ).scalars().all()
        assert remaining_batches == ["batch-legacy"]
    final_engine.dispose()


def test_sqlalchemy_registry_enforces_unique_registered_content(tmp_path: Path) -> None:
    database = tmp_path / "registry.db"
    database_url = f"sqlite:///{database.as_posix()}"
    upgrade_database(database_url)
    engine = create_database_engine(database_url)
    registry = SqlAlchemyFileRegistry(create_session_factory(engine))
    now = utc_now()

    registry.create_batch(
        batch_id="batch-1",
        project_id="project-1",
        source_kind=SourceKind.USER_UPLOAD,
        source_description=None,
        submitted_by=None,
        idempotency_key="key-1",
        request_fingerprint="a" * 64,
        total_count=2,
        created_at=now,
    )
    blob = StoredBlob("b" * 64, 3, f"sha256/bb/bb/{'b' * 64}", True)
    registration_results = []
    for index in (1, 2):
        registration_results.append(registry.register_file(
            file_id=f"file-{index}",
            batch_id="batch-1",
            project_id="project-1",
            original_name=f"file-{index}.txt",
            display_name=f"file-{index}.txt",
            client_media_type="text/plain",
            extension="txt",
            blob=blob,
            registered_at=now,
        ))
    registry.complete_batch(
        batch_id="batch-1",
        status=BatchStatus.COMPLETED,
        registered_count=1,
        failed_count=1,
        completed_at=now,
    )

    detail = registry.get_batch_detail("batch-1")
    assert detail is not None
    assert detail.batch.status is BatchStatus.COMPLETED
    assert registration_results[0] is None
    assert registration_results[1] is not None
    assert registration_results[1].file_id == "file-1"
    assert len(detail.files) == 1
    assert detail.files[0].status is FileStatus.REGISTERED
    assert detail.files[0].sha256 == blob.sha256

    listed = registry.list_files(project_id=None, status=None, sha256=blob.sha256, limit=10, cursor=None)
    assert len(listed.items) == 1
    engine.dispose()
