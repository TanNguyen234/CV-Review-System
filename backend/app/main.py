"""
FastAPI Entry Point — CV AI Evaluation System API.
Production-hardened with file validation, rate limiting concept, and security.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import shutil
import uuid
import time

from app.services.ai.graph import cv_graph
from app.services.ai.state import AgentState
from app.core.config import settings
from app.core.logging_config import pipeline_logger, set_correlation_id
from app.core.database import db_manager
from app.api.v1.jobs import router as jobs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_manager.connect()
    yield
    # Shutdown
    db_manager.disconnect()

app = FastAPI(
    title="CV AI Evaluation System",
    version="2.0.0",
    description="Multi-agent AI pipeline for comprehensive CV evaluation",
    lifespan=lifespan
)

# CORS Configuration — restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Setup Static and Templates
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include the new Jobs Router for Web App Streaming
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])

@app.get("/app", response_class=HTMLResponse)
async def web_app(request: Request):
    """
    Serve the frontend interface.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/")
async def root():
    return {
        "message": "CV AI Evaluation System API is running",
        "version": "2.0.0",
        "features": [
            "parallel_evaluation",
            "confidence_scoring",
            "jd_matching",
            "cross_phase_validation",
        ],
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/evaluate")
async def evaluate_cv(
    cv_file: UploadFile = File(...),
    jd_text: Optional[str] = Form(default=None),
):
    """
    Evaluate a CV (and optionally match against a Job Description).
    Legacy synchronous endpoint.
    """
    correlation_id = set_correlation_id()

    if not cv_file.filename or not cv_file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    if cv_file.content_type and cv_file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {cv_file.content_type}. Expected application/pdf.",
        )

    temp_id = str(uuid.uuid4())
    temp_dir = os.path.join("data", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    safe_filename = f"{temp_id}.pdf"
    file_path = os.path.join(temp_dir, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            content = await cv_file.read()
            file_size_mb = len(content) / (1024 * 1024)

            if file_size_mb > settings.max_upload_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large ({file_size_mb:.1f}MB). Maximum: {settings.max_upload_size_mb}MB.",
                )

            buffer.write(content)

        pipeline_logger.pipeline_start(
            cv_filename=cv_file.filename or "unknown",
            has_jd=bool(jd_text),
        )

        start_time = time.time()

        initial_state: AgentState = {
            "messages": [],
            "raw_text": file_path,
            "cleaned_text": "",
            "sections": {},
            "text_insights": {},
            "scores": {},
            "confidence_scores": {},
            "jd_text": jd_text or "",
            "jd_analysis": None,
            "validation_result": None,
            "report_html": "",
            "chatbot_summary": "",
            "processing_metadata": {
                "correlation_id": correlation_id,
                "cv_filename": cv_file.filename,
                "pipeline_version": "2.0.0",
            },
            "errors": [],
        }

        result = cv_graph.invoke(initial_state)

        duration = time.time() - start_time
        final_score = (
            result.get("scores", {}).get("META", {}).get("final_score", 0)
        )

        pipeline_logger.pipeline_complete(
            duration_s=duration,
            final_score=final_score,
        )

        return {
            "success": len(result.get("errors", [])) == 0,
            "correlation_id": correlation_id,
            "data": {
                "scores": result.get("scores"),
                "insights": result.get("text_insights"),
                "report": result.get("report_html"),
                "summary": result.get("chatbot_summary"),
                "jd_analysis": result.get("jd_analysis"),
                "validation": result.get("validation_result"),
                "confidence": result.get("confidence_scores"),
            },
            "metadata": {
                "duration_s": round(duration, 2),
                "processing": result.get("processing_metadata"),
            },
            "errors": result.get("errors"),
        }

    except HTTPException:
        raise
    except Exception as e:
        pipeline_logger.node_error("api", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
