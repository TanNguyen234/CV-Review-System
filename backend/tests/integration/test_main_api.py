import pytest

def test_root_endpoint(client):
    """Test the root endpoint / returns 200 and expected schema."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "features" in data
    assert "CV AI Evaluation System API is running" in data["message"]

def test_health_check(client):
    """Test the /health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_web_app_endpoint(client):
    """Test the /app endpoint returns 200 HTML."""
    response = client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.usefixtures("mock_db", "mock_cv_graph", "mock_spam_validator")
def test_evaluate_endpoint_success(client, sample_pdf):
    """Test the legacy /evaluate endpoint with valid PDF."""
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/evaluate",
            files={"cv_file": ("sample_cv.pdf", f, "application/pdf")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "correlation_id" in data
    assert "data" in data
    assert "scores" in data["data"]
    assert "report" in data["data"]

def test_evaluate_endpoint_invalid_extension(client, tmp_path):
    """Test /evaluate with non-pdf extension."""
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello")
    
    with open(txt_file, "rb") as f:
        response = client.post(
            "/evaluate",
            files={"cv_file": ("sample.txt", f, "text/plain")}
        )
    
    assert response.status_code == 400
    assert "Only PDF files are accepted" in response.json()["detail"]

def test_evaluate_endpoint_missing_file(client):
    """Test /evaluate without file returns 422 Validation Error."""
    response = client.post("/evaluate")
    assert response.status_code == 422
