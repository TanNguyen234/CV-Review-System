"""
Phase Evaluator Nodes — Evaluate CV across multiple dimensions.
Supports parallel execution via fan-out from the graph.
Includes confidence scoring and enrichment context injection.
"""

import json
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


def _build_enrichment_context(state: AgentState) -> str:
    """
    Build enrichment context string from RAG results for injection into prompts.
    """
    text_insights = state.get("text_insights", {})
    if not text_insights:
        return ""

    rag_context = text_insights.get("rag_context", {})
    if not rag_context:
        return ""

    results = rag_context.get("results", [])
    if not results:
        return ""

    context_parts = [
        "Ngữ cảnh bổ sung từ nghiên cứu thị trường (sử dụng để đánh giá chính xác hơn):"
    ]
    for i, result in enumerate(results[:3], 1):
        title = result.get("title", "")
        content = result.get("content", "")[:300]
        if title or content:
            context_parts.append(f"{i}. {title}: {content}")

    return "\n".join(context_parts)


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

        # Inject enrichment context for Phase 3
        if inject_enrichment:
            enrichment_ctx = _build_enrichment_context(state)
            format_kwargs["enrichment_context"] = enrichment_ctx
        elif "{enrichment_context}" in prompt_template:
            format_kwargs["enrichment_context"] = ""

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
