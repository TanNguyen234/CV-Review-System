"""
Unit Tests for CVTextCleaner.
Tests artifact removal, whitespace normalization, section detection, and date normalization.
"""

import pytest
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.services.ai.helpers.cleaner import CVTextCleaner


@pytest.fixture
def cleaner():
    return CVTextCleaner()


class TestRemoveArtifacts:
    def test_removes_picture_text_markers(self, cleaner):
        text = "Hello ----- Start of picture text -----image data----- End of picture text ----- World"
        result = cleaner.remove_artifacts(text)
        assert "----- Start" not in result
        assert "image data" not in result
        assert "Hello" in result
        assert "World" in result

    def test_removes_page_numbers(self, cleaner):
        text = "Content here Page 1 of 3 more content"
        result = cleaner.remove_artifacts(text)
        assert "Page 1 of 3" not in result
        assert "Content here" in result

    def test_removes_arrow_markers(self, cleaner):
        text = "Before ==> some artifact <== After"
        result = cleaner.remove_artifacts(text)
        assert "==>" not in result
        assert "some artifact" not in result


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self, cleaner):
        text = "Hello     World"
        result = cleaner.normalize_whitespace(text)
        assert result == "Hello World"

    def test_replaces_nbsp(self, cleaner):
        text = "Hello\xa0World"
        result = cleaner.normalize_whitespace(text)
        assert "\xa0" not in result

    def test_collapses_tabs(self, cleaner):
        text = "Hello\t\tWorld"
        result = cleaner.normalize_whitespace(text)
        assert result == "Hello World"

    def test_strips_edges(self, cleaner):
        text = "   Hello   "
        result = cleaner.normalize_whitespace(text)
        assert result == "Hello"


class TestCleanSymbols:
    def test_removes_copyright(self, cleaner):
        result = cleaner.clean_symbols("Copyright © 2024")
        assert "©" not in result

    def test_removes_bullets(self, cleaner):
        result = cleaner.clean_symbols("• Item one • Item two")
        assert "•" not in result

    def test_replaces_pipes(self, cleaner):
        result = cleaner.clean_symbols("Name | Phone | Email")
        assert "|" not in result


class TestNormalizeDates:
    def test_normalizes_to_current(self, cleaner):
        result = cleaner.normalize_dates("01/2020 to CURRENT")
        assert "Present" in result
        assert "CURRENT" not in result

    def test_normalizes_date_ranges(self, cleaner):
        result = cleaner.normalize_dates("01/2020 to 12/2023")
        assert "01/2020 - 12/2023" in result


class TestSectionMapping:
    def test_has_required_sections(self, cleaner):
        required = ["OBJECTIVE", "SKILLS", "EXPERIENCE", "EDUCATION", "PROJECTS"]
        for section in required:
            assert section in cleaner.section_mapping

    def test_section_mapping_includes_vietnamese(self, cleaner):
        skills_keywords = cleaner.section_mapping["SKILLS"]
        assert "KỸ NĂNG" in skills_keywords

    def test_all_keywords_flattened(self, cleaner):
        total_keywords = sum(
            len(v) for v in cleaner.section_mapping.values()
        )
        assert len(cleaner.all_keywords) == total_keywords


class TestFullCleanPipeline:
    def test_clean_basic_cv_text(self, cleaner):
        raw = """
        John Doe © 2024
        Page 1 of 2

        SKILLS
        Python, JavaScript, React

        EXPERIENCE
        Software Engineer at Company
        01/2020 to CURRENT
        """
        result = cleaner.clean(raw)
        assert "©" not in result
        assert "Page 1 of 2" not in result
        assert "Python" in result
        assert "Present" in result

    def test_clean_empty_text(self, cleaner):
        result = cleaner.clean("")
        assert result == ""

    def test_clean_preserves_content(self, cleaner):
        raw = "Nguyen Van A\nSoftware Engineer\nPython, Java, Docker"
        result = cleaner.clean(raw)
        assert "Nguyen Van A" in result
        assert "Python" in result
