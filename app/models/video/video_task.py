from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, BigInteger, String, DateTime, Enum as SQLEnum, Text

from app.core.database import Base


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
    )
    task_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )
    user_id = Column(
        BigInteger,
        nullable=False,
        index=True,
    )
    status = Column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    input_file_path = Column(
        String,
        nullable=True,
    )
    output_file_path = Column(
        String,
        nullable=True,
    )
    error_message = Column(
        Text,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    completed_at = Column(
        DateTime,
        nullable=True,
    )

