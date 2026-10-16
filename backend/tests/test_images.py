import io
from PIL import Image

def test_upload_image(client, auth_headers):
    # Create a small valid test PNG image
    img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    data = {
        "file": (buf, "receipt.png"),
    }
    res = client.post("/api/images", headers=auth_headers, data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["name"] == "receipt.png"
    assert json_data["kind"] == "image"
    assert "id" in json_data


def test_multimodal_vision_model_detection():
    from backend.services.vision_service import VisionService

    assert VisionService.is_vision_model("gemma4:31b-cloud") is True
    assert VisionService.is_vision_model("gemma4-31b-cloud") is True
    assert VisionService.is_vision_model("gemma") is True
    assert VisionService.is_vision_model("llama3.2-vision") is True
    assert VisionService.is_vision_model("llava") is True
    assert VisionService.is_vision_model("nemotron-3-ultra:cloud") is False
    assert VisionService.is_vision_model("gpt-oss:20b-cloud") is False


def test_multimodal_chat_image_passing(client, auth_headers):
    # Upload an image
    img = Image.new("RGB", (64, 64), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    up_res = client.post("/api/images", headers=auth_headers, data={"file": (buf, "logo_banner.png")}, content_type="multipart/form-data")
    img_id = up_res.get_json()["id"]

    # Chat asking about the image using multimodal Gemma model
    payload = {
        "message": "what is this image about",
        "attachment_ids": [img_id],
    }
    res = client.post("/api/chat", headers=auth_headers, json=payload)
    assert res.status_code == 200
    raw = res.data.decode("utf-8")
    assert "logo_banner.png" in raw or "Visual Description" in raw or "image" in raw
