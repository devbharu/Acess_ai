from backend.database import get_db

def test_conversations_empty(client, auth_headers):
    res = client.get("/api/conversations", headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json() == []

def test_conversation_lifecycle(client, auth_headers):
    email = auth_headers["X-User-Email"]
    # Insert a conversation directly
    cid = "conv_test_123"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, title) VALUES (?, (SELECT id FROM users WHERE email = ?), ?)",
            (cid, email, "Monthly Invoice Analysis"),
        )
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES ('m1', ?, 'user', 'What is the balance?')",
            (cid,),
        )
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES ('m2', ?, 'assistant', 'The balance is $150.')",
            (cid,),
        )

    # 1. List conversations
    res = client.get("/api/conversations", headers=auth_headers)
    assert res.status_code == 200
    convs = res.get_json()
    assert len(convs) == 1
    assert convs[0]["id"] == cid
    assert convs[0]["title"] == "Monthly Invoice Analysis"

    # 2. Get messages
    m_res = client.get(f"/api/conversations/{cid}/messages", headers=auth_headers)
    assert m_res.status_code == 200
    msgs = m_res.get_json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "The balance is $150."

    # 3. Rename
    ren_res = client.put(f"/api/conversations/{cid}", headers=auth_headers, json={"title": "Updated Invoice"})
    assert ren_res.status_code == 200
    assert ren_res.get_json()["title"] == "Updated Invoice"

    # 4. Delete
    del_res = client.delete(f"/api/conversations/{cid}", headers=auth_headers)
    assert del_res.status_code == 204

    # Verify deleted
    list_after = client.get("/api/conversations", headers=auth_headers)
    assert list_after.get_json() == []


def test_conversation_media_isolation(client, auth_headers):
    """Test that media uploaded to one chat is private and never visible in another chat."""
    import io
    from backend.services.context import ContextResolver
    from backend.services.tools import list_conversation_files

    cid_a = "conv_private_alpha"
    cid_b = "conv_private_beta"
    email = auth_headers["X-User-Email"]

    with get_db() as conn:
        conn.execute("INSERT INTO conversations (id, user_id, title) VALUES (?, (SELECT id FROM users WHERE email = ?), 'Alpha')", (cid_a, email))
        conn.execute("INSERT INTO conversations (id, user_id, title) VALUES (?, (SELECT id FROM users WHERE email = ?), 'Beta')", (cid_b, email))

    # Upload doc to conv_alpha
    res_a = client.post(
        "/api/documents",
        headers=auth_headers,
        data={
            "file": (io.BytesIO(b"Alpha Secret Data: Formula X-42."), "alpha_secret.txt"),
            "conversation_id": cid_a,
        },
        content_type="multipart/form-data",
    )
    assert res_a.status_code == 201
    doc_a_id = res_a.get_json()["id"]

    # Upload doc to conv_beta
    res_b = client.post(
        "/api/documents",
        headers=auth_headers,
        data={
            "file": (io.BytesIO(b"Beta Public Report: Status Normal."), "beta_report.txt"),
            "conversation_id": cid_b,
        },
        content_type="multipart/form-data",
    )
    assert res_b.status_code == 201
    doc_b_id = res_b.get_json()["id"]

    # 1. API attachments endpoint check
    atts_a = client.get(f"/api/conversations/{cid_a}/attachments", headers=auth_headers).get_json()
    assert len(atts_a) == 1
    assert atts_a[0]["id"] == doc_a_id
    assert atts_a[0]["name"] == "alpha_secret.txt"

    atts_b = client.get(f"/api/conversations/{cid_b}/attachments", headers=auth_headers).get_json()
    assert len(atts_b) == 1
    assert atts_b[0]["id"] == doc_b_id
    assert atts_b[0]["name"] == "beta_report.txt"

    # 2. ContextResolver check - verify other conversation's media is never leaked
    with get_db() as conn:
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]
    media_a = ContextResolver.get_scoped_media(user_id=user_id, conversation_id=cid_a)
    media_a_ids = [d["id"] for d in media_a["documents"]]
    assert doc_a_id in media_a_ids
    assert doc_b_id not in media_a_ids

    media_b = ContextResolver.get_scoped_media(user_id=user_id, conversation_id=cid_b)
    media_b_ids = [d["id"] for d in media_b["documents"]]
    assert doc_b_id in media_b_ids
    assert doc_a_id not in media_b_ids

    # 3. Tool list check
    files_a = list_conversation_files(user_id=user_id, conversation_id=cid_a)
    assert len(files_a) == 1
    assert files_a[0]["id"] == doc_a_id

    files_b = list_conversation_files(user_id=user_id, conversation_id=cid_b)
    assert len(files_b) == 1
    assert files_b[0]["id"] == doc_b_id

