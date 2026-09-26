from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import Container, get_container

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(container: Annotated[Container, Depends(get_container)], response: Response) -> dict[str, object]:
    checks = {
        "registry": container.registry.is_ready(),
        "original_file_store": container.file_store.is_ready(),
    }
    ready_now = all(checks.values())
    if not ready_now:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ready_now else "not-ready", "checks": checks}

