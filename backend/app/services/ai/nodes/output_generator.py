"""
Output Generator Node — Generates the HTML report with enhanced visualizations.
Includes confidence indicators, JD matching, skill gap analysis, and dynamic metadata.
"""

from datetime import datetime, timezone
from app.services.ai.state import AgentState
from app.core.logging_config import pipeline_logger
import time
import os


def _confidence_badge(confidence: int) -> str:
    """Generate a confidence badge with color coding."""
    colors = {
        1: ("#ef4444", "Rất thấp"),
        2: ("#f97316", "Thấp"),
        3: ("#eab308", "Trung bình"),
        4: ("#22c55e", "Cao"),
        5: ("#059669", "Rất cao"),
    }
    color, label = colors.get(confidence, ("#94a3b8", "N/A"))
    return f'<span class="confidence-badge" style="background:{color}">{label}</span>'


def _score_color(score: int, max_score: int) -> str:
    """Determine score color based on percentage."""
    if max_score == 0:
        return "#94a3b8"
    pct = score / max_score
    if pct >= 0.8:
        return "#059669"
    elif pct >= 0.6:
        return "#22c55e"
    elif pct >= 0.4:
        return "#eab308"
    elif pct >= 0.2:
        return "#f97316"
    return "#ef4444"


def _score_level_label(score: int, lang: str = "vi") -> tuple:
    """Map actual score to a descriptive quality label and color."""
    if score >= 90:
        labels = {"vi": "Xuất sắc", "en": "Excellent"}
        return labels.get(lang, labels["vi"]), "#059669"
    elif score >= 75:
        labels = {"vi": "Khá", "en": "Good"}
        return labels.get(lang, labels["vi"]), "#22c55e"
    elif score >= 60:
        labels = {"vi": "Trung bình", "en": "Average"}
        return labels.get(lang, labels["vi"]), "#eab308"
    elif score >= 40:
        labels = {"vi": "Cần cải thiện", "en": "Needs Improvement"}
        return labels.get(lang, labels["vi"]), "#f97316"
    else:
        labels = {"vi": "Yếu", "en": "Weak"}
        return labels.get(lang, labels["vi"]), "#ef4444"


TRANSLATIONS = {
    "vi": {
        "report_title": "Báo Cáo Phân Tích Resume",
        "brand": "DigiSource Intelligence",
        "candidate_name": "Tên Ứng Viên",
        "expertise_level": "Cấp Độ Chuyên Môn",
        "industry": "Ngành Nghề",
        "score_unit": "/ 100",
        "confidence_label": "Mức tin cậy",
        "section_analysis": "Phân Tích Từng Phần",
        "phase2_title": "GIAI ĐOẠN 2: Nền tảng & Tối ưu ATS",
        "phase3_title": "GIAI ĐOẠN 3: Đánh giá chuyên môn kỹ thuật",
        "phase4_title": "GIAI ĐOẠN 4: Yếu tố bổ sung (Điểm thưởng)",
        "bonus_points": "Điểm",
        "core_strengths": "Điểm Mạnh Cốt Lõi",
        "priority_improvements": "Cải Thiện Ưu Tiên",
        "strategic_roadmap": "Lộ Trình Chiến Lược",
        "career_advice": "Lời Khuyên Phát Triển Sự Nghiệp",
        "industry_standards": "Tiêu Chuẩn & Điểm Chuẩn Ngành",
        "industry_keywords": "Từ Khóa Ngành Trọng Tâm",
        "comprehensive_eval": "Đánh Giá Toàn Diện",
        "generated_by": "Được tạo bởi Hệ thống DigiSource Scorer v2.0",
        "date_label": "Ngày",
        "confidence_report": "Mức tin cậy",
        "security_note": "Báo cáo phân tích bảo mật",
        "consistency_warning": "Cảnh Báo Nhất Quán",
        "score_adjustments": "Điều Chỉnh Điểm",
        "adj_points": "điểm",
        "format_ats": "Định dạng & ATS",
        "professional_foundation": "Nền tảng chuyên nghiệp",
        "content_quality": "Chất lượng nội dung",
        "experience": "Kinh nghiệm làm việc",
        "technical_proof": "Minh chứng kỹ thuật",
        "projects": "Dự án triển khai",
        "leadership": "Khả năng lãnh đạo",
        "languages": "Khả năng Ngoại ngữ",
        "awards": "Giải thưởng & Thành tích",
        "example_suggest": "Ví dụ đề xuất",
        "specific_suggest": "Gợi ý cụ thể",
        "improved_desc": "Dòng mô tả cải thiện",
        "trend_eval": "Đánh giá xu hướng",
        "tech_stack_title": "Phân Tích Tech Stack & Năng Lực Lõi",
        "soft_skills_title": "Đánh Giá Kỹ Năng Mềm & Độ Phù Hợp",
        "page_header": "AI CV Analysis Report",
    },
    "en": {
        "report_title": "Resume Analysis Report",
        "brand": "DigiSource Intelligence",
        "candidate_name": "Candidate Name",
        "expertise_level": "Expertise Level",
        "industry": "Industry",
        "score_unit": "/ 100",
        "confidence_label": "Confidence",
        "section_analysis": "Section-by-Section Analysis",
        "phase2_title": "PHASE 2: Foundation & ATS Optimization",
        "phase3_title": "PHASE 3: Technical Expertise Assessment",
        "phase4_title": "PHASE 4: Bonus Factors",
        "bonus_points": "Points",
        "core_strengths": "Core Strengths",
        "priority_improvements": "Priority Improvements",
        "strategic_roadmap": "Strategic Roadmap",
        "career_advice": "Career Development Advice",
        "industry_standards": "Industry Standards & Benchmarks",
        "industry_keywords": "Key Industry Keywords",
        "comprehensive_eval": "Comprehensive Evaluation",
        "generated_by": "Generated by DigiSource Scorer v2.0",
        "date_label": "Date",
        "confidence_report": "Confidence",
        "security_note": "Confidential analysis report",
        "consistency_warning": "Consistency Warning",
        "score_adjustments": "Score Adjustments",
        "adj_points": "points",
        "format_ats": "Format & ATS",
        "professional_foundation": "Professional Foundation",
        "content_quality": "Content Quality",
        "experience": "Work Experience",
        "technical_proof": "Technical Proof",
        "projects": "Projects",
        "leadership": "Leadership",
        "languages": "Language Skills",
        "awards": "Awards & Achievements",
        "example_suggest": "Suggested Examples",
        "specific_suggest": "Specific Suggestions",
        "improved_desc": "Improved Descriptions",
        "trend_eval": "Trend Evaluation",
        "tech_stack_title": "Tech Stack & Core Competency Analysis",
        "soft_skills_title": "Soft Skills & Culture Fit Assessment",
        "page_header": "AI CV Analysis Report",
    },
}


def _render_jd_section(jd_analysis: dict) -> str:
    """Render the JD matching section of the report."""
    if not jd_analysis:
        return ""

    match_score = jd_analysis.get("match_score", 0)
    recommendation = jd_analysis.get("recommendation", "N/A")

    # Recommendation color
    rec_colors = {
        "Rất phù hợp": "#059669",
        "Phù hợp": "#22c55e",
        "Cần cải thiện": "#eab308",
        "Không phù hợp": "#ef4444",
    }
    rec_color = rec_colors.get(recommendation, "#94a3b8")

    matched = jd_analysis.get("matched_skills", [])
    missing = jd_analysis.get("missing_skills", [])
    bonus = jd_analysis.get("bonus_skills", [])

    matched_html = "".join(
        [f'<span class="skill-tag skill-matched">{s}</span>' for s in matched]
    )
    missing_html = "".join(
        [f'<span class="skill-tag skill-missing">{s}</span>' for s in missing]
    )
    bonus_html = "".join(
        [f'<span class="skill-tag skill-bonus">{s}</span>' for s in bonus]
    )

    interview_questions = jd_analysis.get("interview_questions", [])
    interview_html = ""
    if interview_questions:
        questions_list = "".join([
            f'''
            <div style="background: #f8fafc; padding: 15px; border-left: 3px solid #3b82f6; margin-bottom: 10px; border-radius: 4px;">
                <h4 style="color:#1e40af; margin-top:0; margin-bottom:5px;">Q: {q.get("question", "")}</h4>
                <p style="font-size:13px; color:#475569; margin:0 0 5px 0;"><strong>Mục đích:</strong> {q.get("intent", "")}</p>
                <p style="font-size:13px; color:#059669; margin:0;"><strong>Gợi ý trả lời:</strong> {q.get("expected_answer", "")}</p>
            </div>
            '''
            for q in interview_questions
        ])
        interview_html = f"""
        <div class="interview-section" style="margin-top: 25px; padding-top: 20px; border-top: 1px solid var(--border);">
            <h3 style="color:#1e293b; margin-bottom:15px;">Câu Hỏi Phỏng Vấn Đề Xuất (Dựa trên Skill Gaps)</h3>
            {questions_list}
        </div>
        """

    return f"""
    <h2>So Khớp Với Job Description</h2>
    <div class="jd-card">
        <div class="jd-header">
            <div class="jd-score">{match_score}<span class="jd-score-unit">%</span></div>
            <div class="jd-info">
                <div class="jd-recommendation" style="color:{rec_color};font-weight:800;text-transform:uppercase;font-size:14px;">{recommendation}</div>
                <p style="font-size:14px;color:#64748b;margin-top:5px;">{jd_analysis.get('role_alignment', '')}</p>
                <p style="font-size:13px;color:#94a3b8;margin-top:3px;">{jd_analysis.get('experience_gap', '')}</p>
            </div>
        </div>

        <div class="skill-section">
            <div class="skill-group">
                <h4 style="color:#059669;">Skills Phù Hợp ({len(matched)})</h4>
                <div class="skill-tags">{matched_html}</div>
            </div>
            <div class="skill-group">
                <h4 style="color:#ef4444;">Skills Thiếu ({len(missing)})</h4>
                <div class="skill-tags">{missing_html}</div>
            </div>
            <div class="skill-group">
                <h4 style="color:#3b82f6;">Skills Bổ Sung ({len(bonus)})</h4>
                <div class="skill-tags">{bonus_html}</div>
            </div>
        </div>
        
        {interview_html}
    </div>
    """


def generate_html(state: AgentState, lang: str = "vi") -> str:
    t = TRANSLATIONS.get(lang, TRANSLATIONS["vi"])
    scores = state.get("scores", {})
    meta = scores.get("META", {})

    # Candidate Info
    name = state.get("candidate_name", "N/A")
    level = state.get("candidate_level", "N/A")
    industry = state.get("industry", "N/A")

    final_score = meta.get("final_score", 0)
    summary = meta.get("summary", "")
    detailed_analysis = meta.get("detailed_analysis", "")
    meta_confidence = meta.get("confidence", 3)
    score_label, score_label_color = _score_level_label(final_score, lang)

    # Phase scores
    p2 = scores.get("PHASE2", {})
    p3 = scores.get("PHASE3", {})
    p4 = scores.get("PHASE4", {})
    project_eval = scores.get("PROJECT_EVAL", {})
    tech_stack_eval = scores.get("TECH_STACK_EVAL", {})
    soft_skills_eval = scores.get("SOFT_SKILLS_EVAL", {})

    # Validate Phase 4 bonus: total must match sum of sub-items
    p4_details = p4.get("details", {})
    if p4_details:
        p4_sub_total = sum(d.get("score", 0) for d in p4_details.values() if isinstance(d, dict))
        if p4.get("score", 0) != p4_sub_total:
            p4 = dict(p4)
            p4["score"] = p4_sub_total


    # Dynamic date
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d/%m/%Y %H:%M UTC")

    def render_details(details):
        if not details:
            return ""

        # Use translations for detail titles
        title_map = {
            "format_ats": t["format_ats"],
            "professional_foundation": t["professional_foundation"],
            "content_quality": t["content_quality"],
            "experience": t["experience"],
            "technical_proof": t["technical_proof"],
            "projects": t["projects"],
            "leadership": t["leadership"],
            "languages": t["languages"],
            "awards": t["awards"],
        }

        html = '<div class="details-container">'
        for k, v in details.items():
            title = title_map.get(k.lower(), k.replace("_", " ").title())
            score = v.get("score", 0)
            fb = v.get("feedback", "")
            item_confidence = v.get("confidence", 3)

            html += f"""
            <div class="detail-item">
                <div class="detail-header">
                    <span class="detail-title">{title}</span>
                    <div style="display:flex;align-items:center;gap:8px;">
                        {_confidence_badge(item_confidence)}
                        <span class="detail-score">{score}đ</span>
                    </div>
                </div>
                <div class="detail-body">
                    <p>{fb}</p>
            """

            # Render Examples (from Phase 2)
            examples = v.get("examples", [])
            if examples:
                html += f'<div class="example-box"><strong>{t["example_suggest"]}:</strong><ul>'
                html += "".join([f"<li>{ex}</li>" for ex in examples])
                html += "</ul></div>"

            # Render Suggestions (from Phase 2)
            suggestions = v.get("suggestions", [])
            if suggestions:
                html += f'<div class="suggestion-box"><strong>{t["specific_suggest"]}:</strong><ul>'
                html += "".join([f"<li>{s}</li>" for s in suggestions])
                html += "</ul></div>"

            # Render Improved Bullets (from Phase 3)
            improved = v.get("improved_bullets", [])
            if improved:
                html += f'<div class="improved-box"><strong>{t["improved_desc"]}:</strong><ul>'
                html += "".join([f"<li>{i}</li>" for i in improved])
                html += "</ul></div>"

            # Render Era Evaluation (from Phase 3)
            era_eval = v.get("era_evaluation", "")
            if era_eval:
                html += f'<div class="era-box"><strong>{t["trend_eval"]}:</strong> {era_eval}</div>'

            html += "</div></div>"
        html += "</div>"
        return html

    strengths_html = "".join(
        [f"<li>{s}</li>" for s in meta.get("strengths", [])]
    )
    priority_html = "".join(
        [f"<li>{a}</li>" for a in meta.get("priority_actions", [])]
    )
    advice_html = "".join(
        [f"<li>{a}</li>" for a in meta.get("general_advice", [])]
    )
    keywords_html = ", ".join(meta.get("industry_keywords", []))

    # JD Section
    jd_analysis = state.get("jd_analysis")
    jd_section_html = _render_jd_section(jd_analysis)

    # Market Insight Section
    market_insight = state.get("market_insight")
    market_html = ""
    if market_insight:
        trending = "".join([f'<span class="skill-tag skill-bonus">{s}</span>' for s in market_insight.get('trending_skills', [])])
        market_html = f"""
        <h2>Phân Tích Thị Trường Tuyển Dụng</h2>
        <div style="background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px; margin-bottom: 40px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div style="background: #f8fafc; padding: 15px; border-radius: 4px;">
                    <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 700; margin-bottom: 5px;">Mức Lương Tham Khảo</div>
                    <div style="font-size: 16px; font-weight: 700; color: #059669;">{market_insight.get('salary_range', 'N/A')}</div>
                </div>
                <div style="background: #f8fafc; padding: 15px; border-radius: 4px;">
                    <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 700; margin-bottom: 5px;">Nhu Cầu Thị Trường</div>
                    <div style="font-size: 14px; color: var(--primary);">{market_insight.get('market_demand', 'N/A')}</div>
                </div>
            </div>
            <div style="margin-bottom: 20px;">
                <div style="font-size: 13px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">Kỹ Năng Xu Hướng (Trending):</div>
                <div class="skill-tags">{trending}</div>
            </div>
            <div>
                <div style="font-size: 13px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">Yêu Cầu Tiêu Chuẩn:</div>
                <div style="font-size: 14px; color: #475569; line-height: 1.6;">{market_insight.get('standard_requirements', 'N/A')}</div>
            </div>
        </div>
        """

    # Project Evaluation Section
    project_eval_html = ""
    project_list = project_eval.get("projects", [])
    if project_list:
        complexity_colors = {
            1: "#94a3b8", 2: "#22c55e", 3: "#eab308", 4: "#f97316", 5: "#ef4444"
        }
        complexity_labels = {
            1: "Đơn giản", 2: "Cơ bản", 3: "Trung bình", 4: "Phức tạp", 5: "Enterprise"
        }
        projects_cards = ""
        for proj in project_list:
            crating = proj.get("complexity_rating", 1)
            c_color = complexity_colors.get(crating, "#94a3b8")
            c_label = complexity_labels.get(crating, "N/A")
            dots = "".join([
                f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{c_color if i < crating else "#e2e8f0"};margin-right:3px;"></span>'
                for i in range(5)
            ])
            projects_cards += f'''
            <div style="background:#fff;border:1px solid var(--border);padding:20px;border-radius:4px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <h4 style="margin:0;color:var(--primary);font-size:15px;">{proj.get("project_name", "N/A")}</h4>
                    <div style="display:flex;align-items:center;gap:6px;">
                        {dots}
                        <span style="font-size:11px;color:{c_color};font-weight:700;">{c_label}</span>
                    </div>
                </div>
                <div style="font-size:13px;color:#475569;margin-bottom:8px;">
                    <strong>Stack công nghệ:</strong> {proj.get("tech_stack_analysis", "")}
                </div>
                <div style="font-size:13px;color:#475569;margin-bottom:8px;">
                    <strong>Vai trò:</strong> {proj.get("role_clarity", "")}
                </div>
                <div style="font-size:13px;color:#475569;margin-bottom:8px;">
                    <strong>Impact:</strong> {proj.get("impact_assessment", "")}
                </div>
                <div style="background:#fffbeb;border-left:3px solid var(--warning);padding:10px 12px;border-radius:4px;font-size:12px;color:#92400e;">
                    <strong>Gợi ý cải thiện:</strong> {proj.get("improvement_suggestion", "")}
                </div>
            </div>
            '''

        portfolio_score = project_eval.get("portfolio_score", 0)
        overall_assessment = project_eval.get("overall_assessment", "")
        project_eval_html = f"""
        <h2>Đánh Giá Chi Tiết Từng Dự Án</h2>
        <div style="background:#f8fafc;border:1px solid var(--border);padding:20px;border-radius:4px;margin-bottom:15px;display:flex;align-items:center;gap:20px;">
            <div style="font-size:36px;font-weight:900;color:var(--primary);">{portfolio_score}<span style="font-size:16px;color:#94a3b8;">/10</span></div>
            <div style="flex:1;">
                <div style="font-size:12px;text-transform:uppercase;color:#94a3b8;font-weight:700;">Chất Lượng Portfolio</div>
                <div style="font-size:14px;color:#475569;margin-top:3px;">{overall_assessment}</div>
            </div>
        </div>
        {projects_cards}
        """

    # Tech Stack HTML
    tech_stack_html = ""
    if tech_stack_eval:
        core_comp = tech_stack_eval.get("core_competency", "")
        domains = tech_stack_eval.get("domains", [])
        overall_tech = tech_stack_eval.get("overall_tech_assessment", "")
        
        domains_html = ""
        for dom in domains:
            domain_name = dom.get("domain_name", "")
            skills = dom.get("skills", [])
            assessment = dom.get("assessment", "")
            skills_html = "".join([f'<span class="skill-tag" style="background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;">{s}</span>' for s in skills])
            domains_html += f'''
            <div style="margin-bottom:15px;">
                <h4 style="color:#0f172a;margin-bottom:8px;font-size:14px;">{domain_name}</h4>
                <div class="skill-tags" style="margin-bottom:8px;">{skills_html}</div>
                <div style="font-size:13px;color:#475569;">{assessment}</div>
            </div>
            '''
        
        tech_stack_html = f"""
        <h2>{t.get('tech_stack_title', 'Tech Stack Analysis')}</h2>
        <div style="background:#fff;border:1px solid var(--border);padding:20px;border-radius:4px;margin-bottom:40px;">
            <div style="background:#f8fafc;padding:15px;border-radius:4px;margin-bottom:20px;border-left:4px solid var(--accent);">
                <div style="font-size:12px;text-transform:uppercase;color:#94a3b8;font-weight:700;">Năng Lực Cốt Lõi</div>
                <div style="font-size:16px;color:var(--primary);font-weight:700;">{core_comp}</div>
            </div>
            {domains_html}
            <div style="margin-top:20px;padding-top:15px;border-top:1px dashed var(--border);font-size:13px;color:#475569;">
                <strong>Đánh giá chung:</strong> {overall_tech}
            </div>
        </div>
        """

    # Soft Skills HTML
    soft_skills_html = ""
    if soft_skills_eval:
        skills = soft_skills_eval.get("skills", [])
        culture_fit = soft_skills_eval.get("culture_fit_prediction", "")
        
        skills_cards = ""
        for sk in skills:
            skill_name = sk.get("skill_name", "")
            evidence = sk.get("evidence", "")
            strength = sk.get("strength_level", "")
            strength_colors = {"Cao": "#22c55e", "Trung bình": "#eab308", "Thấp": "#ef4444", "Chưa rõ": "#94a3b8"}
            s_color = strength_colors.get(strength, "#94a3b8")
            
            skills_cards += f'''
            <div style="background:#fff;border:1px solid var(--border);padding:15px;border-radius:4px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div style="font-weight:700;color:var(--primary);font-size:14px;">{skill_name}</div>
                    <div style="font-size:11px;font-weight:700;color:{s_color};padding:2px 8px;border-radius:10px;background:#f8fafc;border:1px solid {s_color}40;">{strength}</div>
                </div>
                <div style="font-size:13px;color:#475569;"><strong>Minh chứng:</strong> {evidence}</div>
            </div>
            '''
            
        soft_skills_html = f"""
        <h2>{t.get('soft_skills_title', 'Soft Skills Analysis')}</h2>
        <div style="margin-bottom:40px;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px;">
                {skills_cards}
            </div>
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:15px;border-radius:4px;color:#166534;font-size:14px;">
                <strong>Dự đoán môi trường phù hợp:</strong> {culture_fit}
            </div>
        </div>
        """

    # Validation warning
    validation = state.get("validation_result", {})
    anomalies = validation.get("anomalies", [])
    validation_html = ""
    if anomalies:
        anomaly_items = "".join([f"<li>{a}</li>" for a in anomalies])
        validation_html = f"""
        <div class="validation-warning">
            <strong>{t['consistency_warning']}:</strong>
            <ul>{anomaly_items}</ul>
        </div>
        """

    # Score adjustments
    adjustments = meta.get("score_adjustments", {})
    adjustments_html = ""
    if adjustments and any(v != 0 for v in adjustments.values()):
        adj_items = "".join(
            [
                f"<li>{k}: {v:+d} {t['adj_points']}</li>"
                for k, v in adjustments.items()
                if v != 0
            ]
        )
        adjustments_html = f"""
        <div class="adjustments-note">
            <strong>{t['score_adjustments']}:</strong>
            <ul>{adj_items}</ul>
        </div>
        """

    detailed_analysis_html = ""
    if detailed_analysis:
        detailed_analysis_html = f"""
        <h2>{t['comprehensive_eval']}</h2>
        <div style="background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px; margin-bottom: 40px; font-size: 15px; line-height: 1.8; color: #334155; white-space: pre-wrap;">{detailed_analysis}</div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{t['report_title']} - {name}</title>
        <style>
            :root {{
                --primary: #0f172a;
                --accent: #2563eb;
                --success: #059669;
                --warning: #d97706;
                --danger: #ef4444;
                --bg: #fdfdfd;
                --text: #334155;
                --border: #e2e8f0;
            }}
            body {{ font-family: 'Inter', -apple-system, sans-serif; line-height: 1.6; color: var(--text); background-color: var(--bg); margin: 0; padding: 60px 20px; }}
            .container {{ max-width: 850px; margin: 0 auto; }}

            header {{ border-bottom: 2px solid var(--primary); padding-bottom: 20px; margin-bottom: 40px; }}
            .brand {{ font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); }}
            .report-title {{ font-size: 32px; font-weight: 900; color: var(--primary); margin: 5px 0; }}
            .report-meta {{ font-size: 12px; color: #94a3b8; margin-top: 5px; }}

            .candidate-info {{ display: flex; gap: 40px; margin-bottom: 40px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }}
            .info-item .label {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 700; letter-spacing: 0.5px; }}
            .info-item .value {{ font-size: 16px; font-weight: 600; color: var(--primary); }}

            .score-card {{ display: flex; align-items: center; gap: 30px; background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px; margin-bottom: 40px; }}
            .final-score {{ font-size: 64px; font-weight: 900; color: var(--primary); }}
            .score-info {{ flex: 1; }}
            .score-status {{ font-weight: 700; color: var(--accent); text-transform: uppercase; font-size: 14px; display: flex; align-items: center; gap: 10px; }}
            .summary-text {{ font-size: 15px; color: #64748b; margin-top: 5px; }}

            .confidence-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; color: #fff; text-transform: uppercase; letter-spacing: 0.3px; }}

            h2 {{ font-size: 20px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; margin-top: 60px; margin-bottom: 25px; display: flex; align-items: center; gap: 10px; }}
            h2::after {{ content: ""; height: 1px; background: var(--border); flex: 1; }}

            .phase-card {{ margin-bottom: 40px; }}
            .phase-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .phase-title {{ font-size: 16px; font-weight: 700; color: var(--primary); }}
            .phase-score {{ font-weight: 800; display: flex; align-items: center; gap: 8px; }}

            .details-container {{ display: grid; gap: 20px; }}
            .detail-item {{ background: #fff; border: 1px solid var(--border); padding: 20px; border-radius: 4px; }}
            .detail-header {{ display: flex; justify-content: space-between; align-items: center; font-weight: 700; margin-bottom: 10px; font-size: 14px; }}
            .detail-title {{ color: var(--primary); }}
            .detail-score {{ color: var(--success); font-size: 15px; }}
            .detail-body p {{ margin: 0; font-size: 14px; color: #475569; }}

            .example-box, .suggestion-box, .improved-box, .era-box {{ margin-top: 15px; padding: 12px 15px; border-radius: 4px; font-size: 13px; }}
            .example-box {{ background: #f8fafc; border-left: 3px solid var(--accent); }}
            .suggestion-box {{ background: #fffbeb; border-left: 3px solid var(--warning); }}
            .improved-box {{ background: #f0fdf4; border-left: 3px solid var(--success); }}
            .era-box {{ background: #f1f5f9; border-left: 3px solid #94a3b8; font-style: italic; }}

            .validation-warning {{ background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid var(--danger); padding: 15px 20px; border-radius: 4px; margin-bottom: 30px; font-size: 13px; }}
            .adjustments-note {{ background: #fffbeb; border: 1px solid #fed7aa; border-left: 4px solid var(--warning); padding: 15px 20px; border-radius: 4px; margin-bottom: 30px; font-size: 13px; }}

            ul {{ padding-left: 18px; margin: 5px 0; }}
            li {{ margin-bottom: 4px; }}

            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 40px; }}
            .highlight-item h3 {{ font-size: 14px; font-weight: 700; text-transform: uppercase; margin-bottom: 15px; color: var(--primary); }}
            .highlight-item ul {{ font-size: 14px; color: #475569; }}

            /* JD Matching Styles */
            .jd-card {{ background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px; margin-bottom: 40px; }}
            .jd-header {{ display: flex; align-items: center; gap: 25px; margin-bottom: 25px; }}
            .jd-score {{ font-size: 48px; font-weight: 900; color: var(--primary); }}
            .jd-score-unit {{ font-size: 20px; color: #94a3b8; }}
            .jd-info {{ flex: 1; }}
            .skill-section {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
            .skill-group h4 {{ font-size: 13px; margin-bottom: 10px; }}
            .skill-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
            .skill-tag {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
            .skill-matched {{ background: #dcfce7; color: #166534; }}
            .skill-missing {{ background: #fee2e2; color: #991b1b; }}
            .skill-bonus {{ background: #dbeafe; color: #1e40af; }}

            .footer-info {{ margin-top: 80px; padding-top: 30px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; color: #94a3b8; font-size: 12px; flex-wrap: wrap; gap: 10px; }}

            @media (max-width: 600px) {{
                .candidate-info, .grid-2 {{ flex-direction: column; grid-template-columns: 1fr; gap: 20px; }}
                .skill-section {{ grid-template-columns: 1fr; }}
                .jd-header {{ flex-direction: column; text-align: center; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="brand">{t['brand']}</div>
                <div class="report-title">{t['report_title']}</div>
                <div class="report-meta">Pipeline v2.0 — {date_str}</div>
            </header>

            {f'''
            <div style="background: #fffbeb; border: 1px solid #f59e0b; border-left: 5px solid #d97706; padding: 15px 20px; border-radius: 4px; margin-bottom: 30px;">
                <h3 style="color: #b45309; margin: 0 0 5px 0; font-size: 16px;">⚠️ Cảnh Báo: Chế Độ Đánh Giá Dự Phòng</h3>
                <p style="color: #92400e; margin: 0; font-size: 14px;">Hệ thống phân tích AI nâng cao hiện đang quá tải hoặc gặp sự cố kết nối. Báo cáo này được tạo bởi thuật toán dự phòng cơ bản, do đó điểm số (đặc biệt là mục kinh nghiệm) và phân tích có thể sơ sài, không phản ánh đúng 100% năng lực thực tế của bạn.</p>
            </div>
            ''' if any("lỗi" in err.lower() or "error" in err.lower() for err in state.get("errors", [])) else ""}

            <div class="candidate-info">
                <div class="info-item">
                    <div class="label">{t['candidate_name']}</div>
                    <div class="value">{name}</div>
                </div>
                <div class="info-item">
                    <div class="label">{t['expertise_level']}</div>
                    <div class="value">{level}</div>
                </div>
                <div class="info-item">
                    <div class="label">{t['industry']}</div>
                    <div class="value">{industry}</div>
                </div>
            </div>

            <div class="score-card">
                <div class="final-score">{final_score}</div>
                <div class="score-info">
                    <div class="score-status" style="color:{score_label_color}">
                        {score_label} — {final_score} {t['score_unit']}
                    </div>
                    <div class="summary-text">{summary}</div>
                    <div style="margin-top:8px;font-size:12px;color:#94a3b8;">
                        {t['confidence_label']}: {_confidence_badge(meta_confidence)}
                    </div>
                </div>
            </div>

            {validation_html}
            {adjustments_html}
            {detailed_analysis_html}

            <h2>{t['section_analysis']}</h2>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">{t['phase2_title']}</span>
                    <div class="phase-score">
                        {_confidence_badge(p2.get('confidence', 3))}
                        <span style="color:{_score_color(p2.get('score', 0), 60)}">{p2.get('score', 0)} / 60</span>
                    </div>
                </div>
                {render_details(p2.get('details', {}))}
            </div>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">{t['phase3_title']}</span>
                    <div class="phase-score">
                        {_confidence_badge(p3.get('confidence', 3))}
                        <span style="color:{_score_color(p3.get('score', 0), 40)}">{p3.get('score', 0)} / 40</span>
                    </div>
                </div>
                {render_details(p3.get('details', {}))}
            </div>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">{t['phase4_title']}</span>
                    <div class="phase-score">
                        {_confidence_badge(p4.get('confidence', 3))}
                        <span style="color:{_score_color(p4.get('score', 0), 10)}">+{p4.get('score', 0)} {t['bonus_points']}</span>
                    </div>
                </div>
                {render_details(p4.get('details', {}))}
            </div>

            {tech_stack_html}
            {soft_skills_html}

            {jd_section_html}
            {market_html}
            {project_eval_html}

            <div class="grid-2">
                <div class="highlight-item">
                    <h3>{t['core_strengths']}</h3>
                    <ul>{strengths_html}</ul>
                </div>
                <div class="highlight-item">
                    <h3>{t['priority_improvements']}</h3>
                    <ul>{priority_html}</ul>
                </div>
            </div>

            <h2>{t['strategic_roadmap']}</h2>
            <div style="background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px;">
                <div class="highlight-item" style="margin-bottom: 30px;">
                    <h3>{t['career_advice']}</h3>
                    <ul>{advice_html}</ul>
                </div>

                <div class="highlight-item" style="margin-bottom: 30px;">
                    <h3>{t['industry_standards']}</h3>
                    <p style="font-size: 14px; color: #475569;">{meta.get('industry_standards', '')}</p>
                </div>

                <div class="highlight-item">
                    <h3>{t['industry_keywords']}</h3>
                    <div style="font-size: 13px; font-family: 'JetBrains Mono', monospace; background: #f8fafc; padding: 15px; border: 1px solid var(--border); border-radius: 4px; color: var(--accent);">
                        {keywords_html}
                    </div>
                </div>
            </div>

            <div class="footer-info">
                <span>{t['generated_by']}</span>
                <span>{t['date_label']}: {date_str}</span>
                <span>{t['confidence_report']}: {_confidence_badge(meta_confidence)}</span>
                <span>{t['security_note']}</span>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def output_generator_node(state: AgentState) -> dict:
    """Generates the final HTML report and saves to disk."""
    start = time.time()
    pipeline_logger.node_start("output_generator")

    lang = state.get("report_lang", "vi")
    html = generate_html(state, lang=lang)

    # Save to file
    output_dir = os.path.join("data", "output")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "report_output.html")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        pipeline_logger.node_error(
            "output_generator", f"Failed to save report: {e}"
        )

    duration_ms = (time.time() - start) * 1000
    pipeline_logger.node_complete(
        "output_generator", duration_ms=duration_ms
    )

    return {
        "report_html": html,
        "processing_metadata": {
            "output_generator_duration_ms": round(duration_ms, 2),
        },
        "errors": [],
    }
