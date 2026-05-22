import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from app.services.security import check_rate_limit, validate_cv_spam

@pytest.mark.asyncio
async def test_check_rate_limit_success():
    """Test rate limiting allows requests under the limit."""
    with patch("app.services.security.db_manager.db") as mock_db:
        mock_col = AsyncMock()
        # Not found means under limit
        mock_col.find_one.return_value = None
        mock_db.__getitem__.return_value = mock_col
        
        result = await check_rate_limit("192.168.1.1", max_requests=5)
        assert result is True
        mock_col.insert_one.assert_called_once()

@pytest.mark.asyncio
async def test_check_rate_limit_exceeded():
    """Test rate limiting blocks requests over the limit."""
    with patch("app.services.security.db_manager.db") as mock_db:
        mock_col = AsyncMock()
        # Found with count >= max
        mock_col.find_one.return_value = {"_id": "test_id", "request_count": 5}
        mock_db.__getitem__.return_value = mock_col
        
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("192.168.1.2", max_requests=5)
            
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)

@pytest.mark.asyncio
@patch("langchain_core.runnables.RunnableSequence.ainvoke")
@patch("app.services.security.pymupdf4llm.to_markdown")
async def test_validate_cv_spam_valid_chain(mock_to_markdown, mock_ainvoke, tmp_path):
    mock_to_markdown.return_value = "John Doe Software Engineer"
    
    class MockResult:
        content = "IS_CV: YES\nREASON: Looks like a valid software engineer CV."
    
    mock_ainvoke.return_value = MockResult()
    
    pdf_path = tmp_path / "valid.pdf"
    pdf_path.write_bytes(b"dummy")
    
    is_cv, reason = await validate_cv_spam(str(pdf_path))
    
    assert is_cv is True
    assert "Looks like a valid software engineer CV" in reason

@pytest.mark.asyncio
@patch("langchain_core.runnables.RunnableSequence.ainvoke")
@patch("app.services.security.pymupdf4llm.to_markdown")
async def test_validate_cv_spam_invalid_chain(mock_to_markdown, mock_ainvoke, tmp_path):
    mock_to_markdown.return_value = "Restaurant Menu..."
    
    class MockResult:
        content = "IS_CV: NO\nREASON: This is a menu, not a CV."
        
    mock_ainvoke.return_value = MockResult()
    
    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_bytes(b"dummy")
    
    is_cv, reason = await validate_cv_spam(str(pdf_path))
    
    assert is_cv is False
    assert "This is a menu, not a CV" in reason


@pytest.mark.asyncio
@patch("langchain_core.runnables.RunnableSequence.ainvoke")
@patch("app.services.security.pymupdf4llm.to_markdown")
@patch("app.services.security.get_llm")
async def test_validate_cv_spam_calls_get_llm(mock_get_llm, mock_to_markdown, mock_ainvoke, tmp_path):
    mock_to_markdown.return_value = "Some text"
    mock_ainvoke.return_value = AsyncMock(content="IS_CV: YES\nREASON: Standard resume")
    
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"dummy")
    
    await validate_cv_spam(str(pdf_path))
    
    mock_get_llm.assert_called_once_with(temperature=0.0)
