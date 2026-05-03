"""
AI Pipeline Test Runner — Full pipeline test with detailed streaming logs.
Supports the upgraded v2.0 pipeline with parallel evaluation and confidence scoring.
"""

import os
import sys
import io
import json
from datetime import datetime

# Fix Windows terminal encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables BEFORE importing app modules
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

from app.services.ai.graph import cv_graph
from app.core.logging_config import set_correlation_id


def _confidence_emoji(conf: int) -> str:
    """Map confidence level to emoji indicator."""
    return {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "✅"}.get(conf, "⚪")


def print_step(node_name, data):
    """Utility to print streaming steps beautifully."""
    print(f"\n[+] [{node_name.upper()}] completed.")

    if node_name == "pdf_processor":
        meta = data.get("processing_metadata", {})
        sections = meta.get("sections_found", [])
        print(f"    - Found {len(sections)} sections: {', '.join(sections)}")
        print(f"    - File size: {meta.get('cv_file_size_bytes', 0) / 1024:.1f}KB")
        print(f"    - Cleaned text: {meta.get('cleaned_text_length', 0)} chars")

    elif node_name == "profiler":
        print(f"    - Candidate: {data.get('candidate_name', 'N/A')}")
        print(f"    - Level: {data.get('candidate_level', 'Unknown')}")
        print(f"    - Industry: {data.get('industry', 'N/A')}")

    elif node_name == "enrichment":
        meta = data.get("processing_metadata", {})
        if meta.get("enrichment_skipped"):
            print("    - Skipped (no API key)")
        else:
            print(
                f"    - Results: {meta.get('enrichment_results_count', 0)}"
            )
            print(f"    - Query: {meta.get('enrichment_query', 'N/A')}")

    elif node_name.startswith("phase"):
        scores = data.get("scores", {})
        for phase_key, phase_data in scores.items():
            if not phase_key.startswith("PHASE"):
                continue
            conf = phase_data.get("confidence", 3)
            print(
                f"    - Score: {phase_data.get('score', 0)} "
                f"{_confidence_emoji(conf)} (confidence: {conf}/5)"
            )
            # Show reasoning if available
            reasoning = phase_data.get("reasoning", "")
            if reasoning:
                print(
                    f"    - Reasoning: {reasoning[:120]}..."
                    if len(reasoning) > 120
                    else f"    - Reasoning: {reasoning}"
                )
            details = phase_data.get("details", {})
            for sub_key, sub_val in details.items():
                sub_conf = sub_val.get("confidence", 3)
                print(
                    f"      > {sub_key.replace('_', ' ').title()}: "
                    f"{sub_val.get('score', 0)}đ "
                    f"{_confidence_emoji(sub_conf)}"
                )
                if "feedback" in sub_val:
                    fb = sub_val["feedback"]
                    print(
                        f"        {fb[:100]}..."
                        if len(fb) > 100
                        else f"        {fb}"
                    )

    elif node_name == "validator":
        vr = data.get("validation_result", {})
        is_consistent = vr.get("is_consistent", True)
        anomalies = vr.get("anomalies", [])
        print(
            f"    - Consistent: {'✅ Yes' if is_consistent else '⚠️ No'}"
        )
        if anomalies:
            for a in anomalies:
                print(f"    - ⚠️ {a}")
        adj = vr.get("adjustments", {})
        if adj:
            for k, v in adj.items():
                if v != 0:
                    print(f"    - Adjustment: {k} → {v:+d}")

    elif node_name == "jd_analyzer":
        jd = data.get("jd_analysis")
        if jd is None:
            print("    - Skipped (no JD provided)")
        else:
            print(f"    - Match Score: {jd.get('match_score', 0)}%")
            print(
                f"    - Recommendation: {jd.get('recommendation', 'N/A')}"
            )
            print(
                f"    - Matched: {', '.join(jd.get('matched_skills', [])[:5])}"
            )
            print(
                f"    - Missing: {', '.join(jd.get('missing_skills', [])[:5])}"
            )

    elif node_name == "meta_evaluator":
        scores = data.get("scores", {})
        meta = scores.get("META", {})
        conf = meta.get("confidence", 3)
        print(
            f"    - FINAL SCORE: {meta.get('final_score', 0)}/100 "
            f"{_confidence_emoji(conf)} (confidence: {conf}/5)"
        )
        summary = meta.get("summary", "")
        print(
            f"    - Summary: {summary[:150]}..."
            if len(summary) > 150
            else f"    - Summary: {summary}"
        )

    elif node_name == "output_generator":
        print("    - HTML report generated.")

    # Print errors
    errors = data.get("errors", [])
    if errors:
        for err in errors:
            print(f"  - [!] Error: {err}")


def run_refinement_test():
    """
    Executes a full pipeline test of the v2.0 AI Core with:
    - Parallel evaluation (Phase 2, 3, 4)
    - Confidence scoring
    - Cross-phase validation
    - Detailed streaming logs
    """
    # Set correlation ID for this test run
    correlation_id = set_correlation_id()

    # Path to sample resume
    pdf_path = os.path.join(
        project_root,
        "data",
        "samples",
        "Nguyen-Thanh-Duy-Tan-Fullstack-Intern.pdf",
    )

    if not os.path.exists(pdf_path):
        print(f"Error: Sample resume not found at {pdf_path}")
        return

    print("=" * 50)
    print("[*] STARTING AI CORE PIPELINE v2.0")
    print("=" * 50)
    print(f"[*] Target CV: {os.path.basename(pdf_path)}")
    print(f"[*] Correlation ID: {correlation_id}")
    print(f"[*] Features: Parallel Eval | Confidence | Validation")
    print("-" * 50)

    initial_state = {
        "raw_text": pdf_path,
        "messages": [],
        "errors": [],
        "scores": {},
        "text_insights": {},
        "confidence_scores": {},
        "candidate_name": "N/A",
        "candidate_level": "Unknown",
        "industry": "N/A",
        "dynamic_rubric": "",
        "jd_text": "",  # Empty = no JD matching
        "jd_analysis": None,
        "validation_result": None,
        "processing_metadata": {
            "correlation_id": correlation_id,
            "pipeline_version": "2.0.0",
        },
    }

    start_time = datetime.now()
    try:
        final_state = dict(initial_state)
        # Use stream to log step-by-step
        for event in cv_graph.stream(
            initial_state, stream_mode="updates"
        ):
            for node_name, state_update in event.items():
                print_step(node_name, state_update)

                # Accumulate state updates
                for key, value in state_update.items():
                    if (
                        isinstance(value, dict)
                        and key in final_state
                        and isinstance(final_state[key], dict)
                    ):
                        final_state[key].update(value)
                    elif (
                        isinstance(value, list)
                        and key in final_state
                        and isinstance(final_state[key], list)
                    ):
                        if key == "errors":
                            final_state[key].extend(value)
                        else:
                            final_state[key] = value
                    else:
                        final_state[key] = value

    except Exception as e:
        print(f"\n❌ Critical Failure during graph execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'=' * 50}")
    print(f"[*] Pipeline completed in {duration:.2f} seconds.")
    print(f"{'=' * 50}")

    # Summary
    meta = final_state.get("scores", {}).get("META", {})
    print(f"\n📊 Final Score: {meta.get('final_score', 0)}/100")
    print(
        f"🎯 Confidence: {meta.get('confidence', 'N/A')}/5"
    )

    # Validation summary
    vr = final_state.get("validation_result", {})
    if vr:
        print(
            f"✅ Validation: {'Consistent' if vr.get('is_consistent') else 'Anomalies detected'}"
        )

    # Error summary
    all_errors = final_state.get("errors", [])
    if all_errors:
        print(f"\n⚠️ Errors ({len(all_errors)}):")
        for err in all_errors:
            print(f"  - {err}")

    # Export findings
    output_json = os.path.join(
        project_root, "data", "output", "test_results.json"
    )
    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    with open(output_json, "w", encoding="utf-8") as f:
        export_data = {
            "pipeline_version": "2.0.0",
            "correlation_id": correlation_id,
            "duration_s": round(duration, 2),
            "candidate_name": final_state.get("candidate_name"),
            "candidate_level": final_state.get("candidate_level"),
            "industry": final_state.get("industry"),
            "dynamic_rubric": final_state.get("dynamic_rubric"),
            "scores": final_state.get("scores", {}),
            "confidence_scores": final_state.get("confidence_scores", {}),
            "validation_result": final_state.get("validation_result"),
            "jd_analysis": final_state.get("jd_analysis"),
            "sections_found": list(
                final_state.get("sections", {}).keys()
            ),
            "processing_metadata": final_state.get(
                "processing_metadata", {}
            ),
            "errors": final_state.get("errors", []),
        }
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full results saved to: {output_json}")
    print(
        f"🌐 HTML Report saved to: "
        f"{os.path.join(project_root, 'data', 'output', 'report_output.html')}"
    )


if __name__ == "__main__":
    run_refinement_test()
