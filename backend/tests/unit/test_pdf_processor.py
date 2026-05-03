"""
Unit Tests for PDF Processor Node.
Tests section parsing logic with mocked PDF data.
"""

import pytest
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.services.ai.helpers.cleaner import CVTextCleaner
from app.services.ai.nodes.pdf_processor import parse_sections


@pytest.fixture
def cleaner():
    return CVTextCleaner()


class TestParseSections:
    def test_parses_basic_sections(self, cleaner):
        text = """UNCLASSIFIED content here

SKILLS
Python, JavaScript, React, Docker

EXPERIENCE
Software Engineer at Google
2020 - Present

EDUCATION
BS Computer Science - MIT
"""
        sections = parse_sections(text, cleaner)
        assert "SKILLS" in sections
        assert "EXPERIENCE" in sections
        assert "EDUCATION" in sections
        assert "Python" in sections["SKILLS"]

    def test_handles_empty_text(self, cleaner):
        sections = parse_sections("", cleaner)
        assert sections == {} or sections == {"UNCLASSIFIED": ""}

    def test_handles_no_sections(self, cleaner):
        text = "Just some random text without any section headers"
        sections = parse_sections(text, cleaner)
        assert "UNCLASSIFIED" in sections

    def test_handles_vietnamese_headers(self, cleaner):
        text = """Nguyen Van A

KỸ NĂNG
Python, Java, Docker

HỌC VẤN
Đại học Bách Khoa

DỰ ÁN
Hệ thống quản lý
"""
        sections = parse_sections(text, cleaner)
        assert "SKILLS" in sections  # Mapped from KỸ NĂNG
        assert "EDUCATION" in sections  # Mapped from HỌC VẤN
        assert "PROJECTS" in sections  # Mapped from DỰ ÁN

    def test_preserves_section_content(self, cleaner):
        text = """SKILLS
Python, JavaScript, React
Docker, Kubernetes
AWS, GCP
"""
        sections = parse_sections(text, cleaner)
        assert "Python" in sections.get("SKILLS", "")
        assert "Docker" in sections.get("SKILLS", "")
        assert "AWS" in sections.get("SKILLS", "")

    def test_multiple_sections_no_overlap(self, cleaner):
        text = """SKILLS
Skill content

EXPERIENCE
Experience content

PROJECTS
Project content
"""
        sections = parse_sections(text, cleaner)
        assert "Skill content" in sections.get("SKILLS", "")
        assert "Experience content" in sections.get("EXPERIENCE", "")
        assert "Project content" in sections.get("PROJECTS", "")
        # Ensure no cross-contamination
        assert "Experience" not in sections.get("SKILLS", "")


class TestPdfProcessorNode:
    def test_rejects_missing_file(self):
        from app.services.ai.nodes.pdf_processor import pdf_processor_node

        result = pdf_processor_node(
            {"raw_text": "/nonexistent/path.pdf", "errors": []}
        )
        assert len(result.get("errors", [])) > 0

    def test_rejects_non_pdf(self):
        from app.services.ai.nodes.pdf_processor import pdf_processor_node

        # Create a temp txt file
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as f:
            f.write(b"Not a PDF")
            temp_path = f.name

        try:
            result = pdf_processor_node(
                {"raw_text": temp_path, "errors": []}
            )
            assert len(result.get("errors", [])) > 0
        finally:
            os.unlink(temp_path)

    def test_rejects_empty_path(self):
        from app.services.ai.nodes.pdf_processor import pdf_processor_node

        result = pdf_processor_node({"raw_text": "", "errors": []})
        assert len(result.get("errors", [])) > 0
