import os
import pathlib
import pytest
from starlette.testclient import TestClient


TEST_DB = pathlib.Path("test.db")


@pytest.fixture(scope="session", autouse=True)
def test_env():
    # Ensure a fresh on-disk SQLite for tests
    if TEST_DB.exists():
        TEST_DB.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture()
def client(test_env):
    # Import here so env is set before app engine is created
    from app.main import app
    with TestClient(app) as c:
        yield c
