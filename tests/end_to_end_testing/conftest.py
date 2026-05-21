# tests/end_to_end_testing/conftest.py
import os
import pytest
from fastapi.testclient import TestClient

# Import your app object
# If your app is in the root, you might need 'from main import app'
from src.Server.main import app

@pytest.fixture(scope="module")
def client():
    """
    This setup runs once per test file (module).
    It handles the startup and shutdown of the FastAPI app.
    """
    if "GROQ_API_KEY" not in os.environ:
        os.environ["GROQ_API_KEY"] = "fake_key_for_testing"

    with TestClient(app) as c:
        yield c
