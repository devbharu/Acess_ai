import io
import json
import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


def _create_test_png() -> bytes:
    im = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _create_test_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    topics = [
        "Hydropower and Turbines",
        "CNC Lathe and Bed Mechanics",
        "3D Printing Workflow and Additive Manufacturing",
        "Innovative Welding Technologies (MIAB, Friction, Ultrasonic)",
        "Robotics, Isaac Asimov Laws and Machine Learning",
        "Solar Photovoltaics and Net Metering",
        "Thermodynamics and Entropy Principles"
    ]
    for t in topics:
        story.append(Paragraph(t, styles["Heading1"]))
        story.append(Paragraph(f"Detailed technical discussion, diagrams, and operational formulas for {t}.", styles["Normal"]))
        story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


@pytest.fixture
def sample_media(client, auth_headers):
    """Creates a sample document and image for benchmark tests."""
    png_bytes = _create_test_png()
    img_res = client.post(
        "/api/images",
        headers=auth_headers,
        data={"file": (io.BytesIO(png_bytes), "sample_robot_diagram.png")},
        content_type="multipart/form-data"
    )
    img_id = img_res.get_json()["id"]

    pdf_bytes = _create_test_pdf()
    doc_res = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(pdf_bytes), "mechanical_presentation.pdf")},
        content_type="multipart/form-data"
    )
    doc_id = doc_res.get_json()["id"]

    return {"img_id": img_id, "doc_id": doc_id}


# =====================================================================
# Scenario 1: List Available Images
# =====================================================================
def test_scenario_1_list_images(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "List the images",
        "conversation_id": "current_conversation",
        "attachments": []
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "list_images"
    assert "Found" in data["answer"]
    assert len(data["media"]) >= 1
    assert data["media"][0]["file_id"] == sample_media["img_id"]
    assert data["media"][0]["filename"] == "sample_robot_diagram.png"
    assert data["sources"] == []
    assert data["limitations"] == []


# =====================================================================
# Scenario 2: Summarize a PDF
# =====================================================================
def test_scenario_2_summarize_pdf(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "What is there in the PDF?",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "summarize_document"
    assert len(data["sections"]) >= 1
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["file_id"] == sample_media["doc_id"]
    assert "mechanical_presentation.pdf" in data["sources"][0]["filename"]
    assert data["limitations"] == []


# =====================================================================
# Scenario 3: Explain Every Topic in a PDF
# =====================================================================
def test_scenario_3_explain_document_topics(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain the PDF, each and every topic",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "explain_document_topics"
    assert len(data["topics"]) >= 1
    assert data["topics"][0]["completion_status"] == "completed"
    assert data["progress"]["completed_sections"] >= 1
    assert data["progress"]["remaining_sections"] == 0
    assert data["limitations"] == []


# =====================================================================
# Scenario 4: Explain a Specific Topic
# =====================================================================
def test_scenario_4_explain_specific_topic(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain thermodynamics in simple words",
        "conversation_id": "current_conversation",
        "attachments": []
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "explain_topic"
    assert len(data["key_points"]) >= 3
    assert any("definition" in kp.lower() for kp in data["key_points"])
    assert any("principle" in kp.lower() for kp in data["key_points"])
    assert any("example" in kp.lower() for kp in data["key_points"])


# =====================================================================
# Scenario 5: Explain Second Topic (Contextual Reference)
# =====================================================================
def test_scenario_5_explain_second_topic_context(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain the second topic",
        "conversation_id": "current_conversation",
        "attachments": [],
        "context": {
            "previous_intent": "summarize_document",
            "previous_result": "Outline with multiple headings",
            "active_file_id": sample_media["doc_id"]
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "explain_topic"
    assert data["resolved_reference"]["type"] == "document_section"
    assert data["resolved_reference"]["file_id"] == sample_media["doc_id"]
    assert "CNC" in data["resolved_reference"]["title"] or "Topic 2" in data["resolved_reference"]["title"]


# =====================================================================
# Scenario 6: Describe an Image
# =====================================================================
def test_scenario_6_describe_image(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Describe this image",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["img_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "describe_image"
    assert len(data["media"]) >= 1
    assert data["media"][0]["file_id"] == sample_media["img_id"]
    assert "description" in data["media"][0]


# =====================================================================
# Scenario 7: Explain a Diagram in a PDF
# =====================================================================
def test_scenario_7_explain_diagram_in_pdf(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain the diagram on page 7",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "analyze_diagram"
    assert len(data["visual_elements"]) >= 1
    assert data["sources"][0]["page"] == 7


# =====================================================================
# Scenario 8: Extract Text from an Image
# =====================================================================
def test_scenario_8_extract_image_text(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Read all the text in this screenshot",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["img_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "extract_image_text"
    assert "extracted_text" in data
    assert data["media"][0]["file_id"] == sample_media["img_id"]


# =====================================================================
# Scenario 9: Answer a Question About an Image
# =====================================================================
def test_scenario_9_answer_question_about_image(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "What is the person doing in this image?",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["img_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "ask_image"
    assert "answer" in data and len(data["answer"]) > 10


# =====================================================================
# Scenario 10: Understand a Chart
# =====================================================================
def test_scenario_10_understand_chart(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain this graph and its trend",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["img_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "analyze_chart"
    assert "trend" in data and len(data["trend"]) > 5
    assert isinstance(data["data_points"], list)


# =====================================================================
# Scenario 11: Find an Answer in a Document
# =====================================================================
def test_scenario_11_find_in_document(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "On which page is the definition of entropy?",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "find_in_document"
    assert len(data["matches"]) >= 1
    assert "page" in data["matches"][0]


# =====================================================================
# Scenario 12: Compare Two PDFs
# =====================================================================
def test_scenario_12_compare_two_pdfs(client, auth_headers, sample_media):
    doc_bytes_2 = _create_test_pdf()
    doc_res_2 = client.post(
        "/api/documents",
        headers=auth_headers,
        data={"file": (io.BytesIO(doc_bytes_2), "renewable_systems.pdf")},
        content_type="multipart/form-data"
    )
    doc_id_2 = doc_res_2.get_json()["id"]

    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Compare these two PDFs",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"], doc_id_2]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "compare_documents"
    assert len(data["similarities"]) >= 1
    assert len(data["differences"]) >= 1


# =====================================================================
# Scenario 13: Continue Previous Explanation
# =====================================================================
def test_scenario_13_continue_previous_task(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Continue",
        "conversation_id": "current_conversation",
        "attachments": [],
        "context": {
            "previous_task": "Explain every topic in a PDF",
            "completed_sections": ["Actual completed section"],
            "remaining_sections": ["Actual pending section"]
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "continue_task"
    assert data["progress"]["completed_sections"] == 2
    assert data["progress"]["remaining_sections"] == 0


# =====================================================================
# Scenario 14: Read the Previous Answer Aloud
# =====================================================================
def test_scenario_14_read_previous_answer_aloud(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Read that aloud",
        "conversation_id": "current_conversation",
        "attachments": [],
        "context": {
            "previous_answer": "This is the previously generated engineering response."
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "read_aloud"
    assert data["audio"]["available"] is True
    assert data["audio"]["audio_url"].startswith("/api/audio/")


# =====================================================================
# Scenario 15: Transcribe Voice Input
# =====================================================================
def test_scenario_15_transcribe_voice_input(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": None,
        "conversation_id": "current_conversation",
        "audio_attachment": "actual_audio_id"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "speech_input"
    assert "transcript" in data and len(data["transcript"]) > 0
    assert data["next_action"] == "Process transcript through the regular orchestrator"


# =====================================================================
# Scenario 16: Generate a PDF Report
# =====================================================================
def test_scenario_16_generate_pdf_report(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Create a downloadable report summarizing this PDF",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "generate_report"
    assert data["report"]["filename"].endswith(".pdf")
    assert "/api/artifacts/" in data["report"]["download_url"]


# =====================================================================
# Scenario 17: Ask a Question with No Uploaded Document
# =====================================================================
def test_scenario_17_no_uploaded_document(client, auth_headers):
    # Empty new conversation with no documents
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain the second chapter of the PDF",
        "conversation_id": "new_isolated_conversation_no_doc",
        "attachments": []
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "needs_clarification"
    assert data["intent"] == "ask_document"
    assert "Please attach the PDF" in data["answer"]
    assert any("No relevant PDF was found" in lim for lim in data["limitations"])


# =====================================================================
# Scenario 18: Handle Multiple Possible PDFs
# =====================================================================
def test_scenario_18_multiple_possible_pdfs(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Summarize the PDF",
        "conversation_id": "current_conversation",
        "attachments": [],
        "context": {
            "available_documents": [
                {"file_id": "actual_pdf_id_1", "filename": "actual_document_1.pdf"},
                {"file_id": "actual_pdf_id_2", "filename": "actual_document_2.pdf"}
            ],
            "active_document": None
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "needs_clarification"
    assert data["intent"] == "summarize_document"
    assert "Which PDF would you like me to summarize?" in data["answer"]
    assert len(data["options"]) == 2
    assert data["options"][0]["filename"] == "actual_document_1.pdf"
    assert data["options"][1]["filename"] == "actual_document_2.pdf"


# =====================================================================
# Scenario 19: Recover from Extraction or Model Failure
# =====================================================================
def test_scenario_19_recovery_from_extraction_failure(client, auth_headers):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain this PDF",
        "conversation_id": "current_conversation",
        "attachments": ["corrupted_error_pdf_id"],
        "context": {
            "extraction_error": True
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "error"
    assert data["intent"] == "ask_document"
    assert "could not extract readable content" in data["answer"].lower()
    assert any("Actual extraction error" in lim for lim in data["limitations"])


# =====================================================================
# Scenario 20: Multimodal Question Combining PDF and Image
# =====================================================================
def test_scenario_20_multimodal_pdf_and_image(client, auth_headers, sample_media):
    res = client.post("/api/agent/scenario", headers=auth_headers, json={
        "message": "Explain this diagram using the PDF and tell me what each component does",
        "conversation_id": "current_conversation",
        "attachments": [sample_media["doc_id"], sample_media["img_id"]]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "multimodal_document_image_analysis"
    assert len(data["components"]) >= 1
    assert data["components"][0]["verification_status"] == "verified"
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["file_id"] == sample_media["doc_id"]
    assert len(data["media"]) >= 1
    assert data["media"][0]["file_id"] == sample_media["img_id"]
