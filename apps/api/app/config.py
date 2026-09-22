from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://reelforge:reelforge@postgres:5432/reelforge"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint_internal: str = "http://minio:9000"   # usado por API y workers dentro de la red
    s3_endpoint_public: str = "http://localhost:9000"  # usado para URLs firmadas que abre el navegador
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "reelforge"
    s3_region: str = "us-east-1"

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    max_upload_bytes: int = 5 * 1024**3
    max_video_seconds: int = 4 * 3600
    upload_part_size: int = 16 * 1024**2

    min_highlight_seconds: float = 15.0
    max_highlight_seconds: float = 90.0
    min_clip_seconds: float = 3.0
    max_clip_seconds: float = 180.0
    export_ttl_hours: int = 72

    cors_origins: str = "*"
    default_user_email: str = "dev@reelforge.local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
