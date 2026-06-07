from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://bimportal:bimportal@localhost:5432/bimportal"
    upload_dir: Path = Path("./storage/uploads")
    converted_dir: Path = Path("./storage/converted")
    superset_url: str = "http://localhost:8088"
    superset_internal_url: str = "http://localhost:8088"
    superset_admin_user: str = "admin"
    superset_admin_password: str = "admin"
    superset_dashboard_id: str = ""


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.converted_dir.mkdir(parents=True, exist_ok=True)
    return settings
