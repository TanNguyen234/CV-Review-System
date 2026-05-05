# CV AI Evaluation System

Hệ thống đánh giá CV full-stack chuyên nghiệp sử dụng pipeline AI đa tác tử trên LangGraph, FastAPI backend, và giao diện Web UI Glassmorphism hiện đại.
Hệ thống tự động trích xuất PDF, profiling, làm giàu dữ liệu, đánh giá song song, kiểm tra nhất quán, và render báo cáo phân tích theo thời gian thực (Real-time SSE Streaming).

---

## 🌟 Tính năng Mới & Nổi bật

| Tính năng | Mô tả |
|:---|:---|
| **Web UI Hiện đại** | Giao diện Glassmorphism tuyệt đẹp tại `/app`, tải lên CV và xem AI làm việc theo thời gian thực. |
| **Real-time SSE Streaming** | Theo dõi trực tiếp tiến trình của các Agent trong LangGraph qua giao diện console và progress bar. |
| **Anti-bot & Rate Limiting** | Giới hạn 5 lần đánh giá CV/ngày cho mỗi IP. Được lưu trữ an toàn bằng MongoDB. |
| **AI Spam Validation** | Sử dụng LLM tốc độ cao (Gemini Flash) đọc nhanh trang 1 của PDF để xác định CV là thật hay file rác trước khi đưa vào luồng chính. |
| **Lưu trữ Cloudinary & MongoDB** | Lưu trữ lịch sử đánh giá vào MongoDB (Async Motor) và tự động upload file lên Cloudinary. |
| **Parallel Evaluation** | Phase 2, 3, 4 chạy đồng thời qua LangGraph fan-out/fan-in |
| **Cross-phase Validation** | Validator phát hiện bất thường giữa các phase (điểm chênh lệch, perfect score, zero-with-high-confidence) |
| **JD Matching** | So khớp CV với Job Description — skill gap analysis (matched / missing / bonus skills) |

---

## 🏗️ Kiến trúc Pipeline & Hệ thống

### Backend Layer
```
Client (Web UI) → POST /submit (Spam Check + Rate Limit) → Cloudinary + MongoDB
Client (Web UI) → GET /stream/{job_id} → SSE Streaming LangGraph Updates
```

### AI Agent Pipeline
```
pdf_processor → profiler → enrichment ─┬→ phase2_eval ─┐
                                        ├→ phase3_eval ─┤→ validator → [jd_analyzer?] → meta_evaluator → output
                                        └→ phase4_eval ─┘
```

**6 giai đoạn AI:**
1. **PDF Processing** — Trích xuất text từ PDF, chuẩn hóa, tách sections.
2. **Profiler** — LLM xác định tên, level (Intern→Senior), sinh ra dynamic rubric cho các evaluator.
3. **Enrichment** — RAG (Tavily search) lấy bối cảnh thị trường.
4. **Parallel Evaluation** — 3 evaluator độc lập đánh giá Nền tảng (60đ), Chuyên môn (30đ), Kỹ năng bổ sung (10đ).
5. **Validator** — Kiểm tra logic và sự nhất quán giữa 3 phase.
6. **Meta Evaluator & Output** — Tổng hợp điểm số và tạo mã HTML báo cáo.

---

## 📂 Cấu trúc dự án

```
backend/
├── app/
│   ├── main.py                          # FastAPI entry point, lifespan, mount UI
│   ├── core/
│   │   ├── config.py                    # Cấu hình Pydantic (Env vars)
│   │   ├── database.py                  # Async MongoDB setup (Motor)
│   │   └── logging_config.py            # Log pipeline
│   ├── api/v1/jobs.py                   # API routes: Submit CV và SSE Stream
│   ├── schemas/db.py                    # MongoDB Models (Pydantic)
│   ├── services/
│   │   ├── security.py                  # Anti-bot Rate Limiter & CV Spam Checker
│   │   └── ai/                          # LangGraph đa tác tử
│   ├── static/                          # CSS/JS cho giao diện Web (Glassmorphism)
│   └── templates/                       # HTML (Jinja2) cho giao diện Web
├── requirements.txt
├── data/
└── docs/
```

---

## 🚀 Công nghệ sử dụng

| Layer | Stack |
|:---|:---|
| **Backend** | FastAPI, SSE-Starlette, Motor (MongoDB), Uvicorn |
| **Frontend** | HTML5, Vanilla CSS (Glassmorphism), Vanilla JS (EventSource), html2pdf.js |
| **AI Orchestration** | LangGraph, LangChain |
| **LLM Models** | Google Gemini (`gemini-2.5-flash`), HuggingFace |
| **Storage & DB** | MongoDB Atlas, Cloudinary |
| **PDF Processing** | PyMuPDF4LLM |

---

## ⚙️ Hướng dẫn Cài đặt & Chạy

### 1. Clone và cài dependencies

```bash
git clone <repo-url>
cd CV-Review-System/backend
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường (`.env`)

Tạo file `.env` ở thư mục gốc của project:

```env
# AI Models
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
AI_MODEL_FLASH=gemini-2.5-flash

# RAG
TAVILY_API=your_tavily_key

# Database & Storage (Bắt buộc cho Web UI)
MONGO_URL=mongodb+srv://<user>:<password>@cluster0.mongodb.net/?appName=Cluster0
CLOUD_NAME=your_cloud_name
CLOUD_KEY=your_cloud_key
CLOUD_SECRET=your_cloud_secret

# Server
PORT=3002
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3002"]
MAX_UPLOAD_SIZE_MB=10
```

### 3. Chạy Server và Truy cập Web UI

```bash
# Set PYTHONPATH và chạy backend
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --port 3002
```

👉 Truy cập hệ thống tại: **[http://localhost:3002/app](http://localhost:3002/app)**

---

## 📖 API Reference (Phiên bản mới)

### `POST /api/v1/jobs/submit`
Gửi CV lên hệ thống, chạy spam check, giới hạn rate limit và trả về ID tiến trình.
- **Form-data**: `cv_file` (PDF), `jd_text` (String)
- **Response**: `{"job_id": "uuid...", "message": "Success"}`

### `GET /api/v1/jobs/stream/{job_id}`
Endpoint SSE (Server-Sent Events) để lắng nghe log LangGraph theo thời gian thực.
- **Event**: `status` -> Chứa string log của từng node.
- **Event**: `complete` -> Chứa JSON gồm mã `report_html` và điểm `scores`.

---

## 🛡️ Hệ thống An toàn (Security Layer)
1. **Rate Limiting**: IP của người dùng được lưu vào `rate_limits` collection trong MongoDB. Giới hạn **5 yêu cầu mỗi ngày**.
2. **Spam Validation**: Mọi tệp tải lên sẽ bị trích xuất trang đầu tiên và đẩy qua LLM Gemini Flash. Hệ thống yêu cầu LLM phán đoán tính hợp lệ "IS_CV: YES/NO". Nếu bị gán cờ rác, tệp sẽ bị xóa ngay lập tức trước khi chạy LangGraph.

---

## 🤝 Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|:---|:---|:---|
| `Cannot connect to MongoDB` | Lỗi URL hoặc IP chưa được whitelist | Kiểm tra `MONGO_URL` và Network Access trong MongoDB Atlas |
| `Rate limit exceeded` | Gửi quá 5 lần 1 ngày | Đổi IP, đợi qua ngày mới, hoặc xóa document trong MongoDB |
| `File rejected: Not a CV` | Tải nhầm tệp (ảnh, word, tệp rác) | Đảm bảo file upload có cấu trúc như một Resume thực tế |
| Lỗi CSS/JS không load | Sai đường dẫn tĩnh | Chạy từ thư mục gốc, FastAPI đã mount thư mục `app/static/` |

---
*Private project — all rights reserved.*