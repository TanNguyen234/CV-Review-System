"""
Soft Skills Evaluator Node — Analyzes soft skills from CV context.
Extracts evidence for communication, problem-solving, teamwork, etc.
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
from app.services.ai.prompts.evaluator_prompts import SOFT_SKILLS_PROMPT
from app.core.logging_config import pipeline_logger


class SoftSkillModel(BaseModel):
    skill_name: str = Field(description="Tên kỹ năng mềm")
    evidence: str = Field(description="Bằng chứng từ CV")
    strength_level: str = Field(description="Mức độ (Cao, Trung bình, Thấp, Chưa rõ)")


class SoftSkillsResult(BaseModel):
    skills: List[SoftSkillModel] = Field(description="Danh sách kỹ năng mềm")
    culture_fit_prediction: str = Field(description="Dự đoán môi trường làm việc")


def soft_skills_evaluator_node(state: AgentState) -> dict:
    """
    Evaluates soft skills based on CV context (action verbs, impact).
    """
    start = time.time()
    pipeline_logger.node_start("soft_skills_evaluator")

    cleaned_text = state.get("cleaned_text", "")
    sections = state.get("sections", {})

    # Soft skills are best extracted from Experience, Projects, and Summary
    context_parts = []
    if "SUMMARY" in sections:
        context_parts.append(f"[SUMMARY]:\n{sections['SUMMARY']}")
    if "EXPERIENCE" in sections:
        context_parts.append(f"[EXPERIENCE]:\n{sections['EXPERIENCE']}")
    if "WORK EXPERIENCE" in sections:
        context_parts.append(f"[WORK EXPERIENCE]:\n{sections['WORK EXPERIENCE']}")
    if "PROJECTS" in sections:
        context_parts.append(f"[PROJECTS]:\n{sections['PROJECTS']}")

    eval_context = "\n\n".join(context_parts) if context_parts else cleaned_text

    if not eval_context.strip():
        pipeline_logger.node_error(
            "soft_skills_evaluator", "No CV text available for soft skills analysis."
        )
        return _build_fallback_result("Không có dữ liệu CV để phân tích.")

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content=SOFT_SKILLS_PROMPT),
            HumanMessage(
                content=f"Dữ liệu CV để phân tích Kỹ năng mềm:\n{eval_context}"
            ),
        ]

        result = invoke_structured(
            llm,
            SoftSkillsResult,
            messages,
            node_name="soft_skills_evaluator",
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "soft_skills_evaluator",
            duration_ms=duration_ms,
        )

        return {
            "scores": {
                "SOFT_SKILLS_EVAL": result.model_dump()
            },
            "processing_metadata": {
                "soft_skills_evaluator_duration_ms": round(duration_ms, 2),
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error(
            "soft_skills_evaluator", str(e), retryable=False
        )
        return _build_fallback_result(f"Lỗi phân tích Kỹ năng mềm: {str(e)}")


def _build_fallback_result(error_msg: str) -> dict:
    """Builds a safe fallback result when LLM fails."""
    return {
        "scores": {
            "SOFT_SKILLS_EVAL": {
                "skills": [],
                "culture_fit_prediction": error_msg,
            }
        },
        "errors": [f"Soft Skills Evaluator error: {error_msg}"],
    }
