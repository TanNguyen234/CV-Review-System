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
Bạn là một chuyên gia tuyển dụng công nghệ cao cấp. Nhiệm vụ của bạn là phân tích văn bản CV của ứng viên và xác định cấp độ chuyên môn cũng như ngành nghề của họ.

Xác định chính xác một trong các cấp độ: "Intern", "Fresher", "Junior", "Mid-level", hoặc "Senior".
Xác định ngành nghề (ví dụ: IT, Marketing, Tài chính, v.v.).
Trích xuất tên đầy đủ của ứng viên.

Sau đó, cung cấp một tiêu chí chấm điểm động ngắn (3-4 câu) mà các đánh giá viên nên tuân theo cho cấp độ cụ thể này.
YÊU CẦU QUAN TRỌNG KHI TẠO TIÊU CHÍ (dynamic_rubric):
- Nếu là "Intern" hoặc "Fresher": Hãy nêu rõ "Ứng viên là người mới bắt đầu. Việc thiếu kinh nghiệm chuyên môn là điều bình thường. Hãy tập trung đánh giá vào các dự án cá nhân/đồ án và tiềm năng phát triển."
- Nếu là "Junior", "Mid-level", "Senior": Hãy nêu rõ "BẮT BUỘC ứng viên phải có kinh nghiệm làm việc thực tế. Đây là ĐIỂM CỨNG trong phần chuyên môn. Nếu chỉ có dự án cá nhân mà không có kinh nghiệm đi làm thật, phải trừ điểm nặng phần Kinh nghiệm."
"""


class ProfilerResult(BaseModel):
    name: str = Field(description="Tên đầy đủ của ứng viên")
    level: str = Field(
        description="Cấp độ chuyên môn (Intern, Fresher, Junior, Mid-level, Senior)"
    )
    industry: str = Field(
        description="Ngành nghề của ứng viên (ví dụ: IT)"
    )
    dynamic_rubric: str = Field(
        description="Hướng dẫn chấm điểm cụ thể dựa trên cấp độ này"
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
            "dynamic_rubric": "Use standard strict evaluation criteria.",
            "errors": [f"Profiler error: {str(e)}"],
        }
