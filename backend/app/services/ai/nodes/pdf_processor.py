import pymupdf4llm
from app.services.ai.helpers.cleaner import CVTextCleaner
from app.services.ai.state import AgentState

def parse_sections(cleaned_text: str, cleaner: CVTextCleaner) -> dict:
    """
    Parses cleaned text into a dictionary of sections based on canonical mapping.
    """
    sections = {}
    current_canonical = "UNCLASSIFIED"
    lines = cleaned_text.split("\n")
    
    current_content = []
    
    # Create a reverse mapping for quick lookup: keyword (upper) -> canonical name
    reverse_map = {}
    for canonical, keywords in cleaner.section_mapping.items():
        for kw in keywords:
            reverse_map[kw.upper()] = canonical
            
    for line in lines:
        line_stripped = line.strip()
        line_upper = line_stripped.upper()
        
        if line_upper in reverse_map:
            # Save previous section
            if current_content:
                sections[current_canonical] = "\n".join(current_content).strip()
            
            # Switch to new canonical section
            current_canonical = reverse_map[line_upper]
            current_content = []
        else:
            current_content.append(line)
            
    # Save the last section
    if current_content:
        sections[current_canonical] = "\n".join(current_content).strip()
        
    return sections

def pdf_processor_node(state: AgentState) -> dict:
    """
    Node to extract and clean text from CV PDF.
    """
    file_path = state.get("raw_text")
    errors = state.get("errors", [])
    
    if not file_path:
        errors.append("PDF Processor: No file path provided.")
        return {"errors": errors}
        
    try:
        raw_text = pymupdf4llm.to_text(file_path)
        cleaner = CVTextCleaner()
        cleaned_text = cleaner.clean(raw_text)
        sections = parse_sections(cleaned_text, cleaner)
        
        return {
            "cleaned_text": cleaned_text,
            "sections": sections,
            "errors": errors
        }
    except Exception as e:
        errors.append(f"PDF Processor error: {str(e)}")
        return {"errors": errors}
