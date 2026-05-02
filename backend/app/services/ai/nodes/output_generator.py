from app.services.ai.state import AgentState

def generate_html(scores: dict, insights: dict) -> str:
    meta = scores.get("META", {})
    final_score = meta.get("final_score", 0)
    strengths = "".join([f"<li>{s}</li>" for s in meta.get("strengths", [])])
    weaknesses = "".join([f"<li>{w}</li>" for w in meta.get("weaknesses", [])])
    summary = meta.get("summary", "")
    
    section_html = ""
    for sec, data in scores.items():
        if sec == "META": continue
        s = data.get("score", 0)
        fb = data.get("feedback", "")
        # Basic parsing to HTML
        fb_html = fb.replace("\n", "<br>")
        section_html += f"<h3>{sec} - Score: {s}</h3><p>{fb_html}</p>"
        
    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>CV Analysis Report</title>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; margin-top: 30px; }}
            .summary {{ background: #ecf0f1; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            .score-container {{ text-align: center; margin: 20px 0; }}
            .score {{ font-size: 48px; font-weight: bold; color: #27ae60; }}
            .section {{ background: #fff; border: 1px solid #e0e0e0; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            .pro {{ color: #27ae60; }}
            .con {{ color: #c0392b; }}
        </style>
    </head>
    <body>
        <h1>Báo Cáo Phân Tích Resume</h1>
        
        <div class="summary">
            <div class="score-container">
                <div>Tổng Điểm</div>
                <div class="score">{final_score}/100</div>
            </div>
            <p><strong>Executive Summary:</strong> {summary}</p>
        </div>
        
        <div style="display: flex; gap: 20px;">
            <div style="flex: 1; background: #e8f8f5; padding: 15px; border-radius: 8px;">
                <h2 class="pro" style="margin-top: 0;">👍 Điểm Mạnh</h2>
                <ul>{strengths}</ul>
            </div>
            <div style="flex: 1; background: #fdf2e9; padding: 15px; border-radius: 8px;">
                <h2 class="con" style="margin-top: 0;">🔧 Cần Cải Thiện</h2>
                <ul>{weaknesses}</ul>
            </div>
        </div>
        
        <h2>Phân Tích Chi Tiết</h2>
        <div class="section">
            {section_html}
        </div>
    </body>
    </html>
    """
    return html

def output_generator_node(state: AgentState) -> dict:
    scores = state.get("scores", {})
    insights = state.get("text_insights", {})
    
    html = generate_html(scores, insights)
    
    return {
        "report_html": html
    }
