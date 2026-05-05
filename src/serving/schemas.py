"""
Pydantic schemas for API request/response.
"""
from pydantic import BaseModel
from typing import Optional


class PredictionResponse(BaseModel):
    id: str
    label: str
    trust_score: float
    risk_score: int
    class_probabilities: dict[str, float]
    active_signals: list[str]
    monitoring_flag: bool


class FeedbackRequest(BaseModel):
    analyst_verdict: str  # "spam" | "junk" | "phishing" | "safe"
