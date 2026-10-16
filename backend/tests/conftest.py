import os
import tempfile
import pytest
from pathlib import Path
import sys

root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import create_app
from backend.database import init_db

@pytest.fixture
def app():
    # Use a temporary database for test isolation
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_PATH"] = db_path

    from backend import config
    config.DATABASE_PATH = db_path
    
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    with app.app_context():
        init_db(db_path)

    yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

import uuid

@pytest.fixture
def auth_headers(client):
    # Register with unique email to ensure clean isolation
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@example.com"
    res = client.post("/api/auth/register", json={
        "name": f"User {uid}",
        "email": email,
        "password": "Password123!",
    })
    data = res.get_json()
    token = data["token"]
    return {"Authorization": f"Bearer {token}", "X-User-Email": email}
