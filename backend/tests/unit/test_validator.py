"""
Unit Tests for Validator Node.
Tests cross-phase consistency checking and anomaly detection.
"""

import pytest
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.services.ai.nodes.validator import (
    validator_node,
    _detect_anomalies,
    _validate_confidence,
    _calculate_relative_score,
)


class TestRelativeScore:
    def test_full_score(self):
        assert _calculate_relative_score(60, 60) == 1.0

    def test_half_score(self):
        assert _calculate_relative_score(30, 60) == 0.5

    def test_zero_score(self):
        assert _calculate_relative_score(0, 60) == 0.0

    def test_zero_max(self):
        assert _calculate_relative_score(10, 0) == 0.0


class TestDetectAnomalies:
    def test_consistent_scores_no_anomalies(self):
        scores = {
            "PHASE2": {"score": 42, "confidence": 4},  # 70%
            "PHASE3": {"score": 20, "confidence": 4},  # 67%
            "PHASE4": {"score": 5, "confidence": 3},  # 50%
        }
        anomalies = _detect_anomalies(scores)
        assert len(anomalies) == 0

    def test_detects_large_discrepancy(self):
        scores = {
            "PHASE2": {"score": 55, "confidence": 4},  # 92%
            "PHASE3": {"score": 5, "confidence": 3},  # 17%
            "PHASE4": {"score": 3, "confidence": 3},
        }
        anomalies = _detect_anomalies(scores)
        assert any("Chênh lệch lớn" in a for a in anomalies)

    def test_detects_perfect_score(self):
        scores = {
            "PHASE2": {"score": 60, "confidence": 4},  # Perfect
            "PHASE3": {"score": 20, "confidence": 3},
            "PHASE4": {"score": 5, "confidence": 3},
        }
        anomalies = _detect_anomalies(scores)
        assert any("điểm tối đa" in a for a in anomalies)

    def test_detects_over_100_total(self):
        scores = {
            "PHASE2": {"score": 55, "confidence": 4},
            "PHASE3": {"score": 28, "confidence": 4},
            "PHASE4": {"score": 10, "confidence": 4},
        }
        # Total = 93, under 100
        anomalies = _detect_anomalies(scores)
        assert not any("Vượt quá" in a for a in anomalies)

    def test_detects_zero_with_high_confidence(self):
        scores = {
            "PHASE2": {"score": 0, "confidence": 5},  # Suspicious
            "PHASE3": {"score": 20, "confidence": 3},
            "PHASE4": {"score": 5, "confidence": 3},
        }
        anomalies = _detect_anomalies(scores)
        assert any("0 điểm nhưng confidence = 5" in a for a in anomalies)


class TestValidateConfidence:
    def test_no_adjustments_for_high_confidence(self):
        scores = {
            "PHASE2": {"score": 40, "confidence": 4},
            "PHASE3": {"score": 20, "confidence": 5},
            "PHASE4": {"score": 5, "confidence": 4},
        }
        adjustments = _validate_confidence(scores)
        assert len(adjustments) == 0

    def test_adjusts_low_confidence(self):
        scores = {
            "PHASE2": {"score": 50, "confidence": 1},  # Very low confidence
            "PHASE3": {"score": 20, "confidence": 4},
            "PHASE4": {"score": 5, "confidence": 3},
        }
        adjustments = _validate_confidence(scores)
        assert "PHASE2" in adjustments
        assert adjustments["PHASE2"] < 0  # Negative adjustment

    def test_no_adjustment_for_zero_score(self):
        scores = {
            "PHASE2": {"score": 0, "confidence": 1},
            "PHASE3": {"score": 20, "confidence": 4},
            "PHASE4": {"score": 5, "confidence": 3},
        }
        adjustments = _validate_confidence(scores)
        assert "PHASE2" not in adjustments  # Can't reduce 0 further


class TestValidatorNode:
    def test_consistent_state(self):
        state = {
            "scores": {
                "PHASE2": {"score": 40, "confidence": 4},
                "PHASE3": {"score": 20, "confidence": 4},
                "PHASE4": {"score": 5, "confidence": 3},
            },
            "confidence_scores": {"PHASE2": 4, "PHASE3": 4, "PHASE4": 3},
        }
        result = validator_node(state)
        vr = result["validation_result"]
        assert vr["is_consistent"] is True
        assert len(vr["anomalies"]) == 0

    def test_empty_scores(self):
        state = {"scores": {}, "confidence_scores": {}}
        result = validator_node(state)
        assert "validation_result" in result
        assert "errors" in result
