"""Application settings, loaded from environment variables (.env supported)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Same credentials as docker-compose.yml (host port 5434 on this machine).
    database_url: str = (
        "postgresql+psycopg://votoscope:votoscope@localhost:5434/votoscope"
    )

    # Bronze: directory holding the immutable source files.
    raw_dir: Path = REPO_ROOT / "data" / "raw"


settings = Settings()
