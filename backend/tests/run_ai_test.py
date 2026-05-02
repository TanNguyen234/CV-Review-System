import os
import sys
import json
from datetime import datetime

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from app.services.ai.graph import cv_graph

def print_step(node_name, data):
    """Utility to print streaming steps beautifully."""
    print(f"\n[+] [{node_name.upper()}] completed.")
    
    # Custom logging per node
    if node_name == "pdf_processor":
        sections = data.get("sections", {}).keys()
        print(f"  - Found {len(sections)} sections: {', '.join(sections)}")
    elif node_name == "profiler":
        print(f"  - Candidate Level Detected: {data.get('candidate_level', 'Unknown')}")
        print(f"  - Dynamic Rubric: {data.get('dynamic_rubric', 'None')}")
    elif node_name.endswith("_eval"):
        section = node_name.split("_")[0].upper()
        if section == "EXPERIENCE": section = "EXPERIENCE"
        elif section == "PROJECT": section = "PROJECTS"
        elif section == "SKILL": section = "SKILLS"
        elif section == "EDUCATION": section = "EDUCATION"
        
        score_data = data.get("scores", {}).get(section, {})
        print(f"  - Score: {score_data.get('score', 0)}/20 (or /10)")
    elif node_name == "meta_evaluator":
        meta = data.get("scores", {}).get("META", {})
        print(f"  - Final Score Generated: {meta.get('final_score', 0)}/100")
        
    if data.get("errors"):
        for err in data["errors"]:
            print(f"  - [!] Error: {err}")

def run_refinement_test():
    """
    Executes a full pipeline test of the refined AI Core with detailed streaming logs.
    """
    # Load environment variables
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=env_path)
    
    # Path to sample resume
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_path = os.path.join(project_root, "data", "samples", "Nguyen-Thanh-Duy-Tan-Fullstack-Intern.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"Error: Sample resume not found at {pdf_path}")
        return

    print("========================================")
    print("[*] STARTING AI CORE PIPELINE")
    print("========================================")
    print(f"[*] Target CV: {os.path.basename(pdf_path)}")
    print("----------------------------------------")

    initial_state = {
        "raw_text": pdf_path,
        "messages": [],
        "errors": [],
        "scores": {},
        "text_insights": {},
        "candidate_level": "Unknown",
        "dynamic_rubric": ""
    }

    start_time = datetime.now()
    try:
        final_state = initial_state.copy()
        # Use stream to log step-by-step
        for event in cv_graph.stream(initial_state, stream_mode="updates"):
            for node_name, state_update in event.items():
                print_step(node_name, state_update)
                
                # Accumulate state updates
                for key, value in state_update.items():
                    if isinstance(value, dict) and key in final_state and isinstance(final_state[key], dict):
                        final_state[key].update(value)
                    elif isinstance(value, list) and key in final_state and isinstance(final_state[key], list):
                        # For messages, we might just append, but errors we extend
                        if key == "errors":
                            final_state[key].extend(value)
                        else:
                            final_state[key] = value # LangGraph add_messages handles sequences, for simple local dict we just overwrite or extend
                    else:
                        final_state[key] = value
                        
    except Exception as e:
        print(f"\n❌ Critical Failure during graph execution: {str(e)}")
        return

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n[*] Pipeline completed in {duration:.2f} seconds.")
    
    # Export findings
    output_json = os.path.join(project_root, "data", "output", "test_results.json")
    with open(output_json, "w", encoding="utf-8") as f:
        export_data = {
            "candidate_level": final_state.get("candidate_level"),
            "dynamic_rubric": final_state.get("dynamic_rubric"),
            "scores": final_state.get("scores", {}),
            "sections_found": list(final_state.get("sections", {}).keys()),
            "errors": final_state.get("errors", [])
        }
        json.dump(export_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 Full results saved to: {output_json}")
    print(f"🌐 HTML Report saved to: {os.path.join(project_root, 'data', 'output', 'report_output.html')}")

if __name__ == "__main__":
    run_refinement_test()
