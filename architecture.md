📄 CV AI Evaluation System - Specification
🎯 Mục tiêu

Xây dựng một web app có khả năng:

Đánh giá CV bằng hệ thống AI Agents
Sử dụng thang điểm cứng (configurable) từ UI
Có thể:
Đánh giá có hoặc không có Job Description (JD)
Trả về:
JSON kết quả
Report HTML/PDF
Chat tương tác với user
🧠 Agent State (Schema chuẩn)
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
    report_html: str
    chatbot_summary: str
    errors: List[str]
⚙️ Công nghệ chính
Backend: FastAPI
Frontend: ReactJS
AI Orchestration: LangGraph
Retrieval: RAG (Lightweight)
LLM APIs:
Gemini API
Tavily API
🔌 APIs sử dụng
1. Gemini API
Xử lý:
Parsing CV
Evaluation
Reasoning
Chat
2. Tavily API
Dùng để:
Enrich data (GitHub, Portfolio, Social, etc.)
External validation (light RAG)
🔁 Flow Graph (LangGraph Pipeline)
Input
cv_pdf (bắt buộc)
jd_pdf (optional)
🧩 Node 1: PDF Processing Agent

Chức năng:

Đọc file PDF
Extract text
Clean text
Chuẩn hóa thành JSON theo sections

Output:

{
  "sections": {
    "personal_info": "...",
    "experience": "...",
    "projects": "...",
    "skills": "...",
    ...
  }
}
🌐 Node 2: Enrichment Agent (Tavily Tool)

Chức năng:

Tìm kiếm thông tin bổ sung:
GitHub
Portfolio
Company info
Enrich context (Light RAG)
📊 Node 3 → N: Section Evaluation Agents

Mỗi section có 1 AI Agent riêng:

Experience Agent
Project Agent
Skills Agent
Education Agent
etc.

Đặc điểm:

Có system prompt riêng
Có:
Scoring logic
Feedback
Có cơ chế:
Retry nếu lỗi
Validation output format
🧠 Critical Node (Meta Evaluation)

Chức năng:

Kiểm tra lại toàn bộ scoring:
Có bias không?
Có inconsistent không?
Re-evaluate nếu cần
📦 Output Node

Trả về:

JSON hoàn chỉnh (không lỗi)
HTML report
Có thể convert sang PDF
💬 Chat Agent (Final Node)

Chức năng:

Cho phép user hỏi:
Vì sao bị chấm điểm thấp?
So sánh với JD
Cách cải thiện CV
📡 Realtime UX

Trong suốt quá trình pipeline:

Mỗi node sẽ emit:
summary
UI hiển thị:
"Đang xử lý bước X..."
🏗️ Cấu trúc project
backend/
│
├── app/
│   ├── main.py (FastAPI entry)
│   ├── api/
│   ├── schemas/
│
├── core/ai/
│   ├── nodes/
│   ├── prompts/
│   ├── helpers/
│   ├── graph.py
│
├── services/
│
└── config/

frontend/
│
├── src/
│   ├── pages/
│   ├── components/
│   ├── hooks/
│   ├── services/
│
└── public/
🤖 Model sử dụng

Hiện tại dùng 2 model:

Gemini API
Model nội bộ (giống trong file notebook)

Tham khảo: project1_cv_review.ipynb

📄 Output mong muốn

Kết quả cuối cùng:

Tương tự report mẫu PDF bạn cung cấp
Nhưng nâng cấp:
UI đẹp hơn
Insight sâu hơn
Có reasoning rõ ràng
Có interactive chat