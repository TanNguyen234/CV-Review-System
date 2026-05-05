"""
Application Configuration using Pydantic Settings.
Validates all required environment variables at startup.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Typed, validated configuration for the CV AI Evaluation System."""

    # --- LLM Configuration ---
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Default Gemini model for evaluations",
    )
    ai_model_flash: str = Field(
        default="gemini-1.5-flash-latest",
        description="Fast model for extraction tasks",
    )
    ai_model_pro: str = Field(
        default="gemini-2.5-flash",
        description="Pro model for meta-evaluation",
    )

    # --- HuggingFace Configuration ---
    use_qwen: bool = Field(default=False, description="Use Qwen model via HuggingFace")
    hf_token: str = Field(default="", description="HuggingFace API token")
    hf_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="HuggingFace model ID",
    )

    # --- Tavily (RAG Enrichment) ---
    tavily_api_key: str = Field(default="", alias="TAVILY_API")

    # --- Application ---
    port: int = Field(default=3002)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3002"],
        description="Allowed CORS origins",
    )
    max_upload_size_mb: int = Field(default=10, description="Max PDF upload size in MB")

    # --- Database & Storage ---
    mongo_url: str = Field(default="", alias="MONGO_URL")
    cloud_name: str = Field(default="", alias="CLOUD_NAME")
    cloud_key: str = Field(default="", alias="CLOUD_KEY")
    cloud_secret: str = Field(default="", alias="CLOUD_SECRET")

    # --- Pipeline Tuning ---
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    llm_max_retries: int = Field(default=3, ge=1, le=5)
    llm_retry_initial_interval: float = Field(default=2.0)
    llm_retry_backoff_factor: float = Field(default=2.0)
    pipeline_max_concurrency: int = Field(
        default=3,
        description="Max concurrent LLM calls during parallel evaluation",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "case_sensitive": False,
    }

    def validate_llm_keys(self) -> None:
        """Validate that at least one LLM provider is configured."""
        if self.use_qwen and not self.hf_token:
            raise ValueError(
                "USE_QWEN=true but HF_TOKEN is not set. "
                "Please set HF_TOKEN in your .env file."
            )
        if not self.use_qwen and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please set GEMINI_API_KEY in your .env file or enable USE_QWEN."
            )


def get_settings() -> Settings:
    """
    Factory function to create Settings instance.
    Searches for .env in project root.
    """
    # Find project root (where .env lives)
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            return Settings(_env_file=env_path)
        current = os.path.dirname(current)

    return Settings()


# Singleton settings instance
settings = get_settings()
