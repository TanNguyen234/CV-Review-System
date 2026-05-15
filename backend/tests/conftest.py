"""
Pytest configuration and shared fixtures for CV Review System.
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Ensure backend is importable
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Load env
from dotenv import load_dotenv

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# Import app after loading env vars
from app.main import app  # noqa: E402
from app.core.database import db_manager  # noqa: E402

@pytest.fixture
def client():
    """Provides a TestClient for FastAPI endpoints."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_db():
    """Mocks MongoDB database operations using AsyncMock."""
    mock_db_instance = MagicMock()
    mock_collection = AsyncMock()
    
    # Setup mock collection methods
    mock_collection.insert_one.return_value = MagicMock(inserted_id="mock_id")
    mock_collection.update_one.return_value = MagicMock(modified_count=1)
    mock_collection.find_one.return_value = {"job_id": "mock_job_id", "report_html": "<h1>Mock Report</h1>"}
    
    # Make db["collection_name"] return the mock_collection
    mock_db_instance.__getitem__.return_value = mock_collection
    
    original_db = db_manager.db
    db_manager.db = mock_db_instance
    yield mock_db_instance
    db_manager.db = original_db

@pytest.fixture
def sample_pdf(tmp_path):
    """Creates a temporary sample PDF file for upload tests."""
    pdf_path = tmp_path / "sample_cv.pdf"
    # Write a dummy PDF content (doesn't need to be perfectly valid for basic API tests, 
    # but needs to bypass simple extension checks)
    pdf_path.write_bytes(b"%PDF-1.4\n%Dummy PDF content\n%%EOF")
    return pdf_path

@pytest.fixture
def mock_cv_graph():
    """Mocks the langgraph cv_graph execution."""
    with patch("app.api.v1.jobs.cv_graph") as mock_graph:
        
        # Mock .invoke() for legacy endpoint
        mock_graph.invoke.return_value = {
            "scores": {"META": {"final_score": 85}},
            "text_insights": {"insight": "Good CV"},
            "report_html": "<h1>Mock Report</h1>",
            "chatbot_summary": "Summary",
            "jd_analysis": None,
            "validation_result": None,
            "confidence_scores": {},
            "processing_metadata": {"correlation_id": "test", "pipeline_version": "2.0.0"},
            "errors": []
        }
        
        # Mock .astream() for SSE endpoint
        async def mock_astream(*args, **kwargs):
            yield {"extractor": {"status": "extracted"}}
            yield {"evaluator": {"status": "evaluated"}}
            yield {"output_generator": {
                "report_html": "<h1>Mock Report</h1>",
                "scores": {"META": {"final_score": 85}}
            }}
            
        mock_graph.astream = mock_astream
        
        # Also need to patch in main.py
        with patch("app.main.cv_graph", mock_graph):
            yield mock_graph

@pytest.fixture
def mock_spam_validator():
    """Mocks validate_cv_spam to always return true for tests unless configured otherwise."""
    with patch("app.api.v1.jobs.validate_cv_spam", new_callable=AsyncMock) as mock_validator:
        mock_validator.return_value = (True, "Valid")
        yield mock_validator
