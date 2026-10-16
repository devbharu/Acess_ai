def test_get_settings_default(client, auth_headers):
    res = client.get("/api/settings", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["model"] == "gemma4:31b-cloud"
    assert "temperature" in data
    assert "system_prompt" in data

def test_update_settings(client, auth_headers):
    patch = {
        "model": "gpt-oss:20b-cloud",
        "temperature": 0.45,
        "grounded_only": False,
    }
    res = client.put("/api/settings", headers=auth_headers, json=patch)
    assert res.status_code == 200
    data = res.get_json()
    assert data["model"] == "gpt-oss:20b-cloud"
    assert data["temperature"] == 0.45
    assert data["grounded_only"] is False

    # Verify persistent retrieval
    get_res = client.get("/api/settings", headers=auth_headers)
    assert get_res.get_json()["model"] == "gpt-oss:20b-cloud"
