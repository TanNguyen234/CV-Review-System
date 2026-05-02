import os
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.ai.state import AgentState
from app.services.ai.helpers.llm_factory import get_pro_llm, invoke_structured
from app.services.ai.prompts.evaluator_prompts import META_PROMPT

class MetaEvaluationResult(BaseModel):
    final_score: int = Field(description="Total score out of 100 based on the sum of section scores.")
    strengths: List[str] = Field(description="Top 3 strengths of the candidate.")
    weaknesses: List[str] = Field(description="Top 3 areas for improvement.")
    summary: str = Field(description="A comprehensive summary paragraph evaluating the candidate's profile.")

def meta_evaluator_node(state: AgentState) -> dict:
    """
    Aggregates section scores and provides a final verdict.
    """
    scores = state.get("scores", {})
    errors = state.get("errors", [])
    
    # Calculate sum of scores
    total_score = sum([s.get("score", 0) for s in scores.values()])
    
    try:
        llm = get_pro_llm()
        
        messages = [
            SystemMessage(content=META_PROMPT),
            HumanMessage(content=f"Here are the section scores and feedback:\n{scores}\n\nCandidate Level Context:\n{state.get('dynamic_rubric', '')}")
        ]
        
        result = invoke_structured(llm, MetaEvaluationResult, messages)
        
        scores["META"] = {
            "final_score": result.final_score,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "summary": result.summary
        }
        
    except Exception as e:
        errors.append(f"Meta Evaluator error: {str(e)}")
        scores["META"] = {"final_score": 0, "error": "Final aggregation failed."}
        
    return {"scores": scores, "errors": errors}
