import json

def test_chat_sse_stream(client, auth_headers):
    # First upload an invoice document
    import io
    doc_content = b"Invoice #1042\nTotal Amount: $42,500\nPayment Due Date: October 28, 2026\nAccount: Bharath S"
    upload_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_content), "invoice.txt")},
        content_type="multipart/form-data",
    )
    doc_id = upload_res.get_json()["id"]

    # Send chat query
    payload = {
        "conversation_id": None,
        "message": "What is the total amount due?",
        "attachment_ids": [doc_id],
        "via_voice": False,
    }

    res = client.post("/api/chat", headers=auth_headers, json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.content_type

    # Parse SSE text
    raw_text = res.data.decode("utf-8")
    assert "event: meta" in raw_text
    assert "event: sources" in raw_text
    assert "event: done" in raw_text

    # Extract conversation_id from meta
    lines = raw_text.split("\n")
    events = []
    current_event = None
    for line in lines:
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            data_str = line[6:].strip()
            events.append((current_event, json.loads(data_str)))

    event_names = [e[0] for e in events]
    assert "meta" in event_names
    assert "sources" in event_names
    assert "done" in event_names

    # Check sources
    sources_data = next(e[1] for e in events if e[0] == "sources")
    assert len(sources_data) > 0
    assert any("invoice.txt" in s.get("source", "") for s in sources_data)

    # Check done
    done_data = next(e[1] for e in events if e[0] == "done")
    assert "latency_ms" in done_data
    assert "model" in done_data
