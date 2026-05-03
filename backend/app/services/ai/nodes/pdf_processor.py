"""
PDF Processor Node — Extracts, cleans, and structures text from CV PDFs.
"""

import os
import time

import pymupdf4llm

from app.services.ai.helpers.cleaner import CVTextCleaner
from app.services.ai.state import AgentState
from app.core.logging_config import pipeline_logger


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
                sections[current_canonical] = "\n".join(
                    current_content
                ).strip()

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
    Validates file existence and type before processing.
    """
    start = time.time()
    pipeline_logger.node_start("pdf_processor")

    file_path = state.get("raw_text")

    if not file_path:
        pipeline_logger.node_error(
            "pdf_processor", "No file path provided"
        )
        return {"errors": ["PDF Processor: No file path provided."]}

    # Validate file exists
    if not os.path.exists(file_path):
        pipeline_logger.node_error(
            "pdf_processor", f"File not found: {file_path}"
        )
        return {"errors": [f"PDF Processor: File not found: {file_path}"]}

    # Validate file extension
    if not file_path.lower().endswith(".pdf"):
        pipeline_logger.node_error(
            "pdf_processor", f"Invalid file type: {file_path}"
        )
        return {
            "errors": [
                f"PDF Processor: Only PDF files are supported. Got: {file_path}"
            ]
        }

    # Validate file size (max 10MB)
    file_size = os.path.getsize(file_path)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        pipeline_logger.node_error(
            "pdf_processor",
            f"File too large: {file_size / 1024 / 1024:.1f}MB",
        )
        return {
            "errors": [
                f"PDF Processor: File too large ({file_size / 1024 / 1024:.1f}MB). Max: 10MB."
            ]
        }

    try:
        raw_text = pymupdf4llm.to_text(file_path)
        cleaner = CVTextCleaner()
        cleaned_text = cleaner.clean(raw_text)
        sections = parse_sections(cleaned_text, cleaner)

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            "pdf_processor",
            duration_ms=duration_ms,
        )

        return {
            "cleaned_text": cleaned_text,
            "sections": sections,
            "processing_metadata": {
                "pdf_processor_duration_ms": round(duration_ms, 2),
                "cv_file_size_bytes": file_size,
                "cv_filename": os.path.basename(file_path),
                "sections_found": list(sections.keys()),
                "raw_text_length": len(raw_text),
                "cleaned_text_length": len(cleaned_text),
            },
            "errors": [],
        }

    except Exception as e:
        pipeline_logger.node_error("pdf_processor", str(e))
        return {"errors": [f"PDF Processor error: {str(e)}"]}
