def test_get_metrics_dashboard(client):
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert "summary" in data
    assert "answer_correctness" in data["summary"]
    assert "wer" in data["summary"]
    assert "ocr_accuracy" in data["summary"]
    assert "history" in data
    assert "robustness" in data
    assert "latency" in data
    assert "runs" in data

def test_run_metrics_all(client):
    res = client.post("/api/metrics/run", json={"suite": "all"})
    assert res.status_code == 200
    run_data = res.get_json()
    assert run_data["suite"] == "all"
    assert "score" in run_data
    assert "duration_s" in run_data
    assert run_data["samples"] > 0

def test_run_metrics_stt(client):
    res = client.post("/api/metrics/run", json={"suite": "stt"})
    assert res.status_code == 200
    run_data = res.get_json()
    assert run_data["suite"] == "stt"
    assert "wer" in run_data["details"]

def test_run_metrics_ocr(client):
    res = client.post("/api/metrics/run", json={"suite": "ocr"})
    assert res.status_code == 200
    run_data = res.get_json()
    assert run_data["suite"] == "ocr"
    assert "ocr_accuracy" in run_data["details"]

def test_run_metrics_qa(client):
    res = client.post("/api/metrics/run", json={"suite": "qa"})
    assert res.status_code == 200
    run_data = res.get_json()
    assert run_data["suite"] == "qa"
    assert "qa_correctness" in run_data["details"]
