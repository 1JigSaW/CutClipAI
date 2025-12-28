from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    url=settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """
    Database session dependency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
        logger.warning(
            f"Failed to initialize database | error={e} | "
            f"database_url={settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'hidden'}. "
            f"Some features may not work without database connection."
        )

