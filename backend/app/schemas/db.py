from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class RateLimitRecord(BaseModel):
    ip_address: str
    date_str: str  # Format: YYYY-MM-DD
    request_count: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CVRecord(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    pdf_data: Optional[str] = None # Base64 encoded PDF
    raw_text: Optional[str] = None # Extracted text
    status: str = "processing"  # processing, completed, failed, spam
    is_valid_cv: bool = True
    spam_reason: Optional[str] = None
    jd_text: Optional[str] = None
    report_html: Optional[str] = None
    final_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
