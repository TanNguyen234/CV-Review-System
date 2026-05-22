"""
AI Pipeline State Schema.
Defines the shared state flowing through all LangGraph nodes.
Uses Annotated reducers for parallel fan-in support.
"""

import operator
from typing import TypedDict, Sequence, Dict, List, Annotated, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def merge_scores(existing: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Custom reducer for merging score dictionaries from parallel evaluator nodes.
    Handles fan-in from Phase 2, 3, 4 running concurrently.
    """
    if existing is None:
        return update
    if update is None:
        return existing
    merged = dict(existing)
    merged.update(update)
    return merged


def merge_dicts(existing: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Generic dict merger for parallel state updates."""
    if existing is None:
        return update or {}
    if update is None:
        return existing
    merged = dict(existing)
    merged.update(update)
    return merged


class PhaseScoreDetail(TypedDict, total=False):
    """Typed schema for individual phase sub-score details."""
    score: int
    feedback: str
    confidence: int  # 1-5 confidence level
    examples: List[str]
    suggestions: List[str]
    improved_bullets: List[str]
    era_evaluation: str
    relevance_score: int


class PhaseScore(TypedDict, total=False):
    """Typed schema for a complete phase evaluation result."""
    score: int
    details: Dict[str, PhaseScoreDetail]
    feedback: str
    confidence: int  # 1-5 overall phase confidence
    reasoning: str  # Chain-of-thought reasoning


class MetaScore(TypedDict, total=False):
    """Typed schema for meta-evaluation results."""
    final_score: int
    strengths: List[str]
    priority_actions: List[str]
    general_advice: List[str]
    industry_standards: str
    industry_keywords: List[str]
    summary: str
    confidence: int
    score_adjustments: Dict[str, int]  # Any adjustments made by meta


class InterviewQuestion(TypedDict, total=False):
    """Typed schema for tailored interview questions."""
    question: str
    intent: str
    expected_answer: str


class MarketInsight(TypedDict, total=False):
    """Typed schema for enriched market context."""
    salary_range: str
    market_demand: str
    trending_skills: List[str]
    standard_requirements: str


class JDAnalysis(TypedDict, total=False):
    """Typed schema for Job Description analysis results."""
    match_score: int  # 0-100 overall match
    matched_skills: List[str]
    missing_skills: List[str]
    bonus_skills: List[str]
    role_alignment: str
    experience_gap: str
    recommendation: str
    interview_questions: List[InterviewQuestion]


class TechDomain(TypedDict, total=False):
    """Typed schema for a technology domain."""
    domain_name: str
    skills: List[str]
    assessment: str


class TechStackAnalysis(TypedDict, total=False):
    """Typed schema for Tech Stack evaluation results."""
    core_competency: str
    domains: List[TechDomain]
    overall_tech_assessment: str


class SoftSkill(TypedDict, total=False):
    """Typed schema for an individual soft skill."""
    skill_name: str
    evidence: str
    strength_level: str


class SoftSkillsAnalysis(TypedDict, total=False):
    """Typed schema for Soft Skills evaluation results."""
    skills: List[SoftSkill]
    culture_fit_prediction: str


class ProcessingMetadata(TypedDict, total=False):
    """Metadata about the pipeline processing run."""
    correlation_id: str
    start_time: str
    end_time: str
    total_duration_s: float
    node_durations: Dict[str, float]
    model_used: str
    cv_filename: str
    cv_file_size_bytes: int
    pipeline_version: str


class ValidationResult(TypedDict, total=False):
    """Results from the cross-phase validation node."""
    is_consistent: bool
    anomalies: List[str]
    adjustments: Dict[str, int]
    validation_notes: str


class AgentState(TypedDict, total=False):
    """
    Complete pipeline state schema.
    Uses Annotated reducers for fields that receive parallel updates.
    """
    # --- Message History ---
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # --- PDF Processing ---
    raw_text: str  # Input: file path or raw text
    cleaned_text: str
    sections: Dict[str, str]

    # --- Profiling ---
    candidate_name: str
    candidate_level: str
    industry: str
    dynamic_rubric: str
    years_of_experience: float

    # --- Enrichment ---
    text_insights: Annotated[Dict[str, Any], merge_dicts]
    market_insight: Optional[MarketInsight]

    # --- Evaluation Scores (parallel-safe merge) ---
    scores: Annotated[Dict[str, Any], merge_scores]

    # --- Confidence Tracking ---
    confidence_scores: Annotated[Dict[str, int], merge_dicts]

    # --- JD Matching (optional) ---
    jd_text: str  # Raw JD text, empty if not provided
    jd_analysis: Optional[JDAnalysis]

    # --- Validation ---
    validation_result: Optional[ValidationResult]

    # --- Output ---
    report_lang: str  # Language for report output: "vi" or "en"
    report_html: str
    chatbot_summary: str

    # --- Metadata ---
    processing_metadata: Annotated[Dict[str, Any], merge_dicts]

    # --- Error Tracking (append-safe) ---
    errors: Annotated[List[str], operator.add]
