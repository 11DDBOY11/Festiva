"""Test configuration and fixtures for Festiva AI backend targeting PostgreSQL."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.db.base import Base
from app.main import app

# Target PostgreSQL database for testing
DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.TEST_DATABASE_URL)

# Enforce hermetic unit tests: no unit test calls live Groq
os.environ["LLM_PROVIDER"] = "fake"
settings.LLM_PROVIDER = "fake"


@pytest.fixture(autouse=True)
def enforce_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure all unit tests use FakeLLMClient; live LLM calls reserved for eval --live."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_PROVIDER", "fake")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    """Ensure schema is created on PostgreSQL, truncate data after each test."""
    Base.metadata.create_all(bind=engine)
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a scoped database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
