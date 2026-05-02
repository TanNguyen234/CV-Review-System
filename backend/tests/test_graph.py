import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from app.services.ai.graph import cv_graph

# Load environment variables
# Note: .env is in the root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

# Map env variables
if "GEMINI_API" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API"]
if "TAVILY_API" in os.environ and "TAVILY_API_KEY" not in os.environ:
    os.environ["TAVILY_API_KEY"] = os.environ["TAVILY_API"]

def run_test():
    # Use the sample resume provided in the data/samples folder
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_path = os.path.join(project_root, "data", "samples", "resume-analysis-report-79055eb7-7629-413d-9179-b4752a9875d2 (2)_1.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"Test file not found at {pdf_path}")
        return
        
    print(f"Running CV Analysis on {os.path.basename(pdf_path)}...")
    print("This may take a minute as multiple AI agents evaluate the sections...")
    
    # Initialize state
    initial_state = {
        "raw_text": pdf_path,
        "messages": [],
        "errors": []
    }
    
    # Run graph
    try:
        final_state = cv_graph.invoke(initial_state)
        
        print("\n--- RESULTS ---")
        if final_state.get("errors"):
            print("Errors encountered:")
            for err in final_state["errors"]:
                print(f"- {err}")
            
        print("\nFinal Score:", final_state.get("scores", {}).get("META", {}).get("final_score", "N/A"))
        print("\nExtracted Sections:", list(final_state.get("sections", {}).keys()))
        
        html_out = os.path.join(project_root, "data", "output", "report_output.html")
        with open(html_out, "w", encoding="utf-8") as f:
            f.write(final_state.get("report_html", "No HTML generated."))
            
        print(f"\nReport successfully saved to {html_out}")
        
    except Exception as e:
        print(f"Graph execution failed: {e}")

if __name__ == "__main__":
    run_test()
