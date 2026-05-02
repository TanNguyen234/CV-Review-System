# 🧠 AI Core: CV Evaluation Engine

The AI Core is a standalone Python package that orchestrates a multi-agent evaluation pipeline for Resumes (CVs) using LangGraph and Gemini.

## 📁 Package Structure

- `graph.py`: The central orchestration logic defining the state machine.
- `state.py`: Typed schema for the agent state.
- `nodes/`: Individual processing steps (PDF extraction, LLM evaluation, aggregation).
- `helpers/`: Utility functions (Text cleaning, LLM factory).
- `prompts/`: System instructions for the various AI agents.

## 🚀 Key Features

1.  **Robust Parsing**: Normalizes PDF text and automatically detects sections (Experience, Skills, etc.) using a case-insensitive keyword mapping.
2.  **Market Enrichment**: Uses Tavily neural search to fetch industry-standard benchmarks for the candidate's specific tech stack.
3.  **Modular Agents**: Each section of the CV is evaluated by a dedicated agent with a specialized rubric.
4.  **Bias Correction**: A Meta-Evaluation node reviews section-level results to ensure consistency and assign a final aggregated score.
5.  **Configurable Models**: Supports swapping between `gemini-1.5-flash` and `gemini-1.5-pro` via environment variables.

## ⚙️ Configuration

Set the following in your `.env` or `env.txt`:

- `GOOGLE_API_KEY` (or `GEMINI_API`): Your Google AI API key.
- `TAVILY_API_KEY`: Your Tavily search API key.
- `AI_MODEL_FLASH`: (Optional) Override for evaluation model (default: gemini-1.5-flash).
- `AI_MODEL_PRO`: (Optional) Override for meta-evaluation model (default: gemini-1.5-pro).

## 🛠️ Standalone Usage

```python
from backend.core.ai.graph import cv_graph

initial_state = {
    \"raw_text\": \"path/to/resume.pdf\",
    \"messages\": [],
    \"errors\": []
}

final_state = cv_graph.invoke(initial_state)
print(final_state[\"scores\"][\"META\"][\"final_score\"])
```
