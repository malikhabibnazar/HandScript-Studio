"""Runtime configuration.

Local development defaults to SQLite, a folder for generated files, and an
in-process worker. Docker Compose points the same settings at PostgreSQL,
Redis, and S3-compatible storage.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/handscript.db"
    redis_url: str = ""
    embedded_worker: bool = True
    s3_endpoint: str = ""
    s3_bucket: str = "handscript"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    storage_dir: str = "./data/files"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    worker_tick_seconds: float = 0.45
    handwriting_engine: str = "graves"
    graves_enabled: bool = True
    graves_weights_path: str = "./data/graves/weights.npz"
    graves_styles_dir: str = "./data/graves/styles"
    graves_default_style_id: int = 9
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-pro-preview"
    onedm_enabled: bool = True
    onedm_weights_path: str = "./data/onedm/weights/epoch-ckpt.pt"
    onedm_device: str = "auto"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def uses_s3(self) -> bool:
        return bool(self.s3_endpoint and self.s3_access_key and self.s3_secret_key)

    @property
    def database_dialect(self) -> str:
        return self.database_url.split(":", 1)[0]


@lru_cache
def get_settings() -> Settings:
    return Settings()
