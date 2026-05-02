from langgraph.graph import StateGraph, END
from app.services.ai.state import AgentState
from app.services.ai.nodes.pdf_processor import pdf_processor_node
from app.services.ai.nodes.profiler import profiler_node
from app.services.ai.nodes.enrichment import enrichment_node
from app.services.ai.nodes.evaluators import (
    experience_evaluator_node,
    project_evaluator_node,
    skill_evaluator_node,
    education_evaluator_node
)
from app.services.ai.nodes.meta_evaluator import meta_evaluator_node
from app.services.ai.nodes.output_generator import output_generator_node

def create_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("pdf_processor", pdf_processor_node)
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("enrichment", enrichment_node)
    
    workflow.add_node("experience_eval", experience_evaluator_node)
    workflow.add_node("project_eval", project_evaluator_node)
    workflow.add_node("skill_eval", skill_evaluator_node)
    workflow.add_node("education_eval", education_evaluator_node)
    
    workflow.add_node("meta_evaluator", meta_evaluator_node)
    workflow.add_node("output_generator", output_generator_node)

    # Add Edges (Sequential to avoid LangGraph fan-in duplicate execution issues)
    workflow.set_entry_point("pdf_processor")
    workflow.add_edge("pdf_processor", "profiler")
    workflow.add_edge("profiler", "enrichment")
    workflow.add_edge("enrichment", "experience_eval")
    workflow.add_edge("experience_eval", "project_eval")
    workflow.add_edge("project_eval", "skill_eval")
    workflow.add_edge("skill_eval", "education_eval")
    workflow.add_edge("education_eval", "meta_evaluator")
    
    # Finalize
    workflow.add_edge("meta_evaluator", "output_generator")
    workflow.add_edge("output_generator", END)

    # Compile Graph
    app = workflow.compile()
    return app

# Singleton compiled graph
cv_graph = create_graph()
