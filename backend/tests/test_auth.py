def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "SecretPassword1",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "token" in data
    assert data["user"]["name"] == "Alice"
    assert data["user"]["email"] == "alice@example.com"

def test_register_duplicate(client, auth_headers):
    email = auth_headers["X-User-Email"]
    res = client.post("/api/auth/register", json={
        "name": "Duplicate User",
        "email": email,
        "password": "NewPassword!",
    })
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]

def test_register_missing_fields(client):
    res = client.post("/api/auth/register", json={"name": "Bob"})
    assert res.status_code == 400

def test_login_success(client, auth_headers):
    email = auth_headers["X-User-Email"]
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "token" in data
    assert data["user"]["email"] == email

def test_login_bad_credentials(client, auth_headers):
    email = auth_headers["X-User-Email"]
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword",
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.get_json()["error"]

def test_me_endpoint(client, auth_headers):
    email = auth_headers["X-User-Email"]
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["email"] == email

    # Test update
    put_res = client.put("/api/auth/me", headers=auth_headers, json={"name": "Bharath S"})
    assert put_res.status_code == 200
    assert put_res.get_json()["name"] == "Bharath S"

def test_unauthorized_access(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    res_bad = client.get("/api/auth/me", headers={"Authorization": "Bearer badtoken"})
    assert res_bad.status_code == 401
