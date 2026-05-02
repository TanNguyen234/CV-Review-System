from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import shutil
import uuid

from app.services.ai.graph import cv_graph
from app.services.ai.state import AgentState

app = FastAPI(title="CV AI Evaluation System", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "CV AI Evaluation System API is running"}

@app.post("/evaluate")
async def evaluate_cv(
    cv_file: UploadFile = File(...),
    jd_text: Optional[str] = None
):
    # Create temp file
    temp_id = str(uuid.uuid4())
    temp_dir = os.path.join("data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    file_path = os.path.join(temp_dir, f"{temp_id}_{cv_file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(cv_file.file, buffer)
        
    try:
        # Initial State
        initial_state: AgentState = {
            "messages": [],
            "raw_text": file_path,
            "cleaned_text": "",
            "sections": {},
            "text_insights": {},
            "scores": {},
            "report_html": "",
            "chatbot_summary": "",
            "errors": []
        }
        
        # Run Graph
        result = cv_graph.invoke(initial_state)
        
        return {
            "success": len(result.get("errors", [])) == 0,
            "data": {
                "scores": result.get("scores"),
                "insights": result.get("text_insights"),
                "report": result.get("report_html"),
                "summary": result.get("chatbot_summary")
            },
            "errors": result.get("errors")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
