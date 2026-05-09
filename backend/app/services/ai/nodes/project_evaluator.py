"""
Project Evaluator Node — Deep analysis of individual projects listed in the CV.
Evaluates each project's technical depth, impact, relevance, and role clarity.
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
from app.core.logging_config import pipeline_logger


PROJECT_EVAL_PROMPT = """
Bạn là một Senior Technical Architect với 15+ năm kinh nghiệm review portfolio.
Nhiệm vụ: Phân tích CHI TIẾT TỪNG DỰ ÁN có trong CV của ứng viên.

Ngữ cảnh đánh giá: {dynamic_rubric}
Cấp độ ứng viên: {candidate_level}
Số năm kinh nghiệm: {years_of_experience}

YÊU CẦU TUYỆT ĐỐI:
1. PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT.
2. KHÔNG BỊA ĐẶT. Chỉ phân tích những gì CÓ THẬT trong CV.
3. Mỗi dự án phải được đánh giá riêng biệt với các tiêu chí:
   - tech_stack_analysis: Phân tích stack công nghệ (có phù hợp? có outdated? có đa dạng?).
   - role_clarity: Vai trò của ứng viên có rõ ràng không? (Lead, Member, Solo?)
   - impact_assessment: Dự án có thể hiện được impact thực tế không? (định lượng: số user, doanh thu, hiệu suất...)
   - complexity_rating: 1-5 (1=đơn giản, 5=phức tạp enterprise-level)
   - improvement_suggestion: 1-2 gợi ý cải thiện cách trình bày dự án này trong CV.
4. Nếu CV không có dự án nào, trả về mảng rỗng.
5. Cuối cùng đưa ra nhận xét tổng quan (overall_assessment) về chất lượng portfolio.

Trả về JSON:
{{
  "projects": [
    {{
      "project_name": string,
      "tech_stack_analysis": string (phân tích chi tiết stack),
      "role_clarity": string (vai trò rõ ràng hay mơ hồ),
      "impact_assessment": string (impact đo lường được?),
      "complexity_rating": integer (1-5),
      "improvement_suggestion": string (gợi ý cải thiện)
    }}
  ],
  "overall_assessment": string (nhận xét tổng quan portfolio),
  "portfolio_score": integer (0-10, chất lượng portfolio tổng thể)
}}
"""


class ProjectEvaluation(BaseModel):
    project_name: str = Field(description="Tên dự án")
    tech_stack_analysis: str = Field(description="Phân tích stack công nghệ")
    role_clarity: str = Field(description="Đánh giá độ rõ ràng của vai trò")
    impact_assessment: str = Field(description="Đánh giá impact")
    complexity_rating: int = Field(description="Độ phức tạp 1-5", ge=1, le=5)
    improvement_suggestion: str = Field(description="Gợi ý cải thiện")


class ProjectEvalResult(BaseModel):
    projects: List[ProjectEvaluation] = Field(
        description="Danh sách đánh giá từng dự án"
    )
    overall_assessment: str = Field(
        description="Nhận xét tổng quan portfolio"
    )
    portfolio_score: int = Field(
        description="Điểm portfolio tổng thể 0-10", ge=0, le=10
    )


def project_evaluator_node(state: AgentState) -> dict:
    """
    Deep analysis of each project in the CV.
    Evaluates tech stack, role clarity, impact, and complexity.
    """
    start = time.time()
    pipeline_logger.node_start("project_evaluator")

    cleaned_text = state.get("cleaned_text", "")
    sections = state.get("sections", {})

    # Build project context: prefer sections-based, fallback to full text
    project_context = ""
    if sections:
        project_context = "\n\n".join(
            [f"[{k}]: {v}" for k, v in sections.items()]
        )
    else:
        project_context = cleaned_text

    if not project_context:
        pipeline_logger.node_error(
            "project_evaluator", "No CV text available"
        )
        return {
            "scores": {
                "PROJECT_EVAL": {
                    "projects": [],
                    "overall_assessment": "Không có dữ liệu CV để phân tích.",
                    "portfolio_score": 0,
                }
            },
            "errors": ["Project Evaluator: No CV text available."],
        }

    try:
        llm = get_llm()

        dynamic_rubric = state.get(
            "dynamic_rubric", "Sử dụng tiêu chuẩn đánh giá thông thường."
        )
        candidate_level = state.get("candidate_level", "Unknown")
        years_of_experience = state.get("years_of_experience", 0.0)

        formatted_prompt = PROJECT_EVAL_PROMPT.format(
            dynamic_rubric=dynamic_rubric,
            candidate_level=candidate_level,
            years_of_experience=years_of_experience,
        )

        messages = [
            SystemMessage(content=formatted_prompt),
            HumanMessage(
                content=f"Dữ liệu CV để phân tích dự án:\n{project_context}"
            ),
        ]

        result = invoke_structured(
            llm,
            ProjectEvalResult,
            messages,
            node_name="project_evaluator",
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "project_evaluator",
            duration_ms=duration_ms,
            score=result.portfolio_score,
        )

        return {
            "scores": {
                "PROJECT_EVAL": {
                    "projects": [p.model_dump() for p in result.projects],
                    "overall_assessment": result.overall_assessment,
                    "portfolio_score": result.portfolio_score,
                }
            },
            "processing_metadata": {
                "project_evaluator_duration_ms": round(duration_ms, 2),
                "projects_analyzed": len(result.projects),
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error(
            "project_evaluator", str(e), retryable=False
        )
        return {
            "scores": {
                "PROJECT_EVAL": {
                    "projects": [],
                    "overall_assessment": f"Lỗi phân tích: {str(e)}",
                    "portfolio_score": 0,
                }
            },
            "errors": [f"Project Evaluator error: {str(e)}"],
        }
