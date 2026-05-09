"""
Profiler Node — Determines candidate level and generates dynamic evaluation rubrics.
"""

import time
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

PROFILER_PROMPT = """
Bạn là một chuyên gia tuyển dụng công nghệ cao cấp. Nhiệm vụ của bạn là phân tích văn bản CV của ứng viên và xác định cấp độ chuyên môn, ngành nghề, cũng như SỐ NĂM KINH NGHIỆM thực tế.

1. Trích xuất tên đầy đủ của ứng viên.
2. Xác định chính xác một trong các cấp độ: "Intern", "Fresher", "Junior", "Mid-level", hoặc "Senior".
3. Xác định ngành nghề (ví dụ: IT, Marketing, Tài chính, v.v.).
4. TÍNH TOÁN chính xác SỐ NĂM KINH NGHIỆM (years_of_experience) làm việc thực tế dựa trên các mốc thời gian trong CV (chỉ tính kinh nghiệm đi làm chính thức, làm tròn tới 1 chữ số thập phân, ví dụ: 1.5, 2.0). Nếu không có, ghi 0.0.

Sau đó, cung cấp một tiêu chí chấm điểm động ngắn (3-4 câu) mà các đánh giá viên nên tuân theo.
YÊU CẦU QUAN TRỌNG KHI TẠO TIÊU CHÍ (dynamic_rubric):
- Nếu là "Intern" hoặc "Fresher" (hoặc YoE < 1): Hãy nêu rõ "Ứng viên là người mới bắt đầu. Việc thiếu kinh nghiệm chuyên môn là điều bình thường. Hãy tập trung đánh giá vào các dự án cá nhân/đồ án và tiềm năng phát triển."
- Nếu là "Junior", "Mid-level", "Senior" (hoặc YoE >= 1): Hãy nêu rõ "BẮT BUỘC ứng viên phải có kinh nghiệm làm việc thực tế (Ứng viên có {years_of_experience} năm kinh nghiệm). Đây là ĐIỂM CỨNG trong phần chuyên môn. Nếu CV ghi senior nhưng kinh nghiệm quá ngắn, phải trừ điểm nặng."
"""


class ProfilerResult(BaseModel):
    name: str = Field(description="Tên đầy đủ của ứng viên")
    level: str = Field(
        description="Cấp độ chuyên môn (Intern, Fresher, Junior, Mid-level, Senior)"
    )
    industry: str = Field(
        description="Ngành nghề của ứng viên (ví dụ: IT)"
    )
    years_of_experience: float = Field(
        description="Số năm kinh nghiệm làm việc thực tế được tính toán từ các mốc thời gian"
    )
    dynamic_rubric: str = Field(
        description="Hướng dẫn chấm điểm cụ thể dựa trên cấp độ và số năm kinh nghiệm"
    )


def profiler_node(state: AgentState) -> dict:
    """
    Analyzes the CV to determine candidate level and dynamically adjust evaluation rubrics.
    """
    start = time.time()
    pipeline_logger.node_start("profiler")

    cleaned_text = state.get("cleaned_text", "")

    if not cleaned_text:
        pipeline_logger.node_error("profiler", "No cleaned text available")
        return {
            "candidate_name": "N/A",
            "candidate_level": "Unknown",
            "industry": "N/A",
            "years_of_experience": 0.0,
            "dynamic_rubric": "Use standard evaluation criteria.",
            "errors": ["Profiler: No cleaned text available."],
        }

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content=PROFILER_PROMPT),
            HumanMessage(
                content=f"Analyze this CV:\n{cleaned_text[:3000]}"
            ),
        ]

        result = invoke_structured(
            llm, ProfilerResult, messages, node_name="profiler"
        )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "profiler",
            duration_ms=duration_ms,
        )

        return {
            "candidate_name": result.name,
            "candidate_level": result.level,
            "industry": result.industry,
            "years_of_experience": result.years_of_experience,
            "dynamic_rubric": result.dynamic_rubric,
            "processing_metadata": {
                "profiler_duration_ms": round(duration_ms, 2)
            },
            "errors": [],
        }

    except LLMTransientError:
        raise  # Let RetryPolicy handle

    except (LLMPermanentError, Exception) as e:
        pipeline_logger.node_error("profiler", str(e))
        return {
            "candidate_name": "N/A",
            "candidate_level": "Unknown",
            "industry": "N/A",
            "years_of_experience": 0.0,
            "dynamic_rubric": "Use standard strict evaluation criteria.",
            "errors": [f"Profiler error: {str(e)}"],
        }
