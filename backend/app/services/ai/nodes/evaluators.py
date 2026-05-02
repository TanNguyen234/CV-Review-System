import os
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import get_llm, invoke_structured
from app.services.ai.prompts.evaluator_prompts import (
    EXPERIENCE_PROMPT, PROJECT_PROMPT, SKILL_PROMPT, EDUCATION_PROMPT
)

class EvaluationResult(BaseModel):
    """Schema for individual section evaluation results."""
    score: int = Field(description="The score assigned to the section (0-20 or 0-10)")
    feedback: str = Field(description="Detailed feedback and reasoning for the score")

def _evaluate_section(state: AgentState, section_name: str, prompt: str) -> dict:
    """
    Generic function to evaluate a specific section using Gemini.
    """
    errors = state.get("errors", [])
    scores = state.get("scores", {})
    if scores is None: scores = {}
        
    section_text = state.get("sections", {}).get(section_name, "")
        
    if not section_text:
        scores[section_name] = {"score": 0, "feedback": f"Section '{section_name}' not found in CV."}
        return {"scores": scores, "errors": errors}
        
    try:
        llm = get_llm()
        
        dynamic_rubric = state.get("dynamic_rubric", "Use standard criteria.")
        formatted_prompt = prompt.format(dynamic_rubric=dynamic_rubric)
        
        messages = [
            SystemMessage(content=formatted_prompt),
            HumanMessage(content=f"Please evaluate the following section:\n{section_text}")
        ]
        result = invoke_structured(llm, EvaluationResult, messages)
        scores[section_name] = {"score": result.score, "feedback": result.feedback}
    except Exception as e:
        errors.append(f"Evaluator error ({section_name}): {str(e)}")
        scores[section_name] = {"score": 0, "feedback": "Evaluation failed due to system error."}
        
    return {"scores": scores, "errors": errors}

def experience_evaluator_node(state: AgentState) -> dict:
    """Evaluates the EXPERIENCE section."""
    return _evaluate_section(state, "EXPERIENCE", EXPERIENCE_PROMPT)

def project_evaluator_node(state: AgentState) -> dict:
    """Evaluates the PROJECTS section."""
    return _evaluate_section(state, "PROJECTS", PROJECT_PROMPT)

def skill_evaluator_node(state: AgentState) -> dict:
    """Evaluates the SKILLS section."""
    return _evaluate_section(state, "SKILLS", SKILL_PROMPT)

def education_evaluator_node(state: AgentState) -> dict:
    """Evaluates the EDUCATION section."""
    return _evaluate_section(state, "EDUCATION", EDUCATION_PROMPT)
