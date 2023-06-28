import pytest
from fastapi.testclient import TestClient

from app.main import app

DB_URL_TEST = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@pytest.fixture
def client():
    return TestClient(app)
