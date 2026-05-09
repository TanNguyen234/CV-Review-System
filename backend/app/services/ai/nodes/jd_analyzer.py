"""
JD Analyzer Node — Matches CV against Job Description.
Performs skill gap analysis and role alignment scoring.
"""

import time
from typing import List

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import (
    get_llm,
    invoke_structured,
    LLMTransientError,
    LLMPermanentError,
)
from app.services.ai.prompts.evaluator_prompts import JD_ANALYSIS_PROMPT
from app.core.logging_config import pipeline_logger


class InterviewQuestionModel(BaseModel):
    question: str = Field(description="Câu hỏi phỏng vấn")
    intent: str = Field(description="Mục đích hỏi câu này")
    expected_answer: str = Field(description="Gợi ý cách trả lời hoặc từ khóa cần có")


class JDAnalysisResult(BaseModel):
    """Schema for JD matching results."""

    match_score: int = Field(
        description="0-100 overall match score", ge=0, le=100
    )
    matched_skills: List[str] = Field(
        description="Skills from CV that match JD requirements"
    )
    missing_skills: List[str] = Field(
        description="Skills JD requires but CV lacks"
    )
    bonus_skills: List[str] = Field(
        description="Extra skills in CV not required by JD"
    )
    role_alignment: str = Field(
        description="Assessment of role fit"
    )
    experience_gap: str = Field(
        description="Assessment of experience gap"
    )
    recommendation: str = Field(
        description="Final recommendation: Rất phù hợp / Phù hợp / Cần cải thiện / Không phù hợp"
    )
    interview_questions: List[InterviewQuestionModel] = Field(
        description="Tailored interview questions based on skill gaps"
    )


def jd_analyzer_node(state: AgentState) -> dict:
    """
    Analyzes the match between CV and Job Description.
    Only runs when JD text is provided.
    """
    start = time.time()
    pipeline_logger.node_start("jd_analyzer")

    jd_text = state.get("jd_text", "")

    # Skip if no JD provided
    if not jd_text or not jd_text.strip():
        pipeline_logger.node_complete("jd_analyzer", duration_ms=0)
        return {
            "jd_analysis": None,
            "processing_metadata": {"jd_analyzer_skipped": True},
            "errors": [],
        }

    cleaned_text = state.get("cleaned_text", "")
    sections = state.get("sections", {})

    # Build comprehensive CV context
    cv_context = cleaned_text
    if sections:
        cv_context = "\n\n".join(
            [f"[{k}]: {v}" for k, v in sections.items()]
        )

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content=JD_ANALYSIS_PROMPT),
            HumanMessage(
                content=(
                    f"=== JOB DESCRIPTION ===\n{jd_text}\n\n"
                    f"=== CV CỦA ỨNG VIÊN ===\n{cv_context}"
                )
            ),
        ]

        result = invoke_structured(
            llm, JDAnalysisResult, messages, node_name="jd_analyzer"
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "jd_analyzer",
            duration_ms=duration_ms,
            score=result.match_score,
        )

        return {
            "jd_analysis": {
                "match_score": result.match_score,
                "matched_skills": result.matched_skills,
                "missing_skills": result.missing_skills,
                "bonus_skills": result.bonus_skills,
                "role_alignment": result.role_alignment,
                "experience_gap": result.experience_gap,
                "recommendation": result.recommendation,
                "interview_questions": [q.model_dump() for q in result.interview_questions]
            },
            "processing_metadata": {
                "jd_analyzer_duration_ms": round(duration_ms, 2)
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error("jd_analyzer", str(e), retryable=False)
        return {
            "jd_analysis": None,
            "errors": [f"JD Analyzer error: {str(e)}"],
        }
