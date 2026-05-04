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
    </div>
    """


def generate_html(state: AgentState) -> str:
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

    # Phase scores
    p2 = scores.get("PHASE2", {})
    p3 = scores.get("PHASE3", {})
    p4 = scores.get("PHASE4", {})

    # Processing metadata
    metadata = state.get("processing_metadata", {})
    model_used = metadata.get("model_used", "AI Engine")

    # Dynamic date
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d/%m/%Y %H:%M UTC")

    def render_details(details):
        if not details:
            return ""

        # Mapping English keys to Vietnamese titles
        title_map = {
            "format_ats": "Định dạng & ATS",
            "professional_foundation": "Nền tảng chuyên nghiệp",
            "content_quality": "Chất lượng nội dung",
            "experience": "Kinh nghiệm làm việc",
            "technical_proof": "Minh chứng kỹ thuật",
            "projects": "Dự án triển khai",
            "leadership": "Khả năng lãnh đạo",
            "languages": "Khả năng Ngoại ngữ",
            "awards": "Giải thưởng & Thành tích",
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
                html += '<div class="example-box"><strong>Ví dụ đề xuất:</strong><ul>'
                html += "".join([f"<li>{ex}</li>" for ex in examples])
                html += "</ul></div>"

            # Render Suggestions (from Phase 2)
            suggestions = v.get("suggestions", [])
            if suggestions:
                html += '<div class="suggestion-box"><strong>Gợi ý cụ thể:</strong><ul>'
                html += "".join([f"<li>{s}</li>" for s in suggestions])
                html += "</ul></div>"

            # Render Improved Bullets (from Phase 3)
            improved = v.get("improved_bullets", [])
            if improved:
                html += '<div class="improved-box"><strong>Dòng mô tả cải thiện:</strong><ul>'
                html += "".join([f"<li>{i}</li>" for i in improved])
                html += "</ul></div>"

            # Render Era Evaluation (from Phase 3)
            era_eval = v.get("era_evaluation", "")
            if era_eval:
                html += f'<div class="era-box"><strong>Đánh giá xu hướng:</strong> {era_eval}</div>'

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

    # Validation warning
    validation = state.get("validation_result", {})
    anomalies = validation.get("anomalies", [])
    validation_html = ""
    if anomalies:
        anomaly_items = "".join([f"<li>{a}</li>" for a in anomalies])
        validation_html = f"""
        <div class="validation-warning">
            <strong>Cảnh Báo Nhất Quán:</strong>
            <ul>{anomaly_items}</ul>
        </div>
        """

    # Score adjustments
    adjustments = meta.get("score_adjustments", {})
    adjustments_html = ""
    if adjustments and any(v != 0 for v in adjustments.values()):
        adj_items = "".join(
            [
                f"<li>{k}: {v:+d} điểm</li>"
                for k, v in adjustments.items()
                if v != 0
            ]
        )
        adjustments_html = f"""
        <div class="adjustments-note">
            <strong>Điều Chỉnh Điểm:</strong>
            <ul>{adj_items}</ul>
        </div>
        """

    detailed_analysis_html = ""
    if detailed_analysis:
        detailed_analysis_html = f"""
        <h2>Đánh Giá Toàn Diện</h2>
        <div style="background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px; margin-bottom: 40px; font-size: 15px; line-height: 1.8; color: #334155; white-space: pre-wrap;">{detailed_analysis}</div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phân Tích Resume - {name}</title>
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
                <div class="brand">DigiSource Intelligence</div>
                <div class="report-title">Báo Cáo Phân Tích Resume</div>
                <div class="report-meta">Pipeline v2.0 — {date_str}</div>
            </header>

            <div class="candidate-info">
                <div class="info-item">
                    <div class="label">Tên Ứng Viên</div>
                    <div class="value">{name}</div>
                </div>
                <div class="info-item">
                    <div class="label">Cấp Độ Chuyên Môn</div>
                    <div class="value">{level}</div>
                </div>
                <div class="info-item">
                    <div class="label">Ngành Nghề</div>
                    <div class="value">{industry}</div>
                </div>
            </div>

            <div class="score-card">
                <div class="final-score">{final_score}</div>
                <div class="score-info">
                    <div class="score-status">
                        Chỉ Số Đánh Giá / 100
                        {_confidence_badge(meta_confidence)}
                    </div>
                    <div class="summary-text">{summary}</div>
                </div>
            </div>

            {validation_html}
            {adjustments_html}
            {detailed_analysis_html}

            <h2>Phân Tích Từng Phần</h2>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">GIAI ĐOẠN 2: Nền tảng & Tối ưu ATS</span>
                    <div class="phase-score">
                        {_confidence_badge(p2.get('confidence', 3))}
                        <span style="color:{_score_color(p2.get('score', 0), 60)}">{p2.get('score', 0)} / 60</span>
                    </div>
                </div>
                {render_details(p2.get('details', {}))}
            </div>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">GIAI ĐOẠN 3: Đánh giá chuyên môn kỹ thuật</span>
                    <div class="phase-score">
                        {_confidence_badge(p3.get('confidence', 3))}
                        <span style="color:{_score_color(p3.get('score', 0), 40)}">{p3.get('score', 0)} / 40</span>
                    </div>
                </div>
                {render_details(p3.get('details', {}))}
            </div>

            <div class="phase-card">
                <div class="phase-header">
                    <span class="phase-title">GIAI ĐOẠN 4: Yếu tố bổ sung (Điểm thưởng)</span>
                    <div class="phase-score">
                        {_confidence_badge(p4.get('confidence', 3))}
                        <span style="color:{_score_color(p4.get('score', 0), 10)}">+{p4.get('score', 0)} Điểm</span>
                    </div>
                </div>
                {render_details(p4.get('details', {}))}
            </div>

            {jd_section_html}

            <div class="grid-2">
                <div class="highlight-item">
                    <h3>Điểm Mạnh Cốt Lõi</h3>
                    <ul>{strengths_html}</ul>
                </div>
                <div class="highlight-item">
                    <h3>Cải Thiện Ưu Tiên</h3>
                    <ul>{priority_html}</ul>
                </div>
            </div>

            <h2>Lộ Trình Chiến Lược</h2>
            <div style="background: #fff; border: 1px solid var(--border); padding: 30px; border-radius: 4px;">
                <div class="highlight-item" style="margin-bottom: 30px;">
                    <h3>Lời Khuyên Phát Triển Sự Nghiệp</h3>
                    <ul>{advice_html}</ul>
                </div>

                <div class="highlight-item" style="margin-bottom: 30px;">
                    <h3>Tiêu Chuẩn & Điểm Chuẩn Ngành</h3>
                    <p style="font-size: 14px; color: #475569;">{meta.get('industry_standards', '')}</p>
                </div>

                <div class="highlight-item">
                    <h3>Từ Khóa Ngành Trọng Tâm</h3>
                    <div style="font-size: 13px; font-family: 'JetBrains Mono', monospace; background: #f8fafc; padding: 15px; border: 1px solid var(--border); border-radius: 4px; color: var(--accent);">
                        {keywords_html}
                    </div>
                </div>
            </div>

            <div class="footer-info">
                <span>Được tạo bởi Hệ thống DigiSource Scorer v2.0</span>
                <span>Ngày: {date_str}</span>
                <span>Mức tin cậy: {_confidence_badge(meta_confidence)}</span>
                <span>Báo cáo phân tích bảo mật</span>
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

    html = generate_html(state)

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
