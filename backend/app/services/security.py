import os
from datetime import datetime
from fastapi import HTTPException
from app.core.database import db_manager
from app.schemas.db import RateLimitRecord
import pymupdf4llm
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def check_rate_limit(ip_address: str, max_requests: int = 5) -> bool:
    """
    Checks if the IP has exceeded the daily limit.
    Increments the counter if not.
    """
    if db_manager.db is None:
        # DB not connected, maybe in testing
        return True
        
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    collection = db_manager.db["rate_limits"]
    
    record = await collection.find_one({
        "ip_address": ip_address,
        "date_str": date_str
    })
    
    if record:
        if record["request_count"] >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per day."
            )
        # Increment
        await collection.update_one(
            {"_id": record["_id"]},
            {
                "$inc": {"request_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
    else:
        # Create new
        new_record = RateLimitRecord(ip_address=ip_address, date_str=date_str)
        await collection.insert_one(new_record.model_dump())
        
    return True

async def validate_cv_spam(file_path: str) -> tuple[bool, str]:
    """
    Reads the first page of the PDF and uses Gemini Flash to determine if it is a real CV.
    Returns (is_valid, reason).
    """
    try:
        # Extract text from first page only for speed
        md_text = pymupdf4llm.to_markdown(file_path, pages=[0])
        
        llm = ChatGoogleGenerativeAI(
            model=settings.ai_model_flash,
            google_api_key=settings.gemini_api_key,
            temperature=0.0
        )
        
        prompt = PromptTemplate.from_template(
            "You are an AI Security guard for a recruitment system.\n"
            "Your job is to determine if the following text extracted from a PDF looks like a real Resume/Curriculum Vitae (CV) or if it's garbage/spam (e.g. a random document, image text, essay, blank).\n\n"
            "Respond in the following format exactly:\n"
            "IS_CV: YES or NO\n"
            "REASON: a short 1-sentence reason.\n\n"
            "Document Text:\n"
            "{text}"
        )
        
        chain = prompt | llm
        result = await chain.ainvoke({"text": md_text[:2000]})  # Send up to 2000 chars
        content = result.content.strip()
        
        is_cv = "IS_CV: YES" in content.upper()
        reason = content.split("REASON:")[-1].strip() if "REASON:" in content else "Unknown"
        
        if not is_cv:
            logger.warning(f"Spam detected: {reason}")
            
        return is_cv, reason
        
    except Exception as e:
        logger.error(f"Error validating CV: {e}")
        # Fail open if error occurs
        return True, ""
