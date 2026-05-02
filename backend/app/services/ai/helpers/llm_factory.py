import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage
import copy

def invoke_structured(llm, pydantic_class, messages):
    """
    Safely invokes an LLM to return a Pydantic object.
    Falls back to JsonOutputParser if the model lacks native tool calling.
    """
    is_hf = "ChatHuggingFace" in str(type(llm))
    
    if is_hf:
        parser = JsonOutputParser(pydantic_object=pydantic_class)
        format_instructions = parser.get_format_instructions()
        
        new_messages = copy.deepcopy(messages)
        for msg in new_messages:
            if isinstance(msg, SystemMessage):
                msg.content += f"\n\nCRITICAL: You MUST output ONLY valid JSON. {format_instructions}"
                break
        else:
            new_messages.insert(0, SystemMessage(content=f"CRITICAL: You MUST output ONLY valid JSON. {format_instructions}"))
            
        result_msg = llm.invoke(new_messages)
        result_dict = parser.invoke(result_msg)
        return pydantic_class(**result_dict)
    else:
        structured_llm = llm.with_structured_output(pydantic_class)
        return structured_llm.invoke(messages)

def get_llm(temperature: float = 0.2):
    """
    Factory function to create an LLM instance.
    Prioritizes Qwen if USE_QWEN=true, else uses Gemini.
    """
    use_qwen = os.getenv("USE_QWEN", "false").lower() == "true"
    
    if use_qwen:
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise ValueError("HuggingFace token not found. Please set HF_TOKEN in .env")
        
        # Using Qwen2.5 as it's the current standard
        model_id = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        
        llm = HuggingFaceEndpoint(
            repo_id=model_id,
            huggingfacehub_api_token=token,
            temperature=temperature,
            max_new_tokens=1024,
            timeout=300
        )
        return ChatHuggingFace(llm=llm)
    
    # Gemini logic
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API Key not found. Please check .env")

    # Prioritize GEMINI_MODEL from .env as it seems to be the working one for the user
    model_name = os.getenv("GEMINI_MODEL") or os.getenv("AI_MODEL_FLASH") or "gemini-1.5-flash-latest"
        
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature
    )

def get_pro_llm(temperature: float = 0.2):
    """
    Factory for Pro/Meta reasoning.
    """
    # If using Qwen, we use the same endpoint
    if os.getenv("USE_QWEN", "false").lower() == "true":
        return get_llm(temperature=temperature)
        
    model_name = os.getenv("AI_MODEL_PRO") or os.getenv("GEMINI_MODEL") or "gemini-1.5-pro-latest"
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature
    )
