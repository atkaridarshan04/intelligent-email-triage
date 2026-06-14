"""
postprocess.py — Assemble TriageResponse from ModelOutput + RoutingDecision.
"""
from dataclasses import dataclass, field

from src.explainability.rule_summarizer import summarize
from src.inference.adapter import ModelOutput
from src.inference.threshold_router import RoutingDecision


@dataclass
class TriageResponse:
    email_id: str
    label: str                          # final routing label
    predicted_class: str                # model's binary prediction
    spam_probability: float
    phishing_probability: float
    trust_score: float
    routed_to_review: bool
    security_override: bool
    reasons: list[str]
    confidence_notes: list[str]
    model_version: str
    latency_ms: float = 0.0


def build_response(
    email_id: str,
    model_output: ModelOutput,
    routing: RoutingDecision,
    model_version: str,
    latency_ms: float = 0.0,
) -> TriageResponse:
    reasons = summarize(
        model_output.feature_attributions,
        predicted_class=routing.predicted_class,
    )

    confidence_notes: list[str] = []
    if routing.security_override:
        confidence_notes.append("Security override applied: high-risk signal + phishing probability threshold exceeded")
    if routing.routed_to_review:
        confidence_notes.append(f"Low confidence (trust score {routing.trust_score:.0f}) — routed to analyst review")
    if model_output.phishing_prob > 0.55 and routing.predicted_class == "spam":
        confidence_notes.append("Borderline classification — model shows phishing signal")

    return TriageResponse(
        email_id=email_id,
        label=routing.label,
        predicted_class=routing.predicted_class,
        spam_probability=round(model_output.spam_prob, 4),
        phishing_probability=round(model_output.phishing_prob, 4),
        trust_score=round(routing.trust_score, 1),
        routed_to_review=routing.routed_to_review,
        security_override=routing.security_override,
        reasons=reasons,
        confidence_notes=confidence_notes,
        model_version=model_version,
        latency_ms=round(latency_ms, 1),
    )
