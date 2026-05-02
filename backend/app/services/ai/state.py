from typing import TypedDict, Sequence, Dict, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    raw_text: str
    cleaned_text: str
    sections: Dict[str, str]
    text_insights: Dict[str, object]
    scores: Dict[str, object]
    candidate_level: str
    dynamic_rubric: str
    report_html: str
    chatbot_summary: str
    errors: List[str]
