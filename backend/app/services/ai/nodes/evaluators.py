"""
Phase Evaluator Nodes — Evaluate CV across multiple dimensions.
Supports parallel execution via fan-out from the graph.
Includes confidence scoring and enrichment context injection.
"""

import time
from typing import Dict, Any

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import (
    get_llm,
    invoke_structured,
    LLMTransientError,
    LLMPermanentError,
)
from app.services.ai.prompts.evaluator_prompts import (
    PHASE2_PROMPT,
    PHASE3_PROMPT,
    PHASE4_PROMPT,
)
from app.core.logging_config import pipeline_logger


class PhaseResult(BaseModel):
    """Schema for Phase evaluation results with confidence scoring."""

    score: int = Field(description="The total score for this phase")
    confidence: int = Field(
        default=3,
        description="Confidence level 1-5 for this evaluation",
        ge=1,
        le=5,
    )
    reasoning: str = Field(
        default="",
        description="Chain-of-thought reasoning for the score",
    )
    details: Dict[str, Any] = Field(
        description="Breakdown of sub-scores and feedback"
    )
    feedback: str = Field(description="Overall feedback for this phase")


def _build_market_insight_context(state: AgentState) -> str:
    """
    Build market insight context string from the structured MarketInsight
    produced by the enrichment node. Used by Phase 3 evaluator.
    """
    market_insight = state.get("market_insight")
    if not market_insight:
        return ""

    parts = ["Ngữ cảnh thị trường tuyển dụng (dùng để đánh giá mức độ cập nhật của ứng viên):"]

    salary = market_insight.get("salary_range", "")
    if salary:
        parts.append(f"- Mức lương tham khảo: {salary}")

    demand = market_insight.get("market_demand", "")
    if demand:
        parts.append(f"- Nhu cầu thị trường: {demand}")

    trending = market_insight.get("trending_skills", [])
    if trending:
        parts.append(f"- Kỹ năng xu hướng: {', '.join(trending)}")

    standards = market_insight.get("standard_requirements", "")
    if standards:
        parts.append(f"- Yêu cầu tiêu chuẩn ngành: {standards}")

    return "\n".join(parts)


def _evaluate_phase(
    state: AgentState,
    phase_name: str,
    prompt_template: str,
    input_text: str,
    inject_enrichment: bool = False,
) -> dict:
    """
    Generic function to evaluate a phase.
    Raises LLMTransientError for retryable failures (handled by RetryPolicy).
    """
    start = time.time()
    pipeline_logger.node_start(phase_name)

    try:
        llm = get_llm()

        dynamic_rubric = state.get(
            "dynamic_rubric", "Sử dụng tiêu chuẩn đánh giá thông thường."
        )

        # Build format kwargs
        format_kwargs = {"dynamic_rubric": dynamic_rubric}

        # Inject market insight context for Phase 3
        if inject_enrichment:
            market_ctx = _build_market_insight_context(state)
            format_kwargs["market_insight_context"] = market_ctx
        elif "{market_insight_context}" in prompt_template:
            format_kwargs["market_insight_context"] = ""

        formatted_prompt = prompt_template.format(**format_kwargs)

        messages = [
            SystemMessage(content=formatted_prompt),
            HumanMessage(
                content=f"Dữ liệu CV để đánh giá:\n{input_text}"
            ),
        ]

        result = invoke_structured(
            llm, PhaseResult, messages, node_name=phase_name
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            phase_name,
            duration_ms=duration_ms,
            score=result.score,
        )

        return {
            "scores": {
                phase_name: {
                    "score": result.score,
                    "details": result.details,
                    "feedback": result.feedback,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                }
            },
            "confidence_scores": {phase_name: result.confidence},
            "processing_metadata": {
                f"{phase_name}_duration_ms": round(duration_ms, 2)
            },
            "errors": [],
        }

    except LLMTransientError:
        # Let LangGraph RetryPolicy handle this
        raise

    except LLMPermanentError as e:
        pipeline_logger.node_error(phase_name, str(e), retryable=False)
        return {
            "scores": {
                phase_name: {
                    "score": 0,
                    "feedback": "Đánh giá thất bại do lỗi hệ thống.",
                    "confidence": 1,
                    "reasoning": f"Lỗi: {str(e)}",
                }
            },
            "confidence_scores": {phase_name: 1},
            "errors": [f"Lỗi đánh giá {phase_name}: {str(e)}"],
        }

    except Exception as e:
        pipeline_logger.node_error(phase_name, str(e), retryable=False)
        return {
            "scores": {
                phase_name: {
                    "score": 0,
                    "feedback": "Đánh giá thất bại do lỗi không xác định.",
                    "confidence": 1,
                }
            },
            "confidence_scores": {phase_name: 1},
            "errors": [f"Lỗi đánh giá {phase_name}: {str(e)}"],
        }


def phase2_evaluator_node(state: AgentState) -> dict:
    """Evaluates PHASE 2: Core Foundation (Format, ATS, Content Quality)."""
    return _evaluate_phase(
        state,
        "PHASE2",
        PHASE2_PROMPT,
        state.get("cleaned_text", ""),
    )


def phase3_evaluator_node(state: AgentState) -> dict:
    """Evaluates PHASE 3: Specialized Assessment (Experience, Technical, Projects)."""
    sections = state.get("sections", {})
    context = "\n\n".join([f"[{k}]: {v}" for k, v in sections.items()])
    return _evaluate_phase(
        state,
        "PHASE3",
        PHASE3_PROMPT,
        context,
        inject_enrichment=True,  # Feed RAG results to Phase 3
    )


def phase4_evaluator_node(state: AgentState) -> dict:
    """Evaluates PHASE 4: Bonus Factors (Leadership, International, Awards)."""
    return _evaluate_phase(
        state,
        "PHASE4",
        PHASE4_PROMPT,
        state.get("cleaned_text", ""),
    )
