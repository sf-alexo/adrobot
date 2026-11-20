from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _BACKEND_DIR / "adrobot.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    keitaro_base_url: str = "https://your-tracker.example"
    keitaro_api_key: str = ""
    # Absolute path so cwd does not matter for uvicorn / alembic.
    database_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
