# -*- coding: utf-8 -*-
"""Фикстуры pytest: изолированная SQLite-БД и тестовый клиент."""
import os
import sys
import tempfile
from pathlib import Path

# Тестовая БД до импорта приложения
_tmpdir = tempfile.mkdtemp(prefix="balance_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmpdir) / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _db():
    """Свежая БД для каждого теста (изоляция данных между тестами)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user_token(client: TestClient) -> str:
    resp = client.post("/api/auth/register", json={
        "email": "student@guap.ru",
        "username": "Студент",
        "password": "secret123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
