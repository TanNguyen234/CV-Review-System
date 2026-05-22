"""
Unit Tests for LLM Factory Helpers.
"""

import pytest
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.services.ai.helpers.llm_factory import _extract_json_block


class TestExtractJsonBlock:
    def test_extract_standard_json(self):
        text = '{"name": "Alice", "age": 30}'
        result = _extract_json_block(text)
        assert result == {"name": "Alice", "age": 30}

    def test_extract_markdown_json_block(self):
        text = 'Some introductory text...\n```json\n{"name": "Bob", "skills": ["Python", "JS"]}\n```\nSome trailing text.'
        result = _extract_json_block(text)
        assert result == {"name": "Bob", "skills": ["Python", "JS"]}

    def test_extract_markdown_no_json_prefix(self):
        text = '```\n{"name": "Charlie"}\n```'
        result = _extract_json_block(text)
        assert result == {"name": "Charlie"}

    def test_extract_outer_braces(self):
        text = 'Random text { "key": "value" } other random text.'
        result = _extract_json_block(text)
        assert result == {"key": "value"}

    def test_extract_with_trailing_commas(self):
        text = '{"key": "value", "list": [1, 2, 3,],}'
        result = _extract_json_block(text)
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_extract_with_single_quotes(self):
        text = "{'name': 'Dave', 'roles': ['admin', 'user']}"
        result = _extract_json_block(text)
        assert result == {"name": "Dave", "roles": ["admin", "user"]}

    def test_extract_invalid_json_raises_value_error(self):
        text = "This is not JSON at all."
        with pytest.raises(ValueError) as exc_info:
            _extract_json_block(text)
        assert "Could not extract valid JSON" in str(exc_info.value)
