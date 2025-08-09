from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy import create_engine
from .config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Central SQLAlchemy declarative base used by all models
Base = declarative_base()

# Import models to register mappings with Base.metadata (after Base is defined)
from app import models  # noqa: F401,E402

# Create tables after models are imported
Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 