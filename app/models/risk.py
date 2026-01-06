from pydantic import BaseModel
from datetime import date
from typing import Any


class RiskFlag(BaseModel):
    category: str
    score: float
    summary: str
    date: str


class CategoryRisk(BaseModel):
    average_score: float
    count: int
    latest: dict | None = None


class CompanyRiskSummary(BaseModel):
    ticker: str
    overall_score: float
    risk_breakdown: dict[str, CategoryRisk]
    recent_flags: list[RiskFlag]


class RiskComparison(BaseModel):
    comparison: dict
    current_period: dict | None
    previous_period: dict | None
