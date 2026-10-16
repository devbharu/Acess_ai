import io

def test_upload_text_document(client, auth_headers):
    doc_content = b"Invoice #INV-2026-90\nTotal Amount Due: $1,250.00\nDue Date: November 15, 2026\nVendor: AcquiCorp Accessibility Solutions"
    data = {
        "file": (io.BytesIO(doc_content), "invoice.txt"),
    }
    res = client.post("/api/documents", headers=auth_headers, data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["name"] == "invoice.txt"
    assert json_data["kind"] == "document"
    assert json_data["pages"] >= 1
    assert json_data["chars"] > 50
    assert "ocr_used" in json_data

def test_upload_missing_file(client, auth_headers):
    res = client.post("/api/documents", headers=auth_headers, data={}, content_type="multipart/form-data")
    assert res.status_code == 400
