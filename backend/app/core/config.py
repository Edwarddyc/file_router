from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONTEXT_ROUTER_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "development"
    runtime_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "runtime")
    database_url: str | None = None
    max_file_bytes: int = 250 * 1024 * 1024
    max_batch_bytes: int = 1024 * 1024 * 1024
    max_files_per_batch: int = 100
    upload_chunk_bytes: int = 1024 * 1024
    allowed_extensions: tuple[str, ...] = ("pdf", "docx", "xlsx", "md", "csv", "txt")
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    list_default_limit: int = 50
    list_max_limit: int = 200

    @field_validator("runtime_root", mode="before")
    @classmethod
    def resolve_runtime_root(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser().resolve()
        return value

    @field_validator("allowed_extensions", "cors_origins", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        database_path = (self.runtime_root / "registry" / "registry.db").resolve()
        return f"sqlite:///{database_path.as_posix()}"

    def prepare_directories(self) -> None:
        for directory in (
            self.runtime_root,
            self.runtime_root / "staging",
            self.runtime_root / "originals" / "sha256",
            self.runtime_root / "registry",
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

