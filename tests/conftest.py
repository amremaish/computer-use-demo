import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core import database as core_db
from app.models import Base  # ensures models are imported


@pytest.fixture(autouse=True, scope="function")
def _override_db_dependency():
    # Use an in-memory SQLite database for tests (isolated from real Postgres)
    # Use StaticPool so the in-memory DB persists across connections within a test
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create schema for tests
    Base.metadata.create_all(bind=engine)

    def get_test_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Override FastAPI dependency for the duration of the test
    app.dependency_overrides[core_db.get_db] = get_test_db

    yield

    # Teardown: remove override
    app.dependency_overrides.pop(core_db.get_db, None)

