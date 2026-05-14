# CV AI Evaluation System

Hệ thống đánh giá CV full-stack chuyên nghiệp sử dụng pipeline AI đa tác tử trên LangGraph, FastAPI backend, và giao diện Web UI Glassmorphism hiện đại.

Hệ thống tự động trích xuất PDF, profiling, làm giàu dữ liệu, đánh giá song song, kiểm tra nhất quán, và render báo cáo phân tích theo thời gian thực (Real-time SSE Streaming).

---

## 🌟 Tính năng Nổi bật

| Tính năng | Mô tả |
|:---|:---|
| **Web UI Hiện đại** | Giao diện Glassmorphism tuyệt đẹp tại `/app`, hỗ trợ theo dõi tiến trình Agent theo thời gian thực. |
| **Hybrid LLM Support** | Hỗ trợ cả **Google Gemini** và **HuggingFace (Qwen)** thông qua Factory Pattern. Cấu hình linh hoạt qua biến môi trường. |
| **Real-time Streaming** | Sử dụng Server-Sent Events (SSE) để truyền tải cập nhật từ LangGraph trực tiếp lên giao diện người dùng. |
| **Security Layer** | Tích hợp Anti-bot (Rate Limit 5 yêu cầu/ngày) và AI Spam Validation để loại bỏ tệp rác ngay từ đầu phễu. |
| **Lưu trữ Trực tiếp** | Toàn bộ dữ liệu CV (Base64) và kết quả phân tích được lưu trữ tập trung trong **MongoDB**, loại bỏ phụ thuộc vào các dịch vụ lưu trữ bên thứ ba như Cloudinary. |
| **Parallel Evaluation** | Các pha đánh giá (Nền tảng, Chuyên môn, Dự án) chạy đồng thời để tối ưu tốc độ xử lý. |
| **Pytest Suite** | Hệ thống kiểm thử tự động toàn diện bao gồm Unit Tests (Security) và Integration Tests (API Endpoints). |

---

## 🏗️ Kiến trúc Pipeline & Hệ thống

### Backend Layer
```
Client (Web UI) → POST /submit (Spam Check + Rate Limit) → MongoDB (Base64 Storage)
Client (Web UI) → GET /stream/{job_id} → SSE Streaming LangGraph Updates
```

### AI Agent Pipeline
```
pdf_processor → profiler → enrichment ─┬→ phase2_eval ─┐
                                        ├→ phase3_eval ─┤→ validator → [jd_analyzer?] → meta_evaluator → output
                                        └→ phase4_eval ─┘
```

**6 giai đoạn AI:**
1. **PDF Processing** — Trích xuất text, chuẩn hóa và tách phân đoạn CV.
2. **Profiler** — Xác định level và sinh dynamic rubric cho các evaluator.
3. **Enrichment** — RAG (Tavily search) lấy bối cảnh thị trường thực tế.
4. **Parallel Evaluation** — 3 evaluator độc lập chạy song song đánh giá các khía cạnh khác nhau.
5. **Validator** — Kiểm tra logic và sự nhất quán giữa các pha đánh giá.
6. **Meta Evaluator & Output** — Tổng hợp dữ liệu và render báo cáo HTML/PDF.

---

## 📂 Cấu trúc dự án

```
backend/
├── app/
│   ├── api/v1/jobs.py       # API routes (Submit & SSE Stream)
│   ├── core/                # Config, DB (Motor), Logging
│   ├── services/
│   │   ├── security.py      # Rate Limiter & Spam Checker
│   │   └── ai/              # LangGraph Orchestration & Nodes
│   ├── schemas/db.py        # MongoDB Models (Pydantic)
│   ├── static/ & templates/ # Giao diện Web (Glassmorphism)
│   └── main.py              # FastAPI Entry Point
├── tests/
│   ├── integration/         # API Endpoint tests
│   ├── unit/                # Security & Core logic tests
│   └── conftest.py          # Pytest fixtures & mocks
├── requirements.txt
└── .env                     # Configuration
```

---

## 🚀 Công nghệ sử dụng

- **Framework**: FastAPI, LangGraph, LangChain.
- **LLM**: Google Gemini (1.5/2.5 Flash), HuggingFace (Qwen 2.5).
- **Database**: MongoDB Atlas (Async Motor).
- **Processing**: PyMuPDF4LLM, Pydantic v2.
- **Frontend**: Vanilla JS, Glassmorphism CSS.
- **Testing**: Pytest, Pytest-asyncio, Mongomock.

---

## ⚙️ Hướng dẫn Cài đặt

### 1. Cài đặt Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Cấu hình .env

Tạo file `.env` tại thư mục gốc:

```env
# AI Models (Chọn 1 hoặc dùng cả hai)
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

### 3. Chạy hệ thống

```bash
# Set PYTHONPATH
$env:PYTHONPATH = "backend"

# Chạy server
python backend/app/main.py
```
Truy cập: **[http://localhost:3002/app](http://localhost:3002/app)**

---

## 🧪 Kiểm thử (Testing)

Hệ thống đi kèm bộ test tự động để đảm bảo độ tin cậy của API và logic bảo mật.

```bash
# Chạy toàn bộ test suite
cd backend
python -m pytest tests/ -v
```

---

## 🛡️ Bảo mật & Hiệu năng

1. **Anti-bot**: Giới hạn **5 yêu cầu/ngày/IP** thông qua MongoDB tracking.
2. **Zero-Trust AI**: Sử dụng Gemini Flash xác thực tệp upload có phải CV hay không trước khi tốn token chạy pipeline chính.
3. **Storage Efficiency**: CV được lưu trực tiếp dưới dạng Base64 trong MongoDB, giảm độ trễ so với việc upload lên storage bên thứ ba.

---
*Private project — all rights reserved.*