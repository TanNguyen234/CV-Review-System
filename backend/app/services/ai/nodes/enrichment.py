import os
from tavily import TavilyClient
from app.services.ai.state import AgentState

def get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY", os.getenv("TAVILY_API", ""))
    return TavilyClient(api_key=api_key)

def _build_query(sections: dict) -> str:
    # Try to find skills section
    skills = sections.get("SKILLS", sections.get("AREAS OF EXPERTISE", ""))
    target_role = "IT Professional" # Default fallback
    
    # Try to extract role from objective/summary if available
    objective = sections.get("OBJECTIVE", sections.get("SUMMARY", ""))
    if objective:
        target_role = objective[:50] # Take first 50 chars as a hint
    
    # Take first 100 characters of skills to keep query short
    skill_text = skills[:100] if skills else ""
    parts = [target_role, skill_text, "industry standards and expectations"]
    return " ".join([part for part in parts if part]).strip()

def enrichment_node(state: AgentState) -> dict:
    errors = state.get("errors", [])
    api_key = os.getenv("TAVILY_API_KEY", os.getenv("TAVILY_API", ""))

    if not api_key:
        errors.append("TAVILY_API_KEY not set")
        return {"errors": errors}

    sections = state.get("sections", {})
    query = _build_query(sections)
    if not query:
        return {"errors": errors}

    try:
        client = get_tavily_client()
        results = client.search(query, max_results=3)
        
        text_insights = state.get("text_insights", {})
        if text_insights is None:
            text_insights = {}
            
        text_insights["rag_context"] = results
        
        return {
            "text_insights": text_insights,
            "errors": errors
        }
    except Exception as exc:
        errors.append(f"rag_enricher error: {exc}")
        return {"errors": errors}
