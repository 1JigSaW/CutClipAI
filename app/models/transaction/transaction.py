from datetime import datetime
from enum import Enum

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, Enum as SQLEnum

from app.core.database import Base


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    CHARGE = "charge"
    REFUND = "refund"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    type = Column(
        SQLEnum(TransactionType),
        nullable=False,
    )
    amount = Column(
        Integer,
        nullable=False,
    )
    description = Column(
        String,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

