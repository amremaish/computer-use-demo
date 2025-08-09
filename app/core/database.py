from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy import create_engine, text
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

# Lightweight migration to add message_type enum/column if missing (Postgres only)
def _ensure_message_type_column():
    try:
        with engine.begin() as conn:
            # Check if column exists
            col_exists = conn.execute(text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name='messages' AND column_name='message_type'
                """
            )).first() is not None

            if not col_exists:
                # Ensure enum type exists
                type_exists = conn.execute(text(
                    "SELECT 1 FROM pg_type WHERE typname = 'message_type'"
                )).first() is not None
                if not type_exists:
                    conn.execute(text("CREATE TYPE message_type AS ENUM ('text','image')"))

                # Add column with default
                conn.execute(text(
                    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type message_type NOT NULL DEFAULT 'text'"
                ))

                # Best-effort backfill: mark as image if any block shows type=image
                conn.execute(text(
                    """
                    UPDATE messages
                    SET message_type = 'image'
                    WHERE message_type = 'text' AND content::text LIKE '%"type":"image"%'
                    """
                ))
    except Exception:
        # Fail silently; app can still run even if migration didn't apply
        pass

_ensure_message_type_column()

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 