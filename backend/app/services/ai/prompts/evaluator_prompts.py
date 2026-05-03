"""
Evaluator Prompts — Vietnamese-localized evaluation criteria with confidence scoring.
Each phase prompt requires the LLM to provide reasoning and self-assessed confidence.
"""

PHASE2_PROMPT = """
Bạn là một chuyên gia tối ưu hóa CV và ATS. Nhiệm vụ của bạn là đánh giá phần "Nền tảng cốt lõi" (Core Foundation).

YÊU CẦU QUAN TRỌNG:
- PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT (Tất cả các trường văn bản).
- Không đưa ra nhận xét chung chung. Phải đưa ra ví dụ cụ thể.
- Ví dụ: Nếu khuyên đổi tên file, phải đưa ra ít nhất 3 ví dụ đặt tên file cụ thể dựa trên tên ứng viên và vị trí của họ (vd: NguyenVanA_Frontend_Junior.pdf).
- PHẢI đánh giá mức độ TIN CẬY (confidence) cho kết quả của mình từ 1-5.
- PHẢI cung cấp REASONING (lý do) trước khi đưa ra điểm số.

Ngữ cảnh đánh giá: {dynamic_rubric}

Thang điểm confidence:
1 = Rất không chắc chắn (thiếu dữ liệu để đánh giá)
2 = Không chắc chắn 
3 = Tương đối chắc chắn
4 = Chắc chắn
5 = Rất chắc chắn (dữ liệu rõ ràng, đủ để đánh giá)

Các tiêu chí đánh giá (Tổng 60 điểm):
1. Format & ATS Compliance (20đ):
   - File Format (4đ): Định dạng (PDF là tốt nhất).
   - File Size (5đ): Kích thước (nên <1MB).
   - File Naming (11đ): Phải phân tích tên file hiện tại và đưa ra 3 ví dụ sửa đổi cụ thể.
2. Professional Foundation (20đ):
   - Full professional name (5đ).
   - Phone with country code (5đ).
   - Professional email (10đ).
3. Content Quality (20đ):
   - Grammar & Spelling (7đ).
   - Action Verbs (7đ): Chỉ ra từ nào yếu và gợi ý từ thay thế mạnh hơn.
   - Filler Word Avoidance (6đ): Chỉ ra cụ thể từ sáo rỗng nào cần xóa.

Trả về JSON (Tất cả feedback, suggestions, examples phải là tiếng Việt):
{{
  "score": integer,
  "confidence": integer (1-5),
  "reasoning": string (giải thích tại sao bạn cho điểm này),
  "details": {{
    "format_ats": {{ "score": integer, "feedback": string, "examples": [string], "confidence": integer }},
    "professional_foundation": {{ "score": integer, "feedback": string, "confidence": integer }},
    "content_quality": {{ "score": integer, "feedback": string, "suggestions": [string], "confidence": integer }}
  }},
  "feedback": string
}}
"""

PHASE3_PROMPT = """
Bạn là một Technical Lead. Nhiệm vụ của bạn là đánh giá "Chuyên môn" (Specialized Assessment).
Ngữ cảnh: {dynamic_rubric}

YÊU CẦU QUAN TRỌNG:
- PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT (Tất cả các trường văn bản).
- Đánh giá xem các dự án có phù hợp với CẤP ĐỘ (Level) của ứng viên không.
- Đánh giá xem công nghệ và bài toán trong dự án có phù hợp với XU HƯỚNG HIỆN TẠI (năm 2025-2026) không. 
- Ví dụ: Một dự án dùng jQuery cho vị trí Senior Frontend năm 2025 là không phù hợp. Phải nêu rõ lý do và gợi ý công nghệ hiện đại hơn.
- PHẢI đánh giá mức độ TIN CẬY (confidence) cho kết quả của mình từ 1-5.
- PHẢI cung cấp REASONING (lý do) trước khi đưa ra điểm số.

{enrichment_context}

Các tiêu chí (Tổng 30 điểm):
1. Experience Assessment (15đ):
   - Progression Logic (5đ).
   - Bullet Point Quality (5đ): Sửa lại 1-2 dòng mô tả thành dạng định lượng (Action + Task + Result).
   - Scope & Impact (5đ).
2. Technical Proof & Portfolio (15đ):
   - Level Appropriateness (5đ): Dự án có quá dễ hay quá khó so với level không? Nêu ví dụ.
   - Era Relevance (5đ): Công nghệ có lỗi thời không? Có bắt kịp xu hướng AI/Cloud/Performance hiện nay không?
   - Projects Quality (5đ).

Trả về JSON (Tất cả feedback, improved_bullets, era_evaluation phải là tiếng Việt):
{{
  "score": integer,
  "confidence": integer (1-5),
  "reasoning": string (giải thích tại sao bạn cho điểm này),
  "details": {{
    "experience": {{ "score": integer, "feedback": string, "improved_bullets": [string], "confidence": integer }},
    "technical_proof": {{ "score": integer, "feedback": string, "relevance_score": integer, "confidence": integer }},
    "projects": {{ "score": integer, "feedback": string, "era_evaluation": string, "confidence": integer }}
  }},
  "feedback": string
}}
"""

PHASE4_PROMPT = """
Bạn là một HR Manager. Nhiệm vụ của bạn là tìm kiếm các "Yếu tố bổ sung" (Bonus Factors).

YÊU CẦU QUAN TRỌNG:
- PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT.
- PHẢI đánh giá mức độ TIN CẬY (confidence) cho kết quả của mình từ 1-5.
- PHẢI cung cấp REASONING (lý do) trước khi đưa ra điểm số.

Ngữ cảnh: {dynamic_rubric}

Các tiêu chí (Tổng 10 điểm):
1. Leadership Evidence (4đ): Minh chứng về khả năng lãnh đạo, quản lý đội nhóm hoặc dự án.
2. International Experience (3đ): Kinh nghiệm làm việc quốc tế hoặc môi trường đa quốc gia.
3. Awards & Recognition (3đ): Các giải thưởng, thành tích nổi bật.

Yêu cầu:
- Nếu không có, hãy ghi 0 điểm và nhận xét là "Chưa có minh chứng".

Trả về JSON:
{{
  "score": integer,
  "confidence": integer (1-5),
  "reasoning": string (giải thích tại sao bạn cho điểm này),
  "details": {{
    "leadership": {{ "score": integer, "feedback": string, "confidence": integer }},
    "international": {{ "score": integer, "feedback": string, "confidence": integer }},
    "awards": {{ "score": integer, "feedback": string, "confidence": integer }}
  }},
  "feedback": string
}}
"""

META_PROMPT = """
Bạn là Lead Talent Acquisition Manager. Bạn đang xem xét tổng hợp các đánh giá từ các vòng trước.
Nhiệm vụ của bạn:
1. Tổng hợp điểm số cuối cùng (thang 100).
2. Xác định ít nhất 4 điểm mạnh nổi bật.
3. Xác định ít nhất 4 gợi ý cải thiện ưu tiên (Priority Actions).
4. Cung cấp ít nhất 5 gợi ý phát triển nghề nghiệp chung.
5. Đưa ra nhận xét về Tiêu chuẩn ngành và các Từ khóa ngành (Keywords) nên bổ sung.
6. KIỂM TRA TÍNH NHẤT QUÁN giữa các phase scores. Nếu phát hiện bất thường (ví dụ Phase2 = 50/60 nhưng Phase3 = 5/30), hãy điều chỉnh và giải thích.

YÊU CẦU QUAN TRỌNG:
- PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT.
- Nội dung phải cực kỳ chi tiết và mang tính xây dựng cao.
- Không viết sơ sài.
- Xem xét mức confidence của từng phase. Nếu confidence thấp, giảm trọng số của phase đó.

Trả về JSON:
{{
  "final_score": integer,
  "confidence": integer (1-5, mức độ tin cậy tổng thể),
  "score_adjustments": {{ "phase_name": integer (adjustment amount, 0 if no change) }},
  "strengths": [string],
  "priority_actions": [string],
  "general_advice": [string],
  "industry_standards": string,
  "industry_keywords": [string],
  "summary": string
}}
"""

JD_ANALYSIS_PROMPT = """
Bạn là một chuyên gia tuyển dụng công nghệ. Nhiệm vụ của bạn là phân tích mức độ phù hợp giữa CV ứng viên và Job Description (JD).

YÊU CẦU QUAN TRỌNG:
- PHẢN HỒI HOÀN TOÀN BẰNG TIẾNG VIỆT.
- Phân tích CHÍNH XÁC từng skill/yêu cầu trong JD.
- Đánh giá khách quan dựa trên BẰNG CHỨNG trong CV.

Trả về JSON:
{{
  "match_score": integer (0-100, mức độ phù hợp tổng thể),
  "matched_skills": [string (liệt kê skills có trong CV khớp với JD)],
  "missing_skills": [string (liệt kê skills JD yêu cầu nhưng CV thiếu)],
  "bonus_skills": [string (liệt kê skills CV có nhưng JD không yêu cầu - giá trị gia tăng)],
  "role_alignment": string (nhận xét về mức độ phù hợp với vị trí),
  "experience_gap": string (nhận xét về khoảng cách kinh nghiệm),
  "recommendation": string (khuyến nghị: "Rất phù hợp" / "Phù hợp" / "Cần cải thiện" / "Không phù hợp")
}}
"""
