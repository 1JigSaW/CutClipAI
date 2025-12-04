import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://cutclipai:cutclipai@localhost:5432/cutclipai"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    TEMP_DIR: Path = Path("./data/temp")
    OUTPUT_DIR: Path = Path("./data/output")

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_API_URL: str = "https://api.telegram.org"

    API_BASE_URL: str = "http://localhost:8000"

    WHISPER_MODEL: str = "medium"
    FORCE_CPU: bool = False

    VIDEO_MAX_DURATION_SECONDS: int = 1800
    CLIP_MIN_DURATION_SECONDS: int = 20
    CLIP_MAX_DURATION_SECONDS: int = 60
    MAX_CLIPS_COUNT: int = 3

    START_BALANCE_COINS: int = 5
    COINS_PER_CLIP: int = 1

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "cutclipai"
    S3_ENDPOINT_URL: Optional[str] = None

    GOOGLE_DRIVE_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

