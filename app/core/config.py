import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://cutclipai:cutclipai@127.0.0.1:5444/cutclipai"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    FFMPEG_PATH: str = "/opt/homebrew/bin/ffmpeg"
    FFPROBE_PATH: str = "/opt/homebrew/bin/ffprobe"

    TEMP_DIR: Path = Path("./data/temp")
    OUTPUT_DIR: Path = Path("./data/output")

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_API_URL: str = "https://api.telegram.org"

    API_BASE_URL: str = "http://localhost:8000"

    WHISPER_MODEL: str = "medium"
    WHISPER_FAST_MODE: bool = True
    WHISPER_BEAM_SIZE: int = 1
    WHISPER_BEST_OF: int = 1
    FORCE_CPU: bool = False
    USE_GPU_ENCODING: bool = True
    FFMPEG_PRESET: str = "p1"
    FFMPEG_QUALITY: int = 23
    S3_MAX_CONCURRENCY: int = 5

    VIDEO_MAX_DURATION_SECONDS: int = 7200
    CLIP_MIN_DURATION_SECONDS: int = 15
    CLIP_MAX_DURATION_SECONDS: int = 45
    MAX_CLIPS_COUNT: int = 6
    CLIP_PROCESSING_MAX_WORKERS: int = 3
    
    SCORING_WEIGHT_ENERGY: float = 3.0
    SCORING_WEIGHT_TEMPO_VARIATION: float = 2.5
    SCORING_WEIGHT_PAUSES: float = 2.0
    SCORING_WEIGHT_PUNCTUATION: float = 1.5
    SCORING_WEIGHT_SPEECH_PACE: float = 2.0
    SCORING_WEIGHT_STRUCTURE: float = 2.5  # Bonus for video structure (beginning/end)
    SCORING_WEIGHT_HOOK: float = 3.0  # Bonus for hook patterns (questions, statements)
    SCORING_WEIGHT_LLM: float = 5.0  # Bonus from LLM analysis (if enabled)

    START_BALANCE_COINS: int = 6
    COINS_PER_CLIP: int = 1

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "cutclipai"
    S3_ENDPOINT_URL: Optional[str] = None

    GOOGLE_DRIVE_API_KEY: Optional[str] = None
    
    API_SECRET_KEY: str = "cutclipai_secret_key_change_me"
    
    # AssemblyAI for transcription
    ASSEMBLY_AI_API_KEY: Optional[str] = None
    
    # LLM API for analysis (supports multiple providers)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"  # OpenAI model name (for backward compatibility)
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # LLM configuration (format: provider:model)
    LLM: str = "openai:gpt-4o-mini"
    USE_LLM_ANALYSIS: bool = True
    
    # Flow integration (LangFlow or custom workflow)
    FLOW_API_URL: Optional[str] = None
    FLOW_API_KEY: Optional[str] = None
    USE_FLOW: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

