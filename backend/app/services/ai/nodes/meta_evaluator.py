"""
Meta Evaluator Node — Aggregates phase scores and provides final verdict.
Considers confidence levels and validation results for calibrated scoring.
"""

import json
import time
from typing import List, Dict

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import (
    get_pro_llm,
    invoke_structured,
    LLMTransientError,
    LLMPermanentError,
)
from app.services.ai.prompts.evaluator_prompts import META_PROMPT
from app.core.logging_config import pipeline_logger


class MetaEvaluationResult(BaseModel):
    final_score: int = Field(description="Tổng điểm trên thang 100")
    confidence: int = Field(
        default=3,
        description="Mức độ tin cậy tổng thể 1-5",
        ge=1,
        le=5,
    )
    score_adjustments: Dict[str, int] = Field(
        default_factory=dict,
        description="Điều chỉnh điểm cho các phase (nếu có)",
    )
    strengths: List[str] = Field(description="Ít nhất 4 điểm mạnh")
    priority_actions: List[str] = Field(
        description="Ít nhất 4 hành động cải thiện ưu tiên"
    )
    general_advice: List[str] = Field(
        description="Ít nhất 5 lời khuyên phát triển nghề nghiệp"
    )
    industry_standards: str = Field(
        description="Nhận xét về tiêu chuẩn ngành"
    )
    industry_keywords: List[str] = Field(
        description="Các từ khóa ngành nên có"
    )
    summary: str = Field(description="Tóm tắt tổng quan ngắn gọn")
    detailed_analysis: str = Field(description="Phân tích chuyên sâu cực kỳ chi tiết")


def meta_evaluator_node(state: AgentState) -> dict:
    """
    Aggregates phase scores and provides a comprehensive final verdict.
    Takes into account confidence levels and validation results.
    """
    start = time.time()
    pipeline_logger.node_start("meta_evaluator")

    scores = state.get("scores", {})
    confidence_scores = state.get("confidence_scores", {})
    validation_result = state.get("validation_result", {})

    try:
        llm = get_pro_llm()

        # Build comprehensive input for meta evaluation
        input_data = {
            "phase_scores": {
                k: v
                for k, v in scores.items()
                if k.startswith("PHASE")
            },
            "confidence_scores": confidence_scores,
            "candidate_info": {
                "name": state.get("candidate_name"),
                "level": state.get("candidate_level"),
                "industry": state.get("industry"),
            },
        }

        # Include validation results if available
        if validation_result:
            input_data["validation"] = {
                "is_consistent": validation_result.get(
                    "is_consistent", True
                ),
                "anomalies": validation_result.get("anomalies", []),
                "suggested_adjustments": validation_result.get(
                    "adjustments", {}
                ),
            }

        # Include JD analysis if available
        jd_analysis = state.get("jd_analysis")
        if jd_analysis:
            input_data["jd_analysis"] = jd_analysis

        messages = [
            SystemMessage(content=META_PROMPT),
            HumanMessage(
                content=f"Dữ liệu đánh giá chi tiết:\n"
                f"{json.dumps(input_data, ensure_ascii=False, indent=2)}"
            ),
        ]

        result = invoke_structured(
            llm, MetaEvaluationResult, messages, node_name="meta_evaluator"
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "meta_evaluator",
            duration_ms=duration_ms,
            score=result.final_score,
        )

        return {
            "scores": {
                "META": {
                    "final_score": result.final_score,
                    "confidence": result.confidence,
                    "score_adjustments": result.score_adjustments,
                    "strengths": result.strengths,
                    "priority_actions": result.priority_actions,
                    "general_advice": result.general_advice,
                    "industry_standards": result.industry_standards,
                    "industry_keywords": result.industry_keywords,
                    "summary": result.summary,
                    "detailed_analysis": result.detailed_analysis,
                }
            },
            "processing_metadata": {
                "meta_evaluator_duration_ms": round(duration_ms, 2)
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error("meta_evaluator", str(e))
        # Fallback score calculation
        total = sum(
            s.get("score", 0)
            for k, s in scores.items()
            if k.startswith("PHASE")
        )
        return {
            "scores": {
                "META": {
                    "final_score": total,
                    "confidence": 1,
                    "error": f"Lỗi tổng hợp: {str(e)}",
                    "summary": "Đánh giá tổng hợp thất bại. Điểm được tính cơ học từ các phase.",
                }
            },
            "errors": [f"Meta Evaluator error: {str(e)}"],
        }
