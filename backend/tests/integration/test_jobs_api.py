import pytest
import json
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_rate_limiter():
    """Mocks check_rate_limit to pass by default."""
    with patch("app.api.v1.jobs.check_rate_limit", new_callable=AsyncMock) as mock_limit:
        yield mock_limit

@pytest.mark.usefixtures("mock_db", "mock_cv_graph", "mock_spam_validator", "mock_rate_limiter")
def test_submit_job_success(client, sample_pdf):
    """Test successful job submission returns job_id."""
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/api/v1/jobs/submit",
            files={"cv_file": ("test_cv.pdf", f, "application/pdf")},
            data={"jd_text": "Software Engineer"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "message" in data

@pytest.mark.usefixtures("mock_rate_limiter")
def test_submit_job_invalid_extension(client, tmp_path):
    """Test submit rejects non-PDF files."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("dummy")
    
    with open(txt_file, "rb") as f:
        response = client.post(
            "/api/v1/jobs/submit",
            files={"cv_file": ("test.txt", f, "text/plain")}
        )
    
    assert response.status_code == 400
    assert "Only PDF files are accepted" in response.json()["detail"]

@pytest.mark.usefixtures("mock_db", "mock_cv_graph", "mock_rate_limiter")
def test_submit_job_spam_detected(client, sample_pdf):
    """Test submit rejects spam CVs."""
    with patch("app.api.v1.jobs.validate_cv_spam", new_callable=AsyncMock) as mock_spam:
        mock_spam.return_value = (False, "Contains suspicious keywords")
        
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/jobs/submit",
                files={"cv_file": ("test_cv.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 400
        assert "Contains suspicious keywords" in response.json()["detail"]

@pytest.mark.usefixtures("mock_db", "mock_cv_graph", "mock_spam_validator", "mock_rate_limiter")
def test_stream_job(client, sample_pdf):
    """Test SSE stream for a valid job."""
    # First submit to get a job_id
    with open(sample_pdf, "rb") as f:
        submit_response = client.post(
            "/api/v1/jobs/submit",
            files={"cv_file": ("test_cv.pdf", f, "application/pdf")}
        )
    
    job_id = submit_response.json()["job_id"]
    
    # Now stream
    with client.stream("GET", f"/api/v1/jobs/stream/{job_id}") as response:
        assert response.status_code == 200
        content = response.read().decode("utf-8")
        # SSE format checks
        assert "event: status\r\ndata: Initializing pipeline...\r\n\r\n" in content
        assert "event: status\r\ndata: Finished: extractor\r\n\r\n" in content
        assert "event: complete" in content
        
        # Verify JSON payload in complete event
        import re
        match = re.search(r'event: complete\r\ndata: ({.*?})\r\n\r\n', content)
        assert match is not None
        data = json.loads(match.group(1))
        assert "report_html" in data
        assert data["report_html"] == "<h1>Mock Report</h1>"

def test_stream_job_not_found(client):
    """Test stream returns 404 for unknown job_id."""
    response = client.get("/api/v1/jobs/stream/unknown_id")
    assert response.status_code == 404

@pytest.mark.usefixtures("mock_db")
def test_download_report_success(client):
    """Test downloading a completed report."""
    # mock_db already returns a mock document with report_html="<h1>Mock Report</h1>"
    response = client.get("/api/v1/jobs/download/mock_job_id")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<h1>Mock Report</h1>" in response.text
    assert "window.print()" in response.text

@pytest.mark.usefixtures("mock_db")
def test_download_report_not_found(client):
    """Test downloading report fails if not found in DB."""
    with patch("app.core.database.db_manager.db") as mock_db_instance:
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_db_instance.__getitem__.return_value = mock_col
        
        # Replace the fixture's effect temporarily
        original_db = client.app.state # not exactly right, but we patched db_manager.db
        # We can just override db_manager.db inside the test
        from app.core.database import db_manager
        db_manager.db = mock_db_instance
        
        response = client.get("/api/v1/jobs/download/unknown_id")
        assert response.status_code == 404
