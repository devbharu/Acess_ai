import json
import io
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from backend.services.orchestrator import ActivityTracker, generate_activity_summary, Orchestrator


def _create_test_png() -> bytes:
    im = Image.new("RGB", (80, 80), color="orange")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _create_test_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("Introduction to Manufacturing", styles["Heading1"])]
    doc.build(story)
    return buf.getvalue()


def test_activity_tracker_lifecycle():
    events = []
    def sink(event_type, payload):
        events.append((event_type, payload))

    tracker = ActivityTracker(task_id="task_test_1", conversation_id="conv_test_1", callback=sink)
    act = tracker.start_tool("Reading document outline", "outline", {"file": "sample.pdf", "total_pages": 12})
    assert act["status"] == "running"
    assert act["label"] == "Reading document outline"
    assert len(events) == 2  # tool_started, status_update

    tracker.complete_tool(act, detail="Parsed 4 main sections", metadata_patch={"pages": 12})
    assert act["status"] == "completed"
    assert act["duration_ms"] >= 1
    assert act["detail"] == "Parsed 4 main sections"
    assert any(e[0] == "tool_completed" for e in events)

    # Test failure state
    act_fail = tracker.start_tool("Executing OCR on corrupted image", "ocr")
    tracker.fail_tool(act_fail, error="Unrecognized image format")
    assert act_fail["status"] == "failed"
    assert act_fail["error"] == "Unrecognized image format"
    assert any(e[0] == "tool_failed" for e in events)


def test_activity_summary_generation():
    tracker = ActivityTracker("t", "c")
    a1 = tracker.start_tool("Reading document outline", "outline", {"total_pages": 18})
    tracker.complete_tool(a1)
    a2 = tracker.start_tool("Searching for welding", "search")
    tracker.complete_tool(a2)
    a3 = tracker.start_tool("Generating report", "report")
    tracker.complete_tool(a3)

    summary = generate_activity_summary(tracker.activities)
    assert "Read document outline" in summary
    assert "Read 18 pages" in summary
    assert "Searched 1 passage" in summary


def test_chat_sse_emits_structured_activity_events(client, auth_headers):
    # Upload document
    pdf_bytes = _create_test_pdf()
    up_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(pdf_bytes), "sample_doc.pdf")},
        content_type="multipart/form-data"
    )
    doc_id = up_res.get_json()["id"]

    # Stream query
    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "What is in this PDF?",
        "attachment_ids": [doc_id],
    })
    assert res.status_code == 200

    raw_text = res.data.decode("utf-8")
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
    # Verify Claude-style events emitted
    assert "task_started" in event_names
    assert "tool_started" in event_names
    assert "tool_completed" in event_names
    assert "answer_delta" in event_names
    assert "task_completed" in event_names
    assert "done" in event_names

    # Check task_completed data has genuine activities
    task_done = next(e[1] for e in events if e[0] == "task_completed")
    assert len(task_done.get("activities", [])) >= 1
    assert task_done["activities"][0]["status"] == "completed"
    assert "activity_summary" in task_done


def test_activities_persisted_in_database(client, auth_headers):
    # Send request with conversation_id
    conv_id = "test_conv_persistence"
    res = client.post("/api/chat", headers=auth_headers, json={
        "conversation_id": conv_id,
        "message": "List the images",
    })
    assert res.status_code == 200
    # Consume the SSE stream to allow generator to finish and commit assistant reply to DB
    _ = res.data

    # Fetch conversation messages
    msg_res = client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers)
    assert msg_res.status_code == 200
    msgs = msg_res.get_json()
    assert len(msgs) >= 2
    assistant_msg = msgs[1]
    assert "activities" in assistant_msg
    assert isinstance(assistant_msg["activities"], list)
    assert len(assistant_msg["activities"]) >= 1
    assert assistant_msg["activities"][0]["label"] == "Scanning image library"
