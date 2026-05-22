"""
Tech Stack Evaluator Node — Deep analysis of candidate's technology stack.
Categorizes skills into domains and evaluates depth of expertise.
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
from app.services.ai.prompts.evaluator_prompts import TECH_STACK_PROMPT
from app.core.logging_config import pipeline_logger


class TechDomainModel(BaseModel):
    domain_name: str = Field(description="Tên nhóm công nghệ (Frontend, Backend...)")
    skills: List[str] = Field(description="Danh sách kỹ năng")
    assessment: str = Field(description="Đánh giá ngắn gọn về độ sâu")


class TechStackResult(BaseModel):
    core_competency: str = Field(description="Năng lực cốt lõi")
    domains: List[TechDomainModel] = Field(description="Phân loại kỹ năng")
    overall_tech_assessment: str = Field(description="Đánh giá tổng quan stack")


def tech_stack_evaluator_node(state: AgentState) -> dict:
    """
    Evaluates the tech stack of the candidate.
    Categorizes into domains and assesses core competencies.
    """
    start = time.time()
    pipeline_logger.node_start("tech_stack_evaluator")

    cleaned_text = state.get("cleaned_text", "")
    sections = state.get("sections", {})

    # Prioritize Skills and Experience sections, fallback to full text
    context_parts = []
    if "SKILLS" in sections:
        context_parts.append(f"[SKILLS]:\n{sections['SKILLS']}")
    if "EXPERIENCE" in sections:
        context_parts.append(f"[EXPERIENCE]:\n{sections['EXPERIENCE']}")
    if "WORK EXPERIENCE" in sections:
        context_parts.append(f"[WORK EXPERIENCE]:\n{sections['WORK EXPERIENCE']}")
    if "PROJECTS" in sections:
        context_parts.append(f"[PROJECTS]:\n{sections['PROJECTS']}")

    eval_context = "\n\n".join(context_parts) if context_parts else cleaned_text

    if not eval_context.strip():
        pipeline_logger.node_error(
            "tech_stack_evaluator", "No CV text available for tech stack analysis."
        )
        return _build_fallback_result("Không có dữ liệu CV để phân tích.")

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content=TECH_STACK_PROMPT),
            HumanMessage(
                content=f"Dữ liệu CV để phân tích Tech Stack:\n{eval_context}"
            ),
        ]

        result = invoke_structured(
            llm,
            TechStackResult,
            messages,
            node_name="tech_stack_evaluator",
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "tech_stack_evaluator",
            duration_ms=duration_ms,
        )

        return {
            "scores": {
                "TECH_STACK_EVAL": result.model_dump()
            },
            "processing_metadata": {
                "tech_stack_evaluator_duration_ms": round(duration_ms, 2),
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error(
            "tech_stack_evaluator", str(e), retryable=False
        )
        return _build_fallback_result(f"Lỗi phân tích Tech Stack: {str(e)}")


def _build_fallback_result(error_msg: str) -> dict:
    """Builds a safe fallback result when LLM fails."""
    return {
        "scores": {
            "TECH_STACK_EVAL": {
                "core_competency": "Chưa xác định",
                "domains": [],
                "overall_tech_assessment": error_msg,
            }
        },
        "errors": [f"Tech Stack Evaluator error: {error_msg}"],
    }
