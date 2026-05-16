---
title: AI CV Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# CV AI Evaluation System

A professional full-stack CV evaluation system using a multi-agent AI pipeline on LangGraph, FastAPI backend, and a modern Glassmorphism Web UI.

The system automatically extracts content from PDF files, performs candidate profiling, data enrichment, parallel professional assessments, consistency checks, and renders detailed analysis reports in real-time via Server-Sent Events (SSE) streaming.

---

## Key Features

| Feature | Description |
|:---|:---|
| **Modern Web UI** | Sleek Glassmorphism interface at `/app`, supporting real-time agent progress tracking. |
| **Hybrid LLM Support** | Flexible integration of **Google Gemini** and **HuggingFace (Qwen)** via Factory Pattern. Easily configurable via environment variables. |
| **Real-time Streaming** | Uses Server-Sent Events (SSE) to stream live updates from LangGraph directly to the user interface. |
| **Smart Security Layer** | Integrated anti-bot mechanism (5 requests/day limit) and AI Spam Validation to filter invalid files early in the funnel. |
| **Optimized Storage** | All CV data (Base64) and analysis results are stored centrally in **MongoDB**, removing dependencies on third-party storage services. |
| **Parallel Evaluation** | Assessment phases (Foundational, Professional, Project) run concurrently to optimize processing speed. |
| **Comprehensive Test Suite** | Includes Unit Tests for security logic and Integration Tests for API Endpoints. |

---

## System Architecture & Pipeline

### Backend Workflow
```
Client (Web UI) → POST /api/v1/jobs/submit (Spam Check + Rate Limit) → MongoDB (Base64 Storage)
Client (Web UI) → GET /api/v1/jobs/stream/{job_id} → SSE Streaming LangGraph Updates
```

### AI Agent Pipeline (LangGraph)
```
pdf_processor → profiler → enrichment ─┬→ phase2_eval (Foundational) ─┐
                                         ├→ phase3_eval (Professional) ─┤→ validator → meta_evaluator → output
                                         └→ phase4_eval (Project-based) ─┘
```

**6 AI Processing Phases:**
1. **PDF Processing**: Text extraction, normalization, and CV segmenting.
2. **Profiler**: Determines seniority level and generates a dynamic evaluation rubric.
3. **Enrichment**: Uses RAG (Tavily search) to fetch real-world market context.
4. **Parallel Evaluation**: 3 independent agents concurrently evaluate different candidate aspects.
5. **Validator**: Checks logic and consistency across evaluation results.
6. **Meta Evaluator & Output**: Aggregates final data and renders an in-depth report.

---

## Directory Structure

```
backend/
├── app/
│   ├── api/v1/jobs.py       # Job management & SSE Stream API
│   ├── core/                # Configuration, DB connection (Motor), Logging
│   ├── services/
│   │   ├── security.py      # Spam filter & Rate Limiter
│   │   └── ai/              # LangGraph orchestration & Nodes
│   ├── schemas/db.py        # MongoDB Models (Pydantic)
│   ├── static/ & templates/ # Web UI assets (index.html, CSS)
│   └── main.py              # FastAPI entry point
├── tests/
│   ├── integration/         # API integration tests
│   ├── unit/                # Security and core logic unit tests
│   └── conftest.py          # Pytest configuration & Mocks
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables (Manual setup required)
```

---

## Technology Stack

- **Backend Framework**: FastAPI, LangGraph, LangChain.
- **LLM Models**: Google Gemini (1.5/2.5 Flash), HuggingFace (Qwen 2.5).
- **Database**: MongoDB Atlas (Async Motor).
- **Processing**: PyMuPDF4LLM, Pydantic v2.
- **Frontend**: Vanilla JS, Glassmorphism CSS.
- **Testing**: Pytest, Pytest-asyncio, Mongomock.

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration (.env)

Create a `.env` file in the `backend/` directory or project root with the following:

```env
# AI Models
USE_QWEN=true
HF_TOKEN=your_huggingface_token
GEMINI_API_KEY=your_gemini_key

# RAG & Database
TAVILY_API=your_tavily_key
MONGO_URL=your_mongodb_connection_url

# Server Settings
PORT=3002
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3002"]
```

### 3. Run the System

```bash
# Set PYTHONPATH (Windows PowerShell)
$env:PYTHONPATH = "backend"

# Run server with Uvicorn
python backend/app/main.py
```
Access the UI at: **[http://localhost:3002/app](http://localhost:3002/app)**

---

## Testing

The system includes an automated test suite to ensure API reliability and security logic.

```bash
cd backend
python -m pytest tests/ -v
```

---

## Security & Performance

1. **Anti-bot**: Limits to **5 requests/day per IP** via MongoDB tracking.
2. **AI Validation**: Uses Gemini Flash to verify uploaded files are actually CVs before running the full pipeline, saving tokens/costs.
3. **Storage Efficiency**: CVs are stored directly as Base64 in MongoDB, reducing latency and reliance on external file storage services.

---
*Private project — all rights reserved.*