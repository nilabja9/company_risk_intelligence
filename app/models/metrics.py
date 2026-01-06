from pydantic import BaseModel
from datetime import date
from typing import Any


class MetricValue(BaseModel):
    value: float | None
    unit: str
    date: str
    yoy_change: float | None = None


class MetricAnomaly(BaseModel):
    metric: str
    value: float
    date: str


class CompanyMetrics(BaseModel):
    ticker: str
    metrics: dict[str, MetricValue]
    anomalies: list[MetricAnomaly]


class MetricHistoryPoint(BaseModel):
    date: str
    value: float
    filing_type: str


class MetricHistory(BaseModel):
    ticker: str
    metric_name: str
    history: list[MetricHistoryPoint]
