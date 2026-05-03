# CV AI Evaluation System

Hệ thống đánh giá CV sử dụng pipeline AI đa tác tử trên LangGraph. Ba evaluator chuyên biệt chạy song song, mỗi evaluator tự đánh giá mức độ tin cậy (confidence 1–5), kết quả được kiểm tra chéo bởi Validator trước khi đưa ra kết luận cuối cùng.

Pipeline xử lý 1 CV trong khoảng 20–25 giây, bao gồm: trích xuất PDF → profiling → enrichment thị trường → **3 đánh giá song song** → kiểm tra nhất quán → tổng hợp meta → xuất báo cáo HTML.

---

## Tính năng chính

| Tính năng | Mô tả |
|:---|:---|
| **Parallel Evaluation** | Phase 2, 3, 4 chạy đồng thời qua LangGraph fan-out/fan-in |
| **Confidence Scoring** | Mỗi đánh giá kèm mức tin cậy 1–5 và chain-of-thought reasoning |
| **Cross-phase Validation** | Validator phát hiện bất thường giữa các phase (điểm chênh lệch, perfect score, zero-with-high-confidence) |
| **JD Matching** | So khớp CV với Job Description — skill gap analysis (matched / missing / bonus skills) |
| **Retry Policy** | 3 lần retry với exponential backoff cho lỗi tạm thời (timeout, rate limit, 503) |
| **Dynamic Rubric** | Tiêu chí đánh giá tự điều chỉnh theo level ứng viên (Intern → Senior) |
| **RAG Enrichment** | Tavily search bổ sung context thị trường vào Phase 3 |
| **Structured Logging** | Correlation ID theo dõi toàn bộ pipeline, log JSON cho từng node |

---

## Kiến trúc Pipeline

```
pdf_processor → profiler → enrichment ─┬→ phase2_eval ─┐
                                        ├→ phase3_eval ─┤→ validator → [jd_analyzer?] → meta_evaluator → output
                                        └→ phase4_eval ─┘
```

**6 giai đoạn:**

1. **PDF Processing** — Trích xuất text từ PDF bằng PyMuPDF4LLM, chuẩn hóa artifact/whitespace/date, tách sections theo heading tiếng Anh + Việt.
2. **Profiler** — LLM xác định tên, level (Intern→Senior), ngành nghề, sinh ra dynamic rubric cho các evaluator.
3. **Enrichment** — Tavily search thông tin thị trường liên quan đến skills và level của ứng viên. Kết quả được inject vào Phase 3.
4. **Parallel Evaluation** — 3 evaluator chạy đồng thời:
   - **Phase 2** (60đ): Format & ATS, nền tảng chuyên nghiệp, chất lượng nội dung
   - **Phase 3** (30đ): Kinh nghiệm, minh chứng kỹ thuật, chất lượng dự án + đánh giá xu hướng công nghệ
   - **Phase 4** (10đ): Lãnh đạo, kinh nghiệm quốc tế, giải thưởng
5. **Validator** — Kiểm tra nhất quán giữa các phase (logic thuần, không dùng LLM). Phát hiện anomaly và đề xuất điều chỉnh dựa trên confidence.
6. **Meta Evaluator** — Tổng hợp điểm cuối cùng, xem xét confidence của từng phase + kết quả validation + JD analysis (nếu có).

---

## Cấu trúc dự án

```
backend/
├── app/
│   ├── main.py                          # FastAPI entry point (file validation, CORS, health check)
│   ├── core/
│   │   ├── config.py                    # Pydantic Settings — typed env config
│   │   └── logging_config.py            # Structured logging + correlation ID
│   ├── services/
│   │   └── ai/
│   │       ├── graph.py                 # LangGraph StateGraph — parallel edges + retry policies
│   │       ├── state.py                 # AgentState schema — Annotated reducers cho fan-in
│   │       ├── nodes/
│   │       │   ├── pdf_processor.py     # PDF extraction + cleaning + section parsing
│   │       │   ├── profiler.py          # Candidate level detection + dynamic rubric
│   │       │   ├── enrichment.py        # Tavily RAG — market context
│   │       │   ├── evaluators.py        # Phase 2, 3, 4 evaluation nodes
│   │       │   ├── validator.py         # Cross-phase consistency checker
│   │       │   ├── jd_analyzer.py       # JD matching + skill gap analysis
│   │       │   ├── meta_evaluator.py    # Final score aggregation
│   │       │   └── output_generator.py  # HTML report generation
│   │       ├── prompts/
│   │       │   └── evaluator_prompts.py # Vietnamese-localized prompts + confidence instructions
│   │       └── helpers/
│   │           ├── llm_factory.py       # LLM factory (Gemini/HuggingFace) + error classification
│   │           └── cleaner.py           # CVTextCleaner — artifact removal, normalization
│   ├── api/                             # API router (v1)
│   ├── schemas/                         # Pydantic request/response models
│   └── utils/
├── tests/
│   ├── conftest.py                      # Pytest config + env loading
│   ├── run_ai_test.py                   # Full pipeline test with streaming output
│   ├── test_graph.py                    # Legacy graph test
│   └── unit/
│       ├── test_cleaner.py              # 16 tests — text cleaning logic
│       ├── test_pdf_processor.py        # 9 tests — section parsing + file validation
│       └── test_validator.py            # 16 tests — anomaly detection + confidence adjustment
├── scripts/
│   └── list_models.py
└── requirements.txt

data/
├── samples/                             # CV PDF mẫu
└── output/                              # Kết quả: report_output.html, test_results.json

docs/
└── architecture.md                      # Tài liệu kiến trúc gốc

notebooks/
└── project1_cv_review.ipynb             # Jupyter notebook nghiên cứu ban đầu
```

---

## Công nghệ

| Layer | Stack |
|:---|:---|
| **Backend** | FastAPI 0.100+ |
| **AI Orchestration** | LangGraph ≥0.2 (LangChain ≥0.3) |
| **LLM** | Google Gemini (`gemini-2.5-flash`) hoặc HuggingFace (`Qwen/Qwen2.5-7B-Instruct`) |
| **RAG** | Tavily API |
| **PDF Extraction** | PyMuPDF4LLM |
| **Config** | Pydantic Settings |
| **Testing** | pytest + pytest-cov |
| **Language** | Python 3.10+ |

---

## Cài đặt

### 1. Clone và cài dependencies

```bash
git clone <repo-url>
cd CV-Review-System
pip install -r backend/requirements.txt
```

### 2. Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc:

```env
# === BẮT BUỘC: Chọn 1 trong 2 provider ===

# Option A: Google Gemini (mặc định)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# Option B: HuggingFace Qwen
USE_QWEN=false
HF_TOKEN=your_huggingface_token
HF_MODEL=Qwen/Qwen2.5-7B-Instruct

# === TÙY CHỌN ===

# Tavily — bật enrichment (bỏ trống = skip enrichment)
TAVILY_API=your_tavily_api_key

# Model routing
AI_MODEL_FLASH=gemini-1.5-flash-latest
AI_MODEL_PRO=gemini-2.5-flash

# Pipeline tuning
LLM_TEMPERATURE=0.2
LLM_MAX_RETRIES=3
LLM_RETRY_INITIAL_INTERVAL=2.0
LLM_RETRY_BACKOFF_FACTOR=2.0
PIPELINE_MAX_CONCURRENCY=3

# Server
PORT=3002
CORS_ORIGINS=["http://localhost:3000"]
MAX_UPLOAD_SIZE_MB=10
```

> **Lưu ý:** File `.env` đã nằm trong `.gitignore`. Không bao giờ commit API keys.

### 3. Đặt CV mẫu

Đặt file PDF cần test vào `data/samples/`. Pipeline mặc định tìm file `Nguyen-Thanh-Duy-Tan-Fullstack-Intern.pdf`.

---

## Chạy hệ thống

### Test toàn bộ pipeline

```bash
# Set PYTHONPATH và chạy pipeline test
# PowerShell:
$env:PYTHONPATH = "backend"
python backend/tests/run_ai_test.py

# Bash:
PYTHONPATH=backend python backend/tests/run_ai_test.py
```

Output mẫu:

```
==================================================
[*] STARTING AI CORE PIPELINE v2.0
==================================================
[*] Target CV: Nguyen-Thanh-Duy-Tan-Fullstack-Intern.pdf
[*] Correlation ID: 07721684-722
[*] Features: Parallel Eval | Confidence | Validation
--------------------------------------------------

[+] [PDF_PROCESSOR] completed.
    - Found 4 sections: UNCLASSIFIED, EDUCATION, SKILLS, PROJECTS
    - File size: 74.8KB

[+] [PROFILER] completed.
    - Candidate: Nguyen Thanh Duy Tan
    - Level: Intern
    - Industry: IT

[+] [ENRICHMENT] completed.
    - Results: 5

[+] [PHASE2_EVAL] completed.                          ← 3 phases chạy
    - Score: 16 🟢 (confidence: 4/5)                      đồng thời

[+] [PHASE3_EVAL] completed.
    - Score: 24 🟢 (confidence: 4/5)

[+] [PHASE4_EVAL] completed.
    - Score: 2 🟢 (confidence: 4/5)

[+] [VALIDATOR] completed.
    - Consistent: ⚠️ No
    - ⚠️ Chênh lệch lớn giữa Phase 2 (27%) và Phase 3 (80%). Độ lệch: 53%

[+] [META_EVALUATOR] completed.
    - FINAL SCORE: 44/100 🟢 (confidence: 4/5)

[+] [OUTPUT_GENERATOR] completed.

==================================================
[*] Pipeline completed in 22.65 seconds.
==================================================
```

Kết quả lưu tại:
- `data/output/test_results.json` — JSON đầy đủ (scores, confidence, validation, metadata)
- `data/output/report_output.html` — Báo cáo HTML có confidence badges, validation warnings

### Chạy Unit Tests

```bash
# Chạy toàn bộ 41 tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/unit/ -v

# Chạy với coverage
python -m pytest backend/tests/unit/ -v --cov=backend/app --cov-report=term-missing
```

```
backend/tests/unit/test_cleaner.py         16 passed
backend/tests/unit/test_pdf_processor.py    9 passed
backend/tests/unit/test_validator.py       16 passed
============================= 41 passed in 12.88s =============================
```

### Chạy FastAPI server

```bash
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --port 3002
```

API docs tự động tại `http://localhost:3002/docs`.

---

## API Reference

### `POST /evaluate`

Đánh giá CV, tùy chọn so khớp với Job Description.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|:---|:---|:---:|:---|
| `cv_file` | File (PDF) | ✅ | File CV, tối đa 10MB |
| `jd_text` | string | ❌ | Nội dung Job Description để so khớp |

**Response:**

```json
{
  "success": true,
  "correlation_id": "a1b2c3d4-567",
  "data": {
    "scores": {
      "PHASE2": { "score": 42, "confidence": 4, "reasoning": "...", "details": {...} },
      "PHASE3": { "score": 24, "confidence": 4, "details": {...} },
      "PHASE4": { "score": 5, "confidence": 3, "details": {...} },
      "META":   { "final_score": 71, "confidence": 4, "strengths": [...], "priority_actions": [...] }
    },
    "jd_analysis": {
      "match_score": 75,
      "matched_skills": ["Python", "React", "Docker"],
      "missing_skills": ["Kubernetes", "CI/CD"],
      "bonus_skills": ["TypeScript"],
      "recommendation": "Phù hợp"
    },
    "validation": {
      "is_consistent": true,
      "anomalies": []
    },
    "confidence": { "PHASE2": 4, "PHASE3": 4, "PHASE4": 3 },
    "report": "<html>...</html>"
  },
  "metadata": {
    "duration_s": 22.5,
    "processing": { "correlation_id": "a1b2c3d4-567", "pipeline_version": "2.0.0" }
  },
  "errors": []
}
```

### `GET /health`

Health check endpoint.

```json
{ "status": "healthy", "version": "2.0.0" }
```

---

## Hệ thống đánh giá

### Thang điểm 100

| Phase | Điểm tối đa | Tiêu chí |
|:---|:---:|:---|
| **Phase 2 — Nền tảng** | 60 | Format & ATS (20), Professional Foundation (20), Content Quality (20) |
| **Phase 3 — Chuyên môn** | 30 | Experience Assessment (15), Technical Proof & Portfolio (15) |
| **Phase 4 — Bổ sung** | 10 | Leadership (4), International (3), Awards (3) |

### Confidence Levels

| Level | Ý nghĩa | Hành động |
|:---:|:---|:---|
| 5 | Rất chắc chắn — dữ liệu rõ ràng | Chấp nhận điểm |
| 4 | Chắc chắn | Chấp nhận điểm |
| 3 | Tương đối | Xem xét reasoning |
| 2 | Không chắc chắn | Giảm trọng số phase 15% |
| 1 | Rất không chắc chắn — thiếu dữ liệu | Flag cho human review |

### Validation Rules

Validator (logic thuần, không LLM) kiểm tra:
- Chênh lệch > 30% giữa Phase 2 và Phase 3 → flag anomaly
- Điểm tối đa perfect (60/60, 30/30) → cảnh báo kiểm tra lại
- Score = 0 nhưng confidence ≥ 4 → nghi LLM hiểu sai prompt
- Tổng phase vượt 100 → flag overflow

---

## Error Handling

Pipeline phân biệt 2 loại lỗi:

| Loại | Ví dụ | Xử lý |
|:---|:---|:---|
| **LLMTransientError** | Timeout, rate limit (429), service unavailable (503) | Retry 3 lần, exponential backoff (2s → 4s → 8s) |
| **LLMPermanentError** | Invalid API key, bad request (400), auth failure (401) | Fail ngay, ghi log, trả fallback score |

Retry Policy được gắn trực tiếp vào LangGraph nodes, không phải try/catch thủ công.

---

## Mở rộng

### Thêm LLM provider mới

Mở `backend/app/services/ai/helpers/llm_factory.py`, thêm logic vào `get_llm()`:

```python
if settings.use_new_provider:
    return NewProviderLLM(api_key=settings.new_api_key)
```

### Thêm evaluation phase mới

1. Tạo node mới trong `backend/app/services/ai/nodes/`
2. Thêm prompt vào `evaluator_prompts.py`
3. Đăng ký node + edges trong `graph.py`
4. Cập nhật `PHASE_MAX_SCORES` trong `validator.py`

### Thêm JD parser từ file

Hiện tại JD nhận dạng text. Để hỗ trợ PDF:
1. Sử dụng lại `pdf_processor_node` để extract text từ JD PDF
2. Pass kết quả vào `jd_text` field của initial state

---

## Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|:---|:---|:---|
| `LLMPermanentError: Gemini API Key not found` | Thiếu `GEMINI_API_KEY` trong `.env` | Kiểm tra file `.env` ở thư mục gốc |
| `TAVILY_API_KEY not set — enrichment skipped` | Không có Tavily key | Thêm `TAVILY_API=...` vào `.env` hoặc bỏ qua (non-blocking) |
| `File too large` | PDF > 10MB | Giảm kích thước PDF hoặc tăng `MAX_UPLOAD_SIZE_MB` |
| Phase scores chênh lệch lớn | LLM inconsistency | Validator sẽ flag, Meta Evaluator tự điều chỉnh |
| `LLMTransientError` liên tục | API provider quá tải | Tăng `LLM_MAX_RETRIES` hoặc đổi model |
| Import error khi chạy test | PYTHONPATH chưa set | Chạy `$env:PYTHONPATH = "backend"` trước |

---

## License

Private project — all rights reserved.