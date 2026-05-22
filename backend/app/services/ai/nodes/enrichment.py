"""
Enrichment Node — Web search for market context and industry standards.
Uses Tavily API for lightweight RAG enrichment.
"""

import time
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.ai.state import AgentState
from app.core.config import settings
from app.core.logging_config import pipeline_logger
from app.services.ai.helpers.llm_factory import get_llm, invoke_structured

class MarketInsightResult(BaseModel):
    salary_range: str = Field(description="Mức lương tham khảo tại THỊ TRƯỜNG VIỆT NAM, đơn vị VND, ví dụ: 8-15 triệu VND/tháng")
    market_demand: str = Field(description="Nhu cầu tuyển dụng tại Việt Nam và xu hướng thị trường")
    trending_skills: list[str] = Field(description="Danh sách các kỹ năng đang là xu hướng cho vị trí này tại Việt Nam")
    standard_requirements: str = Field(description="Yêu cầu tiêu chuẩn của ngành cho vị trí/cấp độ này tại Việt Nam")

MARKET_INSIGHT_PROMPT = """
Bạn là một chuyên gia phân tích thị trường tuyển dụng CHUẤN VIỆT NAM.

QUY TẮC BẮT BUỘC:
1. Mức lương PHẢI theo thị trường VIỆT NAM, đơn vị VND (đồng Việt Nam), ví dụ: "8 - 15 triệu VND/tháng".
2. TUYỆT ĐỐI KHÔNG dùng USD, EUR, hay bất kỳ đơn vị tiền nước ngoài nào. Không quy đổi.
3. Nhu cầu thị trường phải dựa vào thực tế tuyển dụng Việt Nam (các nền tảng như VietnamWorks, TopDev, ITviec, LinkedIn Việt Nam).
4. Kỹ năng xu hướng phải là những kỹ năng đang được các công ty Việt Nam tìm kiếm nhiều nhất.
5. Phản hồi hoàn toàn bằng TIẾNG VIỆT.

BẢNG THAM KHẢO LƯƠNG VIỆT NAM (IT, 2025-2026):
- Intern/Thực tập: 3 - 6 triệu VND/tháng
- Fresher: 7 - 12 triệu VND/tháng
- Junior (1-2 năm): 10 - 18 triệu VND/tháng
- Mid-level (2-4 năm): 18 - 35 triệu VND/tháng
- Senior (5+ năm): 30 - 60 triệu VND/tháng
- Lead/Manager: 40 - 80+ triệu VND/tháng
(Ngành khác có thể khác, nhưng PHẢI theo VND và thị trường Việt Nam)

Dựa vào các kết quả tìm kiếm web dưới đây, hãy tổng hợp thông tin thị trường tuyển dụng cho vị trí và cấp độ của ứng viên.
Nếu kết quả tìm kiếm không đủ thông tin, hãy tham khảo bảng lương ở trên để ước tính.
"""


def _build_query(sections: dict, level: str = "", industry: str = "") -> str:
    """
    Build a comprehensive search query from CV data.
    Uses skills, objective, level, and industry for better results.
    """
    parts = []

    # Add level and industry for targeted results
    if level and level != "Unknown":
        parts.append(f"{level} level")
    if industry:
        parts.append(f"{industry} industry")

    # Try to find skills section
    skills = sections.get("SKILLS", sections.get("AREAS OF EXPERTISE", ""))
    if skills:
        # Take key skills, not the full text
        skill_lines = [
            line.strip()
            for line in skills.split("\n")
            if line.strip() and len(line.strip()) > 2
        ]
        parts.append(" ".join(skill_lines[:5]))

    # Try to extract role from objective/summary if available
    objective = sections.get("OBJECTIVE", sections.get("SUMMARY", ""))
    if objective:
        parts.append(objective[:100])

    parts.append("mức lương tuyển dụng Việt Nam 2025 2026 yêu cầu kỹ năng")

    query = " ".join([part for part in parts if part]).strip()
    # Limit query length for API
    return query[:300] if query else ""


def _get_offline_market_insight(level: str) -> dict:
    """Return hardcoded offline market insight when API fails."""
    level_lower = level.lower() if level else ""
    if "intern" in level_lower or "thực tập" in level_lower:
        salary = "3 - 6 triệu VND/tháng"
        req = "Kiến thức nền tảng tốt, thái độ học hỏi nhanh, biết sử dụng Git."
    elif "fresher" in level_lower:
        salary = "7 - 12 triệu VND/tháng"
        req = "Nắm vững kiến thức cơ bản, có đồ án thực tế, có thể làm việc dưới sự hướng dẫn."
    elif "junior" in level_lower:
        salary = "10 - 18 triệu VND/tháng"
        req = "1-2 năm kinh nghiệm thực tế, làm việc độc lập với task cơ bản, quen thuộc Agile/Scrum."
    elif "senior" in level_lower:
        salary = "30 - 60 triệu VND/tháng"
        req = "5+ năm kinh nghiệm, khả năng thiết kế hệ thống, tối ưu hiệu năng, mentoring."
    elif "mid" in level_lower:
        salary = "18 - 35 triệu VND/tháng"
        req = "2-4 năm kinh nghiệm, nắm vững best practices, xử lý tốt bài toán độ khó trung bình."
    else:
        salary = "Thỏa thuận theo năng lực (Ước tính tự động)"
        req = "Yêu cầu phụ thuộc vào vị trí và quy mô công ty."
        
    return {
        "salary_range": salary,
        "market_demand": "Thị trường ưu tiên ứng viên có kỹ năng thực chiến và tư duy giải quyết vấn đề.",
        "trending_skills": ["AI/ML", "Cloud", "Microservices", "System Design"],
        "standard_requirements": req
    }


def enrichment_node(state: AgentState) -> dict:
    """
    Enriches the pipeline state with market context from web search.
    Results are fed into Phase 3 evaluator for technology relevance assessment.
    """
    start = time.time()
    pipeline_logger.node_start("enrichment")

    level = state.get("candidate_level", "")
    industry = state.get("industry", "")

    api_key = settings.tavily_api_key
    if not api_key:
        pipeline_logger.node_error(
            "enrichment", "TAVILY_API_KEY not set - using offline fallback", retryable=False
        )
        offline_insight = _get_offline_market_insight(level)
        return {
            "text_insights": {"rag_context": "Offline fallback"},
            "market_insight": offline_insight,
            "processing_metadata": {"enrichment_skipped": True, "offline_fallback": True},
            "errors": ["TAVILY_API_KEY not set — using offline fallback"],
        }

    sections = state.get("sections", {})

    query = _build_query(sections, level, industry)
    if not query:
        return {
            "text_insights": {},
            "processing_metadata": {"enrichment_skipped": True},
            "errors": [],
        }

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5)
        
        # Parse with LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=MARKET_INSIGHT_PROMPT),
            HumanMessage(
                content=f"Truy vấn: {query}\n\nKết quả tìm kiếm:\n{str(results)}"
            ),
        ]
        
        try:
            insight_result = invoke_structured(llm, MarketInsightResult, messages, node_name="enrichment")
            market_insight = {
                "salary_range": insight_result.salary_range,
                "market_demand": insight_result.market_demand,
                "trending_skills": insight_result.trending_skills,
                "standard_requirements": insight_result.standard_requirements
            }
        except Exception as e:
            pipeline_logger.node_error("enrichment", f"LLM parsing failed, using offline fallback: {e}")
            market_insight = _get_offline_market_insight(level)

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "enrichment",
            duration_ms=duration_ms,
        )

        return {
            "text_insights": {"rag_context": "Processed into market_insight"},
            "market_insight": market_insight,
            "processing_metadata": {
                "enrichment_duration_ms": round(duration_ms, 2),
                "enrichment_query": query[:100],
                "enrichment_results_count": len(
                    results.get("results", [])
                ),
            },
            "errors": [],
        }

    except Exception as exc:
        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_error(
            "enrichment", str(exc), retryable=True
        )
        offline_insight = _get_offline_market_insight(level)
        return {
            "text_insights": {"rag_context": "Offline fallback"},
            "market_insight": offline_insight,
            "processing_metadata": {
                "enrichment_duration_ms": round(duration_ms, 2),
                "enrichment_error": str(exc),
                "offline_fallback": True
            },
            "errors": [f"Enrichment error — using offline fallback: {exc}"],
        }
