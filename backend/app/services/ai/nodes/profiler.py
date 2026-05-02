import os
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import get_llm, invoke_structured

PROFILER_PROMPT = """
You are an expert tech recruiter. Your job is to analyze the candidate's CV text and determine their seniority level.
Categorize them as exactly one of: "Intern", "Fresher", "Junior", "Mid-level", or "Senior".

Then, provide a short dynamic scoring rubric (2-3 sentences) that evaluators should follow for this specific level.
For example, if Intern/Fresher, explicitly state: "Candidate is entry-level. Lack of professional experience is expected and should NOT be penalized with a 0 score. Weight personal/academic projects and potential heavily."
If Senior, explicitly state: "Candidate is experienced. Demand high impact, leadership, system design skills, and clear progression in their experience section."
"""

class ProfilerResult(BaseModel):
    level: str = Field(description="The detected seniority level (Intern, Fresher, Junior, Mid-level, Senior).")
    dynamic_rubric: str = Field(description="The specific scoring instructions for evaluators based on this level.")

def profiler_node(state: AgentState) -> dict:
    """
    Analyzes the CV to determine candidate level and dynamically adjust evaluation rubrics.
    """
    errors = state.get("errors", [])
    cleaned_text = state.get("cleaned_text", "")
    
    if not cleaned_text:
        errors.append("Profiler: No cleaned text available.")
        return {"candidate_level": "Unknown", "dynamic_rubric": "Use standard evaluation criteria.", "errors": errors}
        
    try:
        llm = get_llm()
        
        messages = [
            SystemMessage(content=PROFILER_PROMPT),
            HumanMessage(content=f"Analyze this CV:\n{cleaned_text[:3000]}") # First 3000 chars is usually enough to gauge level
        ]
        
        result = invoke_structured(llm, ProfilerResult, messages)
        
        return {
            "candidate_level": result.level,
            "dynamic_rubric": result.dynamic_rubric,
            "errors": errors
        }
    except Exception as e:
        errors.append(f"Profiler error: {str(e)}")
        return {
            "candidate_level": "Unknown", 
            "dynamic_rubric": "Use standard strict evaluation criteria.", 
            "errors": errors
        }
