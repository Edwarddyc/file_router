from dataclasses import dataclass
from typing import cast

from fastapi import Request
from sqlalchemy import Engine

from app.application.intake.orchestrator import IntakeOrchestrator
from app.core.config import Settings
from app.infrastructure.database.registry_repository import SqlAlchemyFileRegistry
from app.infrastructure.storage.local_original_file_store import LocalOriginalFileStore


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: Engine
    registry: SqlAlchemyFileRegistry
    file_store: LocalOriginalFileStore
    intake: IntakeOrchestrator


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)
