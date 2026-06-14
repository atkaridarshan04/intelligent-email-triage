"""Shared test helpers — imported directly by test modules."""
from src.inference.adapter import ModelOutput, STRUCTURED_COLS
from src.inference.postprocess import TriageResponse


class MockAdapter:
    """Returns high phishing score if 'phishing_signal' in text, else high spam."""

    def __init__(self, phishing_prob: float | None = None):
        self._fixed = phishing_prob

    def predict(self, text: str, features: dict) -> ModelOutput:
        p = self._fixed if self._fixed is not None else (0.95 if "phishing_signal" in text else 0.05)
        return ModelOutput(
            spam_prob=round(1.0 - p, 4),
            phishing_prob=round(p, 4),
            feature_attributions={col: 0.1 if col == "reply_to_mismatch" else 0.0 for col in STRUCTURED_COLS},
        )

    def version(self) -> str:
        return "mock-v0.0"

    def model_type(self) -> str:
        return "mock"


def make_triage_response(**overrides) -> TriageResponse:
    defaults = dict(
        email_id="test-id-001",
        label="phishing",
        predicted_class="phishing",
        spam_probability=0.05,
        phishing_probability=0.95,
        trust_score=92.0,
        routed_to_review=False,
        security_override=False,
        reasons=["Reply-To address differs from sender"],
        confidence_notes=[],
        model_version="mock-v0.0",
        latency_ms=12.0,
    )
    defaults.update(overrides)
    return TriageResponse(**defaults)
