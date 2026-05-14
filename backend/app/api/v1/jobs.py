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
import logging

logger = logging.getLogger(__name__)

# Basic in-memory store for jobs
jobs_store = {}

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
    try:
        client_ip = request.client.host
        logger.info(f"Received job submission from {client_ip}")
        
        # 1. Anti-bot Rate Limiter (5 per day)
        try:
            await check_rate_limit(client_ip, max_requests=5)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
        
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
        try:
            is_cv, reason = await validate_cv_spam(file_path)
            if not is_cv:
                # Store spam record in DB
                try:
                    from app.core.database import db_manager
                    from app.schemas.db import CVRecord
                    if db_manager.db is not None:
                        spam_record = CVRecord(
                            job_id=job_id,
                            filename=cv_file.filename,
                            status="spam",
                            is_valid_cv=False,
                            spam_reason=reason
                        )
                        await db_manager.db["cv_records"].insert_one(spam_record.model_dump())
                except Exception as db_e:
                    logger.error(f"Failed to store spam record: {db_e}")

                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=400, detail=f"File rejected: {reason}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Spam validation failed: {e}")
            
        # 5. Extract PDF Base64
        import base64
        pdf_data = None
        try:
            with open(file_path, "rb") as f:
                pdf_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read PDF for base64 encoding: {e}")
            
        # 6. Store in DB
        try:
            from app.core.database import db_manager
            from app.schemas.db import CVRecord
            if db_manager.db is not None:
                # Extract initial raw text from first page for the record
                import pymupdf4llm
                raw_text_preview = ""
                try:
                    raw_text_preview = pymupdf4llm.to_markdown(file_path, pages=[0])
                except Exception:
                    pass
                    
                cv_record = CVRecord(
                    job_id=job_id,
                    filename=cv_file.filename,
                    pdf_data=pdf_data,
                    raw_text=raw_text_preview,
                    jd_text=jd_text,
                    is_valid_cv=True
                )
                await db_manager.db["cv_records"].insert_one(cv_record.model_dump())
        except Exception as e:
            logger.error(f"DB storage failed: {e}")


            
        # Store job info in memory
        jobs_store[job_id] = {
            "file_path": file_path,
            "filename": cv_file.filename,
            "jd_text": jd_text,
            "correlation_id": set_correlation_id()
        }
        
        return {"job_id": job_id, "message": "Job submitted successfully. Connect to stream."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fatal error in submit_job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
                        # Extract final score if available
                        final_score = updates.get("scores", {}).get("META", {}).get("final_score")
                        
                        # We send a special completion event with the HTML
                        final_data = {
                            "report_html": updates["report_html"],
                            "scores": updates.get("scores", {})
                        }
                        
                        # Update DB with results
                        from app.core.database import db_manager
                        if db_manager.db is not None:
                            # Try to get cleaned text from the latest state if possible. 
                            # updates might not contain it, but we'll try. 
                            # Or we can just leave the raw_text as is.
                            await db_manager.db["cv_records"].update_one(
                                {"job_id": job_id},
                                {
                                    "$set": {
                                        "status": "completed", 
                                        "report_html": updates["report_html"],
                                        "final_score": final_score,
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
                        
                        # SSE data must be text, so we JSON serialize
                        yield {"event": "complete", "data": json.dumps(final_data)}
            
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)
                
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield {"event": "error", "data": str(e)}
            if os.path.exists(file_path):
                os.remove(file_path)

    return EventSourceResponse(event_generator())


from fastapi.responses import Response

@router.get("/download/{job_id}")
async def download_report(job_id: str):
    from app.core.database import db_manager
    if db_manager.db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    record = await db_manager.db["cv_records"].find_one({"job_id": job_id})
    if not record or not record.get("report_html"):
        raise HTTPException(status_code=404, detail="Report not found or not ready")
        
    report_html = record["report_html"]
    
    # Wrap in modern template for WeasyPrint
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                margin: 20mm;
                size: A4;
                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-family: 'Inter', sans-serif;
                    font-size: 9pt;
                    color: #64748b;
                }}
                @top-left {{
                    content: "AI CV Analysis Report";
                    font-family: 'Inter', sans-serif;
                    font-size: 9pt;
                    color: #94a3b8;
                }}
            }}
            body {{
                font-family: 'Inter', -apple-system, sans-serif;
                color: #0f172a;
                line-height: 1.6;
                font-size: 11pt;
                background-color: #ffffff;
            }}
            h1, h2, h3, h4 {{
                font-family: 'Outfit', sans-serif;
                color: #1e293b;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }}
            h1 {{
                font-size: 24pt;
                color: #2563eb;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 10px;
                text-align: center;
                margin-top: 0;
            }}
            h2 {{
                font-size: 18pt;
                color: #334155;
                border-bottom: 1px solid #cbd5e1;
                padding-bottom: 5px;
                page-break-after: avoid;
            }}
            .score-badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                background-color: #eff6ff;
                color: #1d4ed8;
                font-weight: 600;
                border: 1px solid #bfdbfe;
                margin-bottom: 15px;
            }}
            .card {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }}
            ul, ol {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .critical-issue {{
                color: #b91c1c;
                background-color: #fef2f2;
                padding: 10px;
                border-left: 4px solid #ef4444;
                margin-bottom: 10px;
            }}
            .recommendation {{
                color: #047857;
                background-color: #ecfdf5;
                padding: 10px;
                border-left: 4px solid #10b981;
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #e2e8f0;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #f1f5f9;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        {report_html}
    </body>
    </html>
    """
    
    # Add auto-print script
    full_html += """
    <script>
        window.onload = function() {
            setTimeout(function() {
                window.print();
            }, 500);
        };
    </script>
    """
    
    return Response(
        content=full_html,
        media_type="text/html"
    )
