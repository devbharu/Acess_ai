import io

def test_tts_generation(client):
    res = client.post("/api/tts", json={
        "text": "The total payment is 450 dollars.",
        "voice": "af_heart",
        "speed": 1.0,
    })
    assert res.status_code == 200
    assert res.content_type == "audio/wav"
    assert len(res.data) > 44  # Valid WAV header + PCM data is > 44 bytes
    assert res.data[:4] == b"RIFF"

def test_tts_empty_text(client):
    res = client.post("/api/tts", json={"text": ""})
    assert res.status_code == 400

def test_stt_transcription(client):
    # Mock / dummy audio file
    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    data = {
        "file": (io.BytesIO(dummy_audio), "audio.wav"),
        "language": "en",
        "model": "tiny",
    }
    res = client.post("/api/stt", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert "text" in res.get_json()
