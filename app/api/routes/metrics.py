from fastapi import APIRouter, HTTPException

from app.services.metrics_engine import get_metrics_engine
from app.services.snowflake_client import get_snowflake_client
from app.models.metrics import CompanyMetrics, MetricValue, MetricAnomaly

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/{ticker}", response_model=CompanyMetrics)
async def get_company_metrics(ticker: str):
    """Get all financial metrics for a company."""
    engine = get_metrics_engine()
    summary = engine.get_company_metrics_summary(ticker.upper())

    if not summary.get("metrics"):
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for {ticker}"
        )

    return CompanyMetrics(
        ticker=summary["ticker"],
        metrics={
            name: MetricValue(
                value=data["value"],
                unit=data["unit"],
                date=data["date"],
                yoy_change=data.get("yoy_change")
            )
            for name, data in summary["metrics"].items()
        },
        anomalies=[
            MetricAnomaly(
                metric=a["metric"],
                value=a["value"],
                date=a["date"]
            )
            for a in summary.get("anomalies", [])
        ]
    )


@router.get("/{ticker}/history/{metric_name}")
async def get_metric_history(ticker: str, metric_name: str):
    """Get historical values for a specific metric."""
    client = get_snowflake_client()
    metrics = client.get_financial_metrics(
        ticker=ticker.upper(),
        metric_names=[metric_name]
    )

    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Metric {metric_name} not found for {ticker}"
        )

    return {
        "ticker": ticker.upper(),
        "metric_name": metric_name,
        "history": [
            {
                "date": str(m["PERIOD_END_DATE"]),
                "value": m["METRIC_VALUE"],
                "filing_type": m["FILING_TYPE"],
                "yoy_change": m["YOY_CHANGE"],
                "is_anomaly": m["IS_ANOMALY"]
            }
            for m in metrics
        ]
    }


@router.get("/{ticker}/compare")
async def compare_metrics(ticker: str, compare_to: str):
    """Compare metrics between two companies."""
    engine = get_metrics_engine()

    summary1 = engine.get_company_metrics_summary(ticker.upper())
    summary2 = engine.get_company_metrics_summary(compare_to.upper())

    comparison = {}
    all_metrics = set(summary1.get("metrics", {}).keys()) | set(summary2.get("metrics", {}).keys())

    for metric in all_metrics:
        val1 = summary1.get("metrics", {}).get(metric, {})
        val2 = summary2.get("metrics", {}).get(metric, {})

        comparison[metric] = {
            ticker.upper(): val1.get("value") if val1 else None,
            compare_to.upper(): val2.get("value") if val2 else None,
            "unit": val1.get("unit") or val2.get("unit") if (val1 or val2) else None
        }

    return {
        "companies": [ticker.upper(), compare_to.upper()],
        "comparison": comparison
    }
