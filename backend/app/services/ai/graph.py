"""
AI Pipeline Graph — LangGraph StateGraph with parallel evaluation and retry policies.

Pipeline Architecture:
    pdf_processor → profiler → enrichment ─┬→ phase2_eval ──────┐
                                            ├→ phase3_eval ──────┤
                                            ├→ phase4_eval ──────┤→ validator → meta_evaluator ─┬→ output_generator
                                            └→ project_evaluator ┘                              │
                                           jd_analyzer (conditional) ───────────────────────────┘
"""

from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy

from app.services.ai.state import AgentState
from app.services.ai.nodes.pdf_processor import pdf_processor_node
from app.services.ai.nodes.profiler import profiler_node
from app.services.ai.nodes.enrichment import enrichment_node
from app.services.ai.nodes.evaluators import (
    phase2_evaluator_node,
    phase3_evaluator_node,
    phase4_evaluator_node,
)
from app.services.ai.nodes.validator import validator_node
from app.services.ai.nodes.jd_analyzer import jd_analyzer_node
from app.services.ai.nodes.project_evaluator import project_evaluator_node
from app.services.ai.nodes.meta_evaluator import meta_evaluator_node
from app.services.ai.nodes.output_generator import output_generator_node
from app.services.ai.helpers.llm_factory import LLMTransientError
from app.core.config import settings


# --- Retry Policy for LLM-calling nodes ---
llm_retry_policy = RetryPolicy(
    max_attempts=settings.llm_max_retries,
    initial_interval=settings.llm_retry_initial_interval,
    backoff_factor=settings.llm_retry_backoff_factor,
    retry_on=(LLMTransientError,),
)


def _should_run_jd_analyzer(state: AgentState) -> str:
    """Conditional edge: route to JD analyzer only if JD text is provided."""
    jd_text = state.get("jd_text", "")
    if jd_text and jd_text.strip():
        return "jd_analyzer"
    return "meta_evaluator"


def create_graph():
    """
    Creates the CV evaluation pipeline graph with:
    - Parallel fan-out for Phase 2, 3, 4 evaluators
    - Retry policies on all LLM-calling nodes
    - Conditional JD matching
    - Cross-phase validation
    """
    workflow = StateGraph(AgentState)

    # === Add Nodes ===

    # Stage 1: Extraction (sequential — each depends on previous)
    workflow.add_node("pdf_processor", pdf_processor_node)
    workflow.add_node(
        "profiler",
        profiler_node,
        retry=llm_retry_policy,
    )
    workflow.add_node("enrichment", enrichment_node)

    # Stage 2: Evaluation (PARALLEL — all 3 phases are independent)
    workflow.add_node(
        "phase2_eval",
        phase2_evaluator_node,
        retry=llm_retry_policy,
    )
    workflow.add_node(
        "phase3_eval",
        phase3_evaluator_node,
        retry=llm_retry_policy,
    )
    workflow.add_node(
        "phase4_eval",
        phase4_evaluator_node,
        retry=llm_retry_policy,
    )

    # Project Evaluator (parallel with other evaluators)
    workflow.add_node(
        "project_evaluator",
        project_evaluator_node,
        retry=llm_retry_policy,
    )

    # Stage 3: Validation (deterministic — no LLM)
    workflow.add_node("validator", validator_node)

    # Stage 4: JD Analysis (conditional)
    workflow.add_node(
        "jd_analyzer",
        jd_analyzer_node,
        retry=llm_retry_policy,
    )

    # Stage 5: Meta Evaluation
    workflow.add_node(
        "meta_evaluator",
        meta_evaluator_node,
        retry=llm_retry_policy,
    )

    # Stage 6: Output
    workflow.add_node("output_generator", output_generator_node)

    # === Add Edges ===

    # Stage 1: Sequential extraction pipeline
    workflow.set_entry_point("pdf_processor")
    workflow.add_edge("pdf_processor", "profiler")
    workflow.add_edge("profiler", "enrichment")

    # Stage 2: PARALLEL FAN-OUT — enrichment feeds all evaluators simultaneously
    workflow.add_edge("enrichment", "phase2_eval")
    workflow.add_edge("enrichment", "phase3_eval")
    workflow.add_edge("enrichment", "phase4_eval")
    workflow.add_edge("enrichment", "project_evaluator")

    # Stage 3: FAN-IN — all evaluators converge to validator
    workflow.add_edge("phase2_eval", "validator")
    workflow.add_edge("phase3_eval", "validator")
    workflow.add_edge("phase4_eval", "validator")
    workflow.add_edge("project_evaluator", "validator")

    # Stage 4: Conditional JD analysis
    workflow.add_conditional_edges(
        "validator",
        _should_run_jd_analyzer,
        {
            "jd_analyzer": "jd_analyzer",
            "meta_evaluator": "meta_evaluator",
        },
    )
    workflow.add_edge("jd_analyzer", "meta_evaluator")

    # Stage 5 → 6: Finalize
    workflow.add_edge("meta_evaluator", "output_generator")
    workflow.add_edge("output_generator", END)

    # Compile with concurrency limit
    app = workflow.compile()
    return app


# Singleton compiled graph
cv_graph = create_graph()
