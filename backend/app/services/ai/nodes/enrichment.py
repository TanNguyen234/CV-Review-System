"""
Enrichment Node — Web search for market context and industry standards.
Uses Tavily API for lightweight RAG enrichment.
"""

import time
from app.services.ai.state import AgentState
from app.core.config import settings
from app.core.logging_config import pipeline_logger


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

    parts.append("hiring standards required skills salary expectations 2025 2026")

    query = " ".join([part for part in parts if part]).strip()
    # Limit query length for API
    return query[:300] if query else ""


def enrichment_node(state: AgentState) -> dict:
    """
    Enriches the pipeline state with market context from web search.
    Results are fed into Phase 3 evaluator for technology relevance assessment.
    """
    start = time.time()
    pipeline_logger.node_start("enrichment")

    api_key = settings.tavily_api_key
    if not api_key:
        pipeline_logger.node_error(
            "enrichment", "TAVILY_API_KEY not set", retryable=False
        )
        return {
            "text_insights": {},
            "processing_metadata": {"enrichment_skipped": True},
            "errors": ["TAVILY_API_KEY not set — enrichment skipped"],
        }

    sections = state.get("sections", {})
    level = state.get("candidate_level", "")
    industry = state.get("industry", "")

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

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "enrichment",
            duration_ms=duration_ms,
        )

        return {
            "text_insights": {"rag_context": results},
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
        return {
            "text_insights": {},
            "processing_metadata": {
                "enrichment_duration_ms": round(duration_ms, 2),
                "enrichment_error": str(exc),
            },
            "errors": [f"Enrichment error (non-blocking): {exc}"],
        }
