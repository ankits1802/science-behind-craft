import os

os.environ.setdefault("DATABASE_URL", "postgresql://kalavigyan:kalavigyan@localhost:5432/kalavigyan_test")
os.environ.setdefault("JWT_SECRET", "test-only-signing-key-" + "k" * 40)
os.environ.setdefault("MASTER_ADMIN_EMAIL", "owner@kalavigyan.test")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRETS_ENCRYPTION_KEY", "")
os.environ.setdefault("TWO_FACTOR_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("BACKEND_CORS_ORIGINS", "http://localhost:3000")

import pytest

from app.core import rate_limit


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_DB_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="needs Postgres with pgvector and PostGIS; set RUN_DB_TESTS=1")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    rate_limit.reset_all()
