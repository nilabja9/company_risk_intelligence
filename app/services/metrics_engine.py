from dataclasses import dataclass
from typing import Any
import uuid
import json

from app.services.snowflake_client import get_snowflake_client
from app.services.claude_client import get_claude_client


@dataclass
class FinancialMetric:
    metric_id: str
    company_ticker: str
    filing_type: str
    filing_date: str
    metric_name: str
    metric_value: float | None
    metric_unit: str
    yoy_change: float | None = None
    is_anomaly: bool = False
    metadata: dict | None = None


class MetricsEngine:
    # Metric definitions with formulas
    COMPUTED_METRICS = {
        "gross_margin": {
            "formula": lambda m: (m.get("gross_profit", 0) / m.get("revenue", 1)) * 100 if m.get("revenue") else None,
            "unit": "percent"
        },
        "operating_margin": {
            "formula": lambda m: (m.get("operating_income", 0) / m.get("revenue", 1)) * 100 if m.get("revenue") else None,
            "unit": "percent"
        },
        "net_margin": {
            "formula": lambda m: (m.get("net_income", 0) / m.get("revenue", 1)) * 100 if m.get("revenue") else None,
            "unit": "percent"
        },
        "roe": {
            "formula": lambda m: (m.get("net_income", 0) / m.get("shareholders_equity", 1)) * 100 if m.get("shareholders_equity") else None,
            "unit": "percent"
        },
        "roa": {
            "formula": lambda m: (m.get("net_income", 0) / m.get("total_assets", 1)) * 100 if m.get("total_assets") else None,
            "unit": "percent"
        },
        "debt_to_equity": {
            "formula": lambda m: m.get("total_debt", 0) / m.get("shareholders_equity", 1) if m.get("shareholders_equity") else None,
            "unit": "ratio"
        },
        "current_ratio": {
            "formula": lambda m: m.get("current_assets", 0) / m.get("current_liabilities", 1) if m.get("current_liabilities") else None,
            "unit": "ratio"
        },
        "quick_ratio": {
            "formula": lambda m: (m.get("current_assets", 0) - m.get("inventory", 0)) / m.get("current_liabilities", 1) if m.get("current_liabilities") else None,
            "unit": "ratio"
        },
        "interest_coverage": {
            "formula": lambda m: m.get("ebit", 0) / m.get("interest_expense", 1) if m.get("interest_expense") else None,
            "unit": "ratio"
        },
        "debt_to_ebitda": {
            "formula": lambda m: m.get("total_debt", 0) / (m.get("ebit", 0) + m.get("depreciation", 0)) if (m.get("ebit", 0) + m.get("depreciation", 0)) else None,
            "unit": "ratio"
        }
    }

    # Anomaly thresholds
    ANOMALY_THRESHOLDS = {
        "gross_margin": {"min": 0, "max": 80, "yoy_change": 10},
        "operating_margin": {"min": -20, "max": 50, "yoy_change": 15},
        "net_margin": {"min": -30, "max": 40, "yoy_change": 20},
        "roe": {"min": -50, "max": 50, "yoy_change": 25},
        "debt_to_equity": {"min": 0, "max": 5, "yoy_change": 0.5},
        "current_ratio": {"min": 0.5, "max": 5, "yoy_change": 0.5},
        "interest_coverage": {"min": 0, "max": 50, "yoy_change": 5},
    }

    def __init__(self):
        self.snowflake = get_snowflake_client()
        self.claude = get_claude_client()

    def extract_raw_metrics(
        self,
        filing_text: str,
        company_ticker: str,
        company_name: str
    ) -> dict:
        return self.claude.extract_financial_metrics(filing_text, company_name)

    def compute_derived_metrics(self, raw_metrics: dict) -> dict:
        computed = {}
        metrics_dict = {}

        # Convert raw metrics to simple dict
        if "metrics" in raw_metrics:
            for name, data in raw_metrics["metrics"].items():
                if isinstance(data, dict) and "value" in data:
                    metrics_dict[name] = data["value"]
                else:
                    metrics_dict[name] = data

        # Compute derived metrics
        for metric_name, config in self.COMPUTED_METRICS.items():
            try:
                value = config["formula"](metrics_dict)
                if value is not None:
                    computed[metric_name] = {
                        "value": round(value, 2),
                        "unit": config["unit"]
                    }
            except (ZeroDivisionError, TypeError):
                continue

        return computed

    def detect_anomalies(
        self,
        current_metrics: dict,
        previous_metrics: dict | None = None
    ) -> dict[str, bool]:
        anomalies = {}

        for metric_name, value_data in current_metrics.items():
            value = value_data.get("value") if isinstance(value_data, dict) else value_data
            if value is None:
                continue

            is_anomaly = False
            threshold = self.ANOMALY_THRESHOLDS.get(metric_name, {})

            # Check absolute bounds
            if "min" in threshold and value < threshold["min"]:
                is_anomaly = True
            if "max" in threshold and value > threshold["max"]:
                is_anomaly = True

            # Check YoY change if previous data exists
            if previous_metrics and metric_name in previous_metrics:
                prev_value = previous_metrics[metric_name]
                if isinstance(prev_value, dict):
                    prev_value = prev_value.get("value")

                if prev_value and prev_value != 0:
                    yoy_change = abs((value - prev_value) / prev_value * 100)
                    if "yoy_change" in threshold and yoy_change > threshold["yoy_change"]:
                        is_anomaly = True

            anomalies[metric_name] = is_anomaly

        return anomalies

    def calculate_yoy_changes(
        self,
        current_metrics: dict,
        previous_metrics: dict
    ) -> dict[str, float]:
        changes = {}

        for metric_name, value_data in current_metrics.items():
            current_value = value_data.get("value") if isinstance(value_data, dict) else value_data
            if current_value is None:
                continue

            if metric_name in previous_metrics:
                prev_value = previous_metrics[metric_name]
                if isinstance(prev_value, dict):
                    prev_value = prev_value.get("value")

                if prev_value and prev_value != 0:
                    change = ((current_value - prev_value) / prev_value) * 100
                    changes[metric_name] = round(change, 2)

        return changes

    def process_filing_metrics(
        self,
        filing_text: str,
        company_ticker: str,
        company_name: str,
        filing_type: str,
        filing_date: str
    ) -> list[FinancialMetric]:
        # Extract raw metrics using Claude
        raw_result = self.extract_raw_metrics(filing_text, company_ticker, company_name)

        # Compute derived metrics
        raw_metrics = raw_result.get("metrics", {})
        computed_metrics = self.compute_derived_metrics(raw_result)

        # Get previous period metrics for YoY comparison
        previous_metrics = self._get_previous_period_metrics(company_ticker, filing_date)

        # Calculate YoY changes
        yoy_changes = {}
        if previous_metrics:
            yoy_changes = self.calculate_yoy_changes(computed_metrics, previous_metrics)

        # Detect anomalies
        anomalies = self.detect_anomalies(computed_metrics, previous_metrics)

        # Create metric objects
        metrics = []

        # Add raw metrics
        for name, data in raw_metrics.items():
            value = data.get("value") if isinstance(data, dict) else data
            metrics.append(FinancialMetric(
                metric_id=f"{company_ticker}_{filing_date}_{name}",
                company_ticker=company_ticker,
                filing_type=filing_type,
                filing_date=filing_date,
                metric_name=name,
                metric_value=value,
                metric_unit="millions_usd",
                yoy_change=yoy_changes.get(name),
                is_anomaly=anomalies.get(name, False),
                metadata={"source": "extracted"}
            ))

        # Add computed metrics
        for name, data in computed_metrics.items():
            metrics.append(FinancialMetric(
                metric_id=f"{company_ticker}_{filing_date}_{name}",
                company_ticker=company_ticker,
                filing_type=filing_type,
                filing_date=filing_date,
                metric_name=name,
                metric_value=data["value"],
                metric_unit=data["unit"],
                yoy_change=yoy_changes.get(name),
                is_anomaly=anomalies.get(name, False),
                metadata={"source": "computed"}
            ))

        return metrics

    def _get_previous_period_metrics(
        self,
        ticker: str,
        current_date: str
    ) -> dict | None:
        query = """
        SELECT metric_name, metric_value
        FROM financial_metrics
        WHERE company_ticker = %s
        AND filing_date < %s
        ORDER BY filing_date DESC
        """
        results = self.snowflake.execute_query(query % (f"'{ticker}'", f"'{current_date}'"))

        if not results:
            return None

        return {r["METRIC_NAME"]: r["METRIC_VALUE"] for r in results}

    def store_metrics(self, metrics: list[FinancialMetric]) -> int:
        stored = 0
        for metric in metrics:
            query = """
            MERGE INTO financial_metrics AS target
            USING (SELECT %s AS metric_id) AS source
            ON target.metric_id = source.metric_id
            WHEN MATCHED THEN UPDATE SET
                metric_value = %s,
                yoy_change = %s,
                is_anomaly = %s
            WHEN NOT MATCHED THEN INSERT
                (metric_id, company_ticker, filing_type, filing_date,
                 metric_name, metric_value, metric_unit, yoy_change, is_anomaly, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s))
            """
            try:
                with self.snowflake.get_cursor(dict_cursor=False) as cursor:
                    cursor.execute(query, (
                        metric.metric_id,
                        metric.metric_value,
                        metric.yoy_change,
                        metric.is_anomaly,
                        metric.metric_id,
                        metric.company_ticker,
                        metric.filing_type,
                        metric.filing_date,
                        metric.metric_name,
                        metric.metric_value,
                        metric.metric_unit,
                        metric.yoy_change,
                        metric.is_anomaly,
                        json.dumps(metric.metadata or {})
                    ))
                stored += 1
            except Exception as e:
                print(f"Error storing metric {metric.metric_id}: {e}")

        return stored

    def get_company_metrics_summary(self, ticker: str) -> dict:
        metrics = self.snowflake.get_financial_metrics(ticker)

        if not metrics:
            return {"ticker": ticker, "metrics": {}, "anomalies": []}

        # Group by metric name, get latest
        latest_metrics = {}
        anomalies = []

        for m in metrics:
            name = m["METRIC_NAME"]
            if name not in latest_metrics:
                latest_metrics[name] = {
                    "value": m["METRIC_VALUE"],
                    "unit": m["METRIC_UNIT"],
                    "date": str(m["FILING_DATE"]),
                    "yoy_change": m["YOY_CHANGE"]
                }
                if m["IS_ANOMALY"]:
                    anomalies.append({
                        "metric": name,
                        "value": m["METRIC_VALUE"],
                        "date": str(m["FILING_DATE"])
                    })

        return {
            "ticker": ticker,
            "metrics": latest_metrics,
            "anomalies": anomalies
        }


def get_metrics_engine() -> MetricsEngine:
    return MetricsEngine()
