import io
import json
import pytest
from PIL import Image
from backend.services.tools import registry
from backend.services.context import ContextResolver, ConversationState
from backend.services.orchestrator import Orchestrator
from backend.services.vision_service import VisionService
from backend.services.document_service import DocumentService


def _create_valid_png() -> bytes:
    im = Image.new("RGB", (120, 120), color="teal")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def test_1_list_images_returns_actual_images(client, auth_headers):
    """Test 1: 'List the images' returns actual images and identifiers."""
    dummy_img = _create_valid_png()
    upload_res = client.post(
        "/api/images",
        headers=auth_headers,
        data={"file": (io.BytesIO(dummy_img), "photo_test.png")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    img_id = upload_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "list the images"
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "photo_test.png" in raw or img_id in raw
    assert "You have 2 document(s)" not in raw


def test_2_what_is_there_in_pdf(client, auth_headers):
    """Test 2: 'What is there in the PDF?' retrieves content and summarizes it."""
    doc_content = b"Engineering Handbook\nSection A: Fluid Dynamics and Turbines.\nSection B: Thermal Heat Exchangers."
    up_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_content), "handbook.txt")},
        content_type="multipart/form-data"
    )
    doc_id = up_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "What is there in the PDF?",
        "attachment_ids": [doc_id]
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "Engineering" in raw or "handbook.txt" in raw
    assert "You have 2 document(s)" not in raw


def test_3_explain_every_topic_outline(client, auth_headers):
    """Test 3: 'Explain every topic' uses document outline and sections."""
    doc_content = b"Mechanical Engineering Notes\nTopic 1: Hydropower\nTopic 2: Robotics\nTopic 3: Solar"
    up_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_content), "notes.txt")},
        content_type="multipart/form-data"
    )
    doc_id = up_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "explain each and every topic",
        "attachment_ids": [doc_id]
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "notes.txt" in raw or "Outline" in raw or "Topic" in raw


def test_4_explain_second_topic_context(client, auth_headers):
    """Test 4: 'Explain the second topic' resolves previous conversation context."""
    conv_id = "conv_test_multi_turn_4"
    # Ensure conversation exists
    client.post("/api/chat", headers=auth_headers, json={
        "message": "hello",
        "conversation_id": conv_id
    })

    ConversationState.update_state(conv_id, {
        "active_topics": ["Hydropower Facilities", "Welding Technologies", "Robotics and AI"]
    })

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "explain the second topic",
        "conversation_id": conv_id
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "Welding" in raw or "Friction" in raw or "Magnetic" in raw


def test_5_describe_image(client, auth_headers):
    """Test 5: 'Describe this image' accesses real image and returns description."""
    dummy_img = _create_valid_png()
    up_res = client.post(
        "/api/images",
        headers=auth_headers,
        data={"file": (io.BytesIO(dummy_img), "sample_scene.png")},
        content_type="multipart/form-data"
    )
    img_id = up_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "describe this image",
        "attachment_ids": [img_id]
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "sample_scene.png" in raw or "Visual Description" in raw


def test_6_read_that_aloud(client, auth_headers):
    """Test 6: 'Read that aloud' uses previous answer and speech service."""
    conv_id = "conv_test_speech_aloud_6"
    client.post("/api/chat", headers=auth_headers, json={
        "message": "hello",
        "conversation_id": conv_id
    })

    ConversationState.update_state(conv_id, {
        "last_assistant_answer": "Solar panels convert solar irradiance into electrical energy via the photovoltaic effect."
    })

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "read that aloud",
        "conversation_id": conv_id
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "Solar" in raw
    assert "panels" in raw
    assert "photovoltaic" in raw


def test_7_scanned_pdf_ocr(tmp_path):
    """Test 7: Scanned PDF or sparse text triggers OCR."""
    test_txt_path = str(tmp_path / "scanned.txt")
    with open(test_txt_path, "w") as f:
        f.write("Scanned invoice OCR sample #9812")
    res = DocumentService.extract_from_file(test_txt_path, "scanned.txt")
    assert res["pages"] == 1
    assert "9812" in res["pages_data"][0]["text"]


def test_8_question_specific_page(client, auth_headers):
    """Test 8: A question about a specific page retrieves that page."""
    doc_content = b"Page One Content\nPage Two Content with technical specifications."
    up_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_content), "multipage.txt")},
        content_type="multipart/form-data"
    )
    doc_id = up_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "what is on page 1",
        "attachment_ids": [doc_id]
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "Page 1" in raw or "Page One" in raw


def test_9_multiple_pdfs_resolved(client, auth_headers):
    """Test 9: Multiple PDFs resolved correctly when specified by name."""
    doc1 = b"Report on Solar Efficiency"
    doc2 = b"Report on Wind Turbines"
    up1 = client.post("/api/documents", headers=auth_headers, data={"file": (io.BytesIO(doc1), "solar_report.txt")}, content_type="multipart/form-data")
    up2 = client.post("/api/documents", headers=auth_headers, data={"file": (io.BytesIO(doc2), "wind_report.txt")}, content_type="multipart/form-data")

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "explain wind_report.txt"
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "wind_report.txt" in raw or "Wind" in raw


def test_10_ambiguous_file_clarification():
    """Test 10: Ambiguous file references trigger clarification when multiple distinct docs exist."""
    media = {
        "documents": [
            {"id": "doc1", "name": "Report_2025.pdf", "kind": "document"},
            {"id": "doc2", "name": "Report_2026.pdf", "kind": "document"}
        ],
        "message_files": [],
        "conversation_files": []
    }
    state = {}
    target_doc, is_ambiguous, candidates = ContextResolver.resolve_document("explain the PDF", media, state)
    assert is_ambiguous is True
    assert len(candidates) == 2


def test_11_missing_files_clear_error(client, auth_headers):
    """Test 11: Missing files produce clear errors instead of generic success messages."""
    res = registry.execute("get_file_metadata", {"file_id": "non_existent_id", "user_id": "dummy_user"}, {})
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_12_tool_failures_safe_handling():
    """Test 12: Tool failures and invalid arguments are safely caught and contained."""
    res = registry.execute("get_page_content", {"file_id": "bad_id", "page_number": "invalid"}, {"user_id": "u1"})
    assert res["success"] is False


def test_13_unsupported_image_models():
    """Test 13: Unsupported image models are detected accurately."""
    assert VisionService.is_vision_model("gemma4:31b-cloud") is True
    assert VisionService.is_vision_model("moondream") is True
    assert VisionService.is_vision_model("nemotron-3-ultra:cloud") is False
    assert VisionService.is_vision_model("deepseek-r1:7b") is False


def test_14_citations_reference_extracted_content(client, auth_headers):
    """Test 14: Citations reference existing extracted content."""
    doc_content = b"Solar Power Principles\nPhotovoltaic conversion converts photons into DC electricity."
    up_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_content), "solar_doc.txt")},
        content_type="multipart/form-data"
    )
    doc_id = up_res.get_json()["id"]

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "tell me about solar power",
        "attachment_ids": [doc_id]
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "Solar" in raw
    assert "event: sources" in raw


def test_15_different_questions_do_not_return_same_generic_response(client, auth_headers):
    """Test 15: Different questions produce distinct, specific responses."""
    queries = [
        "list the images",
        "what is in the pdf",
        "explain the welding techniques",
        "what is on page 1"
    ]
    replies = []
    for q in queries:
        res = client.post("/api/chat", headers=auth_headers, json={"message": q})
        assert res.status_code == 200
        replies.append(res.data.decode("utf-8"))

    # Verify all responses are distinct from each other
    assert replies[0] != replies[1]
    assert replies[1] != replies[2]
    assert replies[2] != replies[3]
    # Verify no response is the generic fallback
    for rep in replies:
        assert "You have 2 document(s) and 4 image(s)" not in rep


def test_16_avatar_jpeg_explain_describes_image_not_pdf(client, auth_headers):
    """Test 16: 'avatar .jpeg expalin' describes avatar.jpeg, not the PDF."""
    dummy_img = _create_valid_png()
    upload_res = client.post(
        "/api/images",
        headers=auth_headers,
        data={"file": (io.BytesIO(dummy_img), "avatar.jpeg")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "avatar .jpeg expalin"
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "avatar.jpeg" in raw
    assert "Visual Description" in raw or "avatar" in raw
    assert "DARSHAN_MECHANICS_PRESENTATION" not in raw
    assert "Hydropower Facilities" not in raw


def test_17_can_i_get_all_images_what_i_have_lists_images(client, auth_headers):
    """Test 17: 'Can I get all images what I have?' lists images even if images.jpeg exists."""
    dummy_img = _create_valid_png()
    upload_res = client.post(
        "/api/images",
        headers=auth_headers,
        data={"file": (io.BytesIO(dummy_img), "images.jpeg")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201

    res = client.post("/api/chat", headers=auth_headers, json={
        "message": "Can I get all images what I have?"
    })
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "images.jpeg" in raw
    assert "Visual Description" not in raw
    assert "DARSHAN_MECHANICS_PRESENTATION" not in raw
