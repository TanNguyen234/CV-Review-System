import os
import uuid
import time
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from app.services.security import check_rate_limit, validate_cv_spam
from app.services.ai.graph import cv_graph
from app.services.ai.state import AgentState
from app.core.config import settings
from app.core.logging_config import set_correlation_id
import cloudinary
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

# Basic in-memory store for jobs
jobs_store = {}

# Configure Cloudinary
if settings.cloud_name and settings.cloud_key and settings.cloud_secret:
    cloudinary.config(
        cloud_name=settings.cloud_name,
        api_key=settings.cloud_key,
        api_secret=settings.cloud_secret
    )

router = APIRouter()

@router.post("/submit")
async def submit_job(
    request: Request,
    cv_file: UploadFile = File(...),
    jd_text: str = Form(default="")
):
    """
    Step 1: Upload file, run anti-bot, validate spam, and return a job_id.
    """
    client_ip = request.client.host
    
    # 1. Anti-bot Rate Limiter (5 per day)
    await check_rate_limit(client_ip, max_requests=5)
    
    # 2. File Validation
    if not cv_file.filename or not cv_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    # 3. Save Temp File
    job_id = str(uuid.uuid4())
    temp_dir = os.path.join("data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{job_id}.pdf")
    
    with open(file_path, "wb") as buffer:
        content = await cv_file.read()
        buffer.write(content)
        
    # 4. Spam Validation
    is_cv, reason = await validate_cv_spam(file_path)
    if not is_cv:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"File rejected: {reason}")
        
    # 5. Cloudinary Upload (Optional/Async) - We can do this in the background, but let's do it here quickly
    cloudinary_url = None
    try:
        if settings.cloud_name:
            res = cloudinary.uploader.upload(file_path, folder="cv_reviews")
            cloudinary_url = res.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        
    # 6. Store in DB (Simulated here if DB not fully wired, else use CVRecord)
    from app.core.database import db_manager
    from app.schemas.db import CVRecord
    if db_manager.db is not None:
        cv_record = CVRecord(
            job_id=job_id,
            filename=cv_file.filename,
            cloudinary_url=cloudinary_url,
            is_valid_cv=True
        )
        await db_manager.db["cv_records"].insert_one(cv_record.model_dump())
        
    # Store job info in memory
    jobs_store[job_id] = {
        "file_path": file_path,
        "filename": cv_file.filename,
        "jd_text": jd_text,
        "correlation_id": set_correlation_id()
    }
    
    return {"job_id": job_id, "message": "Job submitted successfully. Connect to stream."}

@router.get("/stream/{job_id}")
async def stream_job(job_id: str):
    """
    Step 2: Stream the LangGraph execution using SSE.
    """
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found or already processed.")
        
    job_info = jobs_store.pop(job_id)
    file_path = job_info["file_path"]
    filename = job_info["filename"]
    jd_text = job_info["jd_text"]
    correlation_id = job_info["correlation_id"]
    
    async def event_generator():
        try:
            yield {"event": "status", "data": "Initializing pipeline..."}
            
            initial_state: AgentState = {
                "messages": [],
                "raw_text": file_path,
                "cleaned_text": "",
                "sections": {},
                "text_insights": {},
                "scores": {},
                "confidence_scores": {},
                "jd_text": jd_text,
                "jd_analysis": None,
                "validation_result": None,
                "report_html": "",
                "chatbot_summary": "",
                "processing_metadata": {
                    "correlation_id": correlation_id,
                    "cv_filename": filename,
                    "pipeline_version": "2.0.0",
                },
                "errors": [],
            }
            
            # Use LangGraph stream
            async for s in cv_graph.astream(initial_state, stream_mode="updates"):
                # s is a dict with node_name -> state_updates
                for node_name, updates in s.items():
                    logger.info(f"Completed node: {node_name}")
                    # Send status update
                    yield {"event": "status", "data": f"Finished: {node_name}"}
                    
                    # If output generator is done, we have the final HTML
                    if node_name == "output_generator" and "report_html" in updates:
                        # We send a special completion event with the HTML
                        final_data = {
                            "report_html": updates["report_html"],
                            "scores": updates.get("scores", {})
                        }
                        # SSE data must be text, so we JSON serialize
                        yield {"event": "complete", "data": json.dumps(final_data)}
            
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # Update DB status
            from app.core.database import db_manager
            if db_manager.db is not None:
                await db_manager.db["cv_records"].update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "completed", "updated_at": datetime.utcnow()}}
                )
                
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield {"event": "error", "data": str(e)}
            if os.path.exists(file_path):
                os.remove(file_path)

    return EventSourceResponse(event_generator())
