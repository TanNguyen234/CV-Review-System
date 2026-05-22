"""
LLM Factory — Creates and manages LLM instances.
Supports Gemini and HuggingFace with structured output fallback.
"""

import copy
import re
import json
import time
from typing import Type, TypeVar

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging_config import pipeline_logger

T = TypeVar("T", bound=BaseModel)


class LLMTransientError(Exception):
    """Transient error that should trigger a retry (timeout, rate limit, 503)."""
    pass


class LLMPermanentError(Exception):
    """Permanent error that should NOT be retried (bad key, invalid request)."""
    pass


def _classify_and_raise(error: Exception, node_name: str = "unknown") -> None:
    """
    Classify an exception as transient or permanent and raise the appropriate type.
    """
    error_str = str(error).lower()
    transient_indicators = [
        "timeout", "rate limit", "429", "503", "504",
        "service unavailable", "resource exhausted",
        "overloaded", "too many requests", "deadline exceeded",
        "connection", "temporary", "retry",
    ]

    is_transient = any(indicator in error_str for indicator in transient_indicators)

    pipeline_logger.node_error(
        node_name,
        str(error),
        retryable=is_transient,
    )

    if is_transient:
        raise LLMTransientError(f"Transient LLM error: {error}") from error
    else:
        raise LLMPermanentError(f"Permanent LLM error: {error}") from error


def _extract_json_block(text: str) -> dict:
    """
    Robustly extracts and parses a JSON object from text.
    Handles markdown code blocks, surrounding text, trailing commas,
    and minor formatting issues.
    """
    text_clean = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        pass

    # Extract content from markdown blocks if present
    markdown_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_clean, re.DOTALL | re.IGNORECASE)
    if markdown_match:
        content = markdown_match.group(1).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            text_clean = content

    # Find the outer-most { and } braces
    first_brace = text_clean.find('{')
    last_brace = text_clean.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text_clean[first_brace:last_brace+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Try to fix common JSON issues like trailing commas
        fixed_json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        try:
            return json.loads(fixed_json_str)
        except json.JSONDecodeError:
            pass

        # Try to replace single quotes with double quotes for keys and values
        fixed_quotes = json_str
        # Replace single quotes wrapping keys: 'key': -> "key":
        fixed_quotes = re.sub(r"'\s*(\w+)\s*'\s*:", r'"\1":', fixed_quotes)
        # Replace single quotes wrapping string values: : 'value' -> : "value"
        fixed_quotes = re.sub(r":\s*'([^']*)'", r': "\1"', fixed_quotes)
        # Replace single quotes wrapping string values in arrays: ['value1', 'value2']
        fixed_quotes = re.sub(r"'\s*([^']*)\s*'\s*([,\]])", r'"\1"\2', fixed_quotes)
        # Clean trailing commas from this as well
        fixed_quotes = re.sub(r',\s*([\]}])', r'\1', fixed_quotes)
        try:
            return json.loads(fixed_quotes)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:200]}...")


def invoke_structured(
    llm,
    pydantic_class: Type[T],
    messages: list,
    node_name: str = "unknown",
) -> T:
    """
    Safely invokes an LLM to return a Pydantic object.
    Falls back to JsonOutputParser if the model lacks native tool calling.
    Classifies errors for retry policy compatibility.
    """
    is_hf = "ChatHuggingFace" in str(type(llm))
    start = time.time()

    try:
        if is_hf:
            parser = JsonOutputParser(pydantic_object=pydantic_class)
            format_instructions = parser.get_format_instructions()

            new_messages = copy.deepcopy(messages)
            for msg in new_messages:
                if isinstance(msg, SystemMessage):
                    msg.content += (
                        f"\n\nCRITICAL: You MUST output ONLY valid JSON. "
                        f"{format_instructions}"
                    )
                    break
            else:
                new_messages.insert(
                    0,
                    SystemMessage(
                        content=f"CRITICAL: You MUST output ONLY valid JSON. "
                        f"{format_instructions}"
                    ),
                )

            result_msg = llm.invoke(new_messages)
            content = result_msg.content if hasattr(result_msg, "content") else str(result_msg)
            result_dict = _extract_json_block(content)
            result = pydantic_class(**result_dict)
        else:
            # Try structured output first (Gemini function calling)
            try:
                structured_llm = llm.with_structured_output(pydantic_class)
                result = structured_llm.invoke(messages)
            except Exception as struct_err:
                # Fallback: ask for JSON directly and parse
                pipeline_logger.node_error(
                    node_name,
                    f"Structured output failed, trying JSON fallback: {struct_err}",
                    retryable=True,
                )
                parser = JsonOutputParser(pydantic_object=pydantic_class)
                format_instructions = parser.get_format_instructions()

                fallback_messages = copy.deepcopy(messages)
                for msg in fallback_messages:
                    if isinstance(msg, SystemMessage):
                        msg.content += (
                            f"\n\nCRITICAL: You MUST output ONLY valid JSON. "
                            f"{format_instructions}"
                        )
                        break

                result_msg = llm.invoke(fallback_messages)
                content = result_msg.content if hasattr(result_msg, "content") else str(result_msg)
                result_dict = _extract_json_block(content)
                result = pydantic_class(**result_dict)

            if result is None:
                raise LLMPermanentError(
                    f"LLM returned None for structured output in {node_name}"
                )

        duration_ms = (time.time() - start) * 1000
        pipeline_logger.node_complete(
            node_name,
            duration_ms=duration_ms,
        )
        return result

    except (LLMTransientError, LLMPermanentError):
        raise  # Already classified, re-raise as-is
    except Exception as e:
        _classify_and_raise(e, node_name)



def get_llm(temperature: float | None = None):
    """
    Factory function to create an LLM instance.
    Prioritizes Qwen if USE_QWEN=true, else uses Gemini.
    """
    temp = temperature if temperature is not None else settings.llm_temperature

    if settings.use_qwen:
        if not settings.hf_token:
            raise LLMPermanentError(
                "HuggingFace token not found. Please set HF_TOKEN in .env"
            )

        llm = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_token,
            temperature=temp,
            max_new_tokens=4096,
            timeout=300,
        )
        return ChatHuggingFace(llm=llm)

    # Gemini logic
    api_key = settings.gemini_api_key
    if not api_key:
        raise LLMPermanentError(
            "Gemini API Key not found. Please set GEMINI_API_KEY in .env"
        )

    model_name = settings.gemini_model or settings.ai_model_flash

    pipeline_logger.llm_call(model=model_name, node="factory")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temp,
        max_output_tokens=8192,
    )


def get_pro_llm(temperature: float | None = None):
    """
    Factory for Pro/Meta reasoning — uses a more capable model.
    """
    temp = temperature if temperature is not None else settings.llm_temperature

    # If using Qwen, we use the same endpoint
    if settings.use_qwen:
        return get_llm(temperature=temp)

    model_name = settings.ai_model_pro or settings.gemini_model
    api_key = settings.gemini_api_key

    if not api_key:
        raise LLMPermanentError(
            "Gemini API Key not found. Please set GEMINI_API_KEY in .env"
        )

    pipeline_logger.llm_call(model=model_name, node="factory_pro")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temp,
        max_output_tokens=8192,
    )
