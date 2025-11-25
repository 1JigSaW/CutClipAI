from datetime import datetime
from typing import Optional

from sqlalchemy import Column, BigInteger, Integer, DateTime

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
    )
    telegram_id = Column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    balance = Column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

