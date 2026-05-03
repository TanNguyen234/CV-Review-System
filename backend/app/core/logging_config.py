"""
Structured logging configuration for the CV AI Evaluation System.
Provides JSON-formatted logs with correlation IDs for request tracing.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

# Context variable for correlation ID (async-safe)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for a pipeline run."""
    return str(uuid.uuid4())[:12]


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set correlation ID in context. Returns the ID."""
    cid = cid or generate_correlation_id()
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_var.get()


class PipelineLogger:
    """
    Structured logger for the AI pipeline.
    Logs node executions with timing, scores, and correlation IDs.
    """

    def __init__(self, name: str = "cv_pipeline"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _build_entry(self, level: str, event: str, **kwargs) -> dict:
        """Build a structured log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "correlation_id": get_correlation_id(),
        }
        entry.update(kwargs)
        return entry

    def node_start(self, node_name: str, **extra):
        """Log when a pipeline node starts execution."""
        entry = self._build_entry(
            "INFO",
            "node_start",
            node=node_name,
            **extra,
        )
        self.logger.info(str(entry))

    def node_complete(
        self,
        node_name: str,
        duration_ms: float,
        score: Optional[int] = None,
        **extra,
    ):
        """Log when a pipeline node completes."""
        entry = self._build_entry(
            "INFO",
            "node_complete",
            node=node_name,
            duration_ms=round(duration_ms, 2),
            **extra,
        )
        if score is not None:
            entry["score"] = score
        self.logger.info(str(entry))

    def node_error(self, node_name: str, error: str, retryable: bool = False, **extra):
        """Log a node error."""
        entry = self._build_entry(
            "ERROR",
            "node_error",
            node=node_name,
            error=error,
            retryable=retryable,
            **extra,
        )
        self.logger.error(str(entry))

    def pipeline_start(self, cv_filename: str, has_jd: bool = False, **extra):
        """Log pipeline start."""
        entry = self._build_entry(
            "INFO",
            "pipeline_start",
            cv_filename=cv_filename,
            has_jd=has_jd,
            **extra,
        )
        self.logger.info(str(entry))

    def pipeline_complete(self, duration_s: float, final_score: int, **extra):
        """Log pipeline completion."""
        entry = self._build_entry(
            "INFO",
            "pipeline_complete",
            duration_s=round(duration_s, 2),
            final_score=final_score,
            **extra,
        )
        self.logger.info(str(entry))

    def llm_call(self, model: str, node: str, tokens_in: int = 0, **extra):
        """Log an LLM API call."""
        entry = self._build_entry(
            "DEBUG",
            "llm_call",
            model=model,
            node=node,
            tokens_in=tokens_in,
            **extra,
        )
        self.logger.debug(str(entry))


# Singleton logger
pipeline_logger = PipelineLogger()
