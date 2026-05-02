# 🧠 CV AI Evaluation System

Hệ thống đánh giá CV thông minh sử dụng kiến trúc Multi-Agent trên nền tảng LangGraph. Dự án kết hợp sức mạnh của Gemini API (LLM) và Tavily API (Search/RAG) để cung cấp những phân tích sâu sắc, khách quan và thực tế cho hồ sơ ứng tuyển.

## 🎯 Mục tiêu
- **Đánh giá đa chiều**: Tự động phân tích các thành phần của CV (Kinh nghiệm, Dự án, Kỹ năng, Học vấn).
- **Phân tích theo JD**: So khớp hồ sơ với mô tả công việc (Job Description) để tính toán độ phù hợp.
- **Báo cáo chuyên nghiệp**: Xuất kết quả dưới dạng JSON và Report HTML/PDF.
- **Tương tác trực tiếp**: Hỗ trợ Chatbot để giải đáp các thắc mắc về điểm số và cách cải thiện CV.

## ⚙️ Công nghệ chính
- **Backend**: FastAPI
- **AI Orchestration**: LangGraph (LangChain)
- **LLM APIs**: Google Gemini API (`gemini-1.5-flash`, `gemini-1.5-pro`)
- **Retrieval & Search**: Tavily API (Enrichment/Light RAG)
- **PDF Processing**: PyMuPDF4LLM
- **Reporting**: WeasyPrint

## 🔁 Luồng xử lý (AI Pipeline)
Hệ thống vận hành theo một đồ thị trạng thái (StateGraph) gồm các bước:
1. **PDF Processing**: Trích xuất text từ CV/JD và chuẩn hóa dữ liệu.
2. **Enrichment (Tavily)**: Tìm kiếm thông tin thị trường và tiêu chuẩn ngành liên quan đến kỹ năng của ứng viên.
3. **Multi-Agent Evaluation**: Các agent riêng biệt đánh giá từng phần (Experience, Projects, Skills, Education).
4. **Meta Evaluation**: Agent "Trưởng phòng nhân sự" tổng hợp kết quả, loại bỏ bias và đưa ra kết luận cuối cùng.
5. **Output Generation**: Tổng hợp dữ liệu thành báo cáo HTML và JSON.

## 🏗️ Cấu trúc dự án
```text
backend/
├── app/
│   ├── main.py         # FastAPI entry point
│   ├── api/            # API endpoints (v1/v2)
│   ├── core/           # Cấu hình & Constants
│   ├── services/       # Logic nghiệp vụ
│   │   └── ai/         # Core logic điều phối AI (LangGraph)
│   │       ├── graph.py
│   │       ├── nodes/
│   │       └── prompts/
│   ├── schemas/        # Pydantic models (Request/Response)
│   └── utils/          # Tiện ích bổ trợ
├── tests/              # Scripts kiểm tra & Unit tests
├── scripts/            # Scripts bảo trì hệ thống
└── requirements.txt    # Danh sách thư viện

data/
├── samples/            # CV/JD mẫu dùng để test
└── output/             # Kết quả báo cáo (HTML/JSON) xuất ra

docs/                   # Tài liệu thiết kế & Kiến trúc
notebooks/              # Jupyter Notebooks nghiên cứu AI
```

## 🚀 Cài đặt & Sử dụng

### 1. Cài đặt môi trường
Yêu cầu Python 3.9+.
```bash
cd backend
pip install -r requirements.txt
```

### 2. Cấu hình Biến môi trường
Cập nhật file `.env` ở thư mục gốc:
```env
GEMINI_API=your_gemini_api_key
TAVILY_API=your_tavily_api_key
```

### 3. Kiểm tra hệ thống
Để chạy thử nghiệm toàn bộ pipeline với một file PDF mẫu:
```bash
$env:PYTHONPATH = "backend"
python backend/tests/test_graph.py
```
Kết quả sẽ được lưu tại `data/output/report_output.html`.

## 📄 Output mong muốn
- **JSON**: Toàn bộ điểm số và feedback chi tiết để tích hợp API.
- **HTML Report**: Giao diện trực quan, liệt kê điểm mạnh (Strengths) và các điểm cần cải thiện (Weaknesses).
- **Reasoning**: Giải thích rõ ràng tại sao ứng viên đạt được mức điểm đó dựa trên tiêu chuẩn ngành.

---
*Dự án đang trong giai đoạn hoàn thiện AI Core.*