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
        return _build_evaluator_fallback(phase_name, str(e), state)

    except Exception as e:
        pipeline_logger.node_error(phase_name, str(e), retryable=False)
        return _build_evaluator_fallback(phase_name, str(e), state)


def _build_evaluator_fallback(
    phase_name: str, error_msg: str, state: AgentState
) -> dict:
    """
    Build a meaningful fallback result when an evaluator fails.
    Extracts what we can from the CV text instead of returning empty details.
    """
    cleaned_text = state.get("cleaned_text", "")
    sections = state.get("sections", {})
    text_len = len(cleaned_text)

    if phase_name == "PHASE2":
        # Estimate basic scores from text analysis
        has_email = "@" in cleaned_text
        has_phone = any(c.isdigit() for c in cleaned_text[:500])
        has_links = any(kw in cleaned_text.lower() for kw in ["github", "linkedin", "portfolio"])

        format_score = 8 if text_len > 500 else 3
        foundation_score = min(10, (5 if has_email else 0) + (3 if has_phone else 0) + (2 if has_links else 0))
        content_score = min(10, text_len // 200)  # rough heuristic
        total = format_score + foundation_score + content_score

        details = {
            "format_ats": {
                "score": format_score,
                "feedback": (
                    f"CV có {text_len} ký tự và {len(sections)} section. "
                    f"{'Định dạng cơ bản đạt yêu cầu.' if text_len > 500 else 'CV quá ngắn, cần bổ sung nội dung.'}"
                ),
                "confidence": 2,
            },
            "professional_foundation": {
                "score": foundation_score,
                "feedback": (
                    f"{'Có email.' if has_email else 'Thiếu email.'} "
                    f"{'Có SĐT.' if has_phone else 'Thiếu SĐT.'} "
                    f"{'Có link GitHub/LinkedIn.' if has_links else 'Thiếu link portfolio.'}"
                ),
                "confidence": 2,
            },
            "content_quality": {
                "score": content_score,
                "feedback": (
                    f"Đánh giá tự động dựa trên độ dài và cấu trúc CV. "
                    f"CV có {len(sections)} section được nhận diện: {', '.join(list(sections.keys())[:5])}."
                ),
                "confidence": 1,
            },
        }
        return {
            "scores": {
                phase_name: {
                    "score": total,
                    "details": details,
                    "feedback": f"Đánh giá tự động do lỗi AI ({error_msg[:80]}). Điểm ước lượng: {total}/60.",
                    "confidence": 1,
                    "reasoning": f"Fallback scoring: {error_msg}",
                }
            },
            "confidence_scores": {phase_name: 1},
            "errors": [f"Lỗi đánh giá {phase_name}: {error_msg}"],
        }

    elif phase_name == "PHASE3":
        # Estimate from sections
        has_experience = "EXPERIENCE" in sections or "WORK EXPERIENCE" in sections
        has_skills = "SKILLS" in sections
        has_projects = "PROJECTS" in sections or "PROJECT" in sections

        exp_score = 8 if has_experience else 2
        tech_score = 5 if has_skills else 2
        proj_score = 5 if has_projects else 1
        total = exp_score + tech_score + proj_score

        # Try to extract skill keywords
        skills_text = sections.get("SKILLS", "")
        skill_keywords = [
            w.strip() for w in skills_text.replace(",", "\n").split("\n")
            if w.strip() and len(w.strip()) > 1
        ][:10]

        details = {
            "experience": {
                "score": exp_score,
                "feedback": (
                    f"{'Có section kinh nghiệm làm việc.' if has_experience else 'Không tìm thấy section kinh nghiệm.'} "
                    f"Cần đánh giá lại để phân tích chi tiết hơn."
                ),
                "confidence": 1,
            },
            "technical_proof": {
                "score": tech_score,
                "feedback": (
                    f"{'Có section kỹ năng' if has_skills else 'Không tìm thấy section kỹ năng'}. "
                    f"{'Kỹ năng: ' + ', '.join(skill_keywords[:5]) + '.' if skill_keywords else ''}"
                ),
                "confidence": 1,
            },
            "projects": {
                "score": proj_score,
                "feedback": (
                    f"{'Có section dự án.' if has_projects else 'Không tìm thấy section dự án.'} "
                    f"Đánh giá tự động, cần phân tích chi tiết qua AI."
                ),
                "confidence": 1,
            },
        }
        return {
            "scores": {
                phase_name: {
                    "score": total,
                    "details": details,
                    "feedback": f"Đánh giá tự động do lỗi AI ({error_msg[:80]}). Điểm ước lượng: {total}/40.",
                    "confidence": 1,
                    "reasoning": f"Fallback scoring: {error_msg}",
                }
            },
            "confidence_scores": {phase_name: 1},
            "errors": [f"Lỗi đánh giá {phase_name}: {error_msg}"],
        }

    else:  # PHASE4 or unknown
        return {
            "scores": {
                phase_name: {
                    "score": 0,
                    "details": {
                        "leadership": {"score": 0, "feedback": "Chưa đánh giá được do lỗi hệ thống.", "confidence": 1},
                        "languages": {"score": 0, "feedback": "Chưa đánh giá được do lỗi hệ thống.", "confidence": 1},
                        "awards": {"score": 0, "feedback": "Chưa đánh giá được do lỗi hệ thống.", "confidence": 1},
                    },
                    "feedback": f"Đánh giá tự động do lỗi AI ({error_msg[:80]}).",
                    "confidence": 1,
                }
            },
            "confidence_scores": {phase_name: 1},
            "errors": [f"Lỗi đánh giá {phase_name}: {error_msg}"],
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
