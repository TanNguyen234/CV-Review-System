"""
Validation Node — Cross-phase consistency checker.
Acts as a "referee" to detect anomalies between evaluation phases.
"""

import time
from app.services.ai.state import AgentState
from app.core.logging_config import pipeline_logger


# Phase weight configuration (max scores)
PHASE_MAX_SCORES = {
    "PHASE2": 60,
    "PHASE3": 30,
    "PHASE4": 10,
}

# Anomaly detection thresholds
CONSISTENCY_THRESHOLD = 0.3  # Flag if phases differ by more than 30% in relative scoring


def _calculate_relative_score(score: int, max_score: int) -> float:
    """Calculate score as a percentage of max."""
    if max_score == 0:
        return 0.0
    return score / max_score


def _detect_anomalies(scores: dict) -> list[str]:
    """
    Detect scoring anomalies across phases.
    Returns list of anomaly descriptions.
    """
    anomalies = []

    relative_scores = {}
    for phase, max_score in PHASE_MAX_SCORES.items():
        phase_data = scores.get(phase, {})
        score = phase_data.get("score", 0)
        relative_scores[phase] = _calculate_relative_score(score, max_score)

    # Check for large discrepancies between Phase 2 and Phase 3
    if "PHASE2" in relative_scores and "PHASE3" in relative_scores:
        diff = abs(relative_scores["PHASE2"] - relative_scores["PHASE3"])
        if diff > CONSISTENCY_THRESHOLD:
            anomalies.append(
                f"Chênh lệch lớn giữa Phase 2 ({relative_scores['PHASE2']:.0%}) "
                f"và Phase 3 ({relative_scores['PHASE3']:.0%}). "
                f"Độ lệch: {diff:.0%}"
            )

    # Check for suspiciously perfect scores
    for phase, max_score in PHASE_MAX_SCORES.items():
        phase_data = scores.get(phase, {})
        score = phase_data.get("score", 0)
        if score == max_score:
            anomalies.append(
                f"{phase} đạt điểm tối đa ({score}/{max_score}). "
                f"Cần kiểm tra tính chính xác."
            )

    # Check for zero scores with high confidence (suspicious)
    for phase in PHASE_MAX_SCORES:
        phase_data = scores.get(phase, {})
        score = phase_data.get("score", 0)
        confidence = phase_data.get("confidence", 3)
        if score == 0 and confidence >= 4 and phase != "PHASE4":
            anomalies.append(
                f"{phase} = 0 điểm nhưng confidence = {confidence}. "
                f"Có thể LLM đã hiểu sai yêu cầu."
            )

    # Check total doesn't exceed 100
    total = sum(
        scores.get(phase, {}).get("score", 0)
        for phase in PHASE_MAX_SCORES
    )
    if total > 100:
        anomalies.append(
            f"Tổng điểm các phase = {total}/100. Vượt quá thang 100."
        )

    return anomalies


def _validate_confidence(scores: dict) -> dict[str, int]:
    """
    Check confidence scores and suggest adjustments for low-confidence phases.
    Returns suggested score adjustments (can be negative).
    """
    adjustments = {}

    for phase in PHASE_MAX_SCORES:
        phase_data = scores.get(phase, {})
        confidence = phase_data.get("confidence", 3)
        score = phase_data.get("score", 0)

        # If confidence is very low (1-2), suggest conservative adjustment
        if confidence <= 2 and score > 0:
            # Reduce score by 10-20% for low confidence
            reduction = int(score * 0.15)
            if reduction > 0:
                adjustments[phase] = -reduction

    return adjustments


def validator_node(state: AgentState) -> dict:
    """
    Cross-phase validation node.
    Checks consistency, detects anomalies, and validates confidence levels.
    """
    start = time.time()
    pipeline_logger.node_start("validator")

    scores = state.get("scores", {})

    # Detect anomalies
    anomalies = _detect_anomalies(scores)

    # Validate confidence
    adjustments = _validate_confidence(scores)

    # Determine overall consistency
    is_consistent = len(anomalies) == 0

    # Build validation notes
    notes_parts = []
    if is_consistent:
        notes_parts.append("Các đánh giá nhất quán, không phát hiện bất thường.")
    else:
        notes_parts.append(
            f"Phát hiện {len(anomalies)} bất thường cần xem xét."
        )

    if adjustments:
        adj_details = ", ".join(
            f"{k}: {v:+d}" for k, v in adjustments.items()
        )
        notes_parts.append(f"Đề xuất điều chỉnh: {adj_details}")

    duration_ms = (time.time() - start) * 1000
    pipeline_logger.node_complete("validator", duration_ms=duration_ms)

    return {
        "validation_result": {
            "is_consistent": is_consistent,
            "anomalies": anomalies,
            "adjustments": adjustments,
            "validation_notes": " ".join(notes_parts),
        },
        "processing_metadata": {
            "validator_duration_ms": round(duration_ms, 2),
            "anomalies_found": len(anomalies),
        },
        "errors": [],
    }
