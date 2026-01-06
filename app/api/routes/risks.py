from fastapi import APIRouter, HTTPException

from app.services.risk_analyzer import get_risk_analyzer
from app.services.rag_service import get_rag_service
from app.models.risk import CompanyRiskSummary, RiskFlag, CategoryRisk, RiskComparison

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("/{ticker}", response_model=CompanyRiskSummary)
async def get_company_risks(ticker: str):
    """Get risk assessment summary for a company."""
    analyzer = get_risk_analyzer()
    summary = analyzer.get_company_risk_summary(ticker.upper())

    return CompanyRiskSummary(
        ticker=summary["ticker"],
        overall_score=summary["overall_score"],
        risk_breakdown={
            cat: CategoryRisk(
                average_score=data["average_score"],
                count=data["count"],
                latest=data.get("latest")
            )
            for cat, data in summary.get("risk_breakdown", {}).items()
        },
        recent_flags=[
            RiskFlag(
                category=f["category"],
                score=f["score"],
                summary=f["summary"],
                date=f["date"]
            )
            for f in summary.get("recent_flags", [])
        ]
    )


@router.get("/{ticker}/compare-periods", response_model=RiskComparison)
async def compare_risk_periods(
    ticker: str,
    section: str = "RISK_FACTORS"
):
    """Compare risk sections between filing periods."""
    rag = get_rag_service()
    comparison = rag.compare_filings(
        ticker=ticker.upper(),
        section_name=section
    )

    return RiskComparison(
        comparison=comparison.get("comparison", {}),
        current_period=comparison.get("current_period"),
        previous_period=comparison.get("previous_period")
    )


@router.get("/{ticker}/red-flags")
async def get_red_flags(ticker: str):
    """Get high-severity risk flags for a company."""
    analyzer = get_risk_analyzer()
    summary = analyzer.get_company_risk_summary(ticker.upper())

    red_flags = [
        flag for flag in summary.get("recent_flags", [])
        if flag.get("score", 0) >= 70
    ]

    return {
        "ticker": ticker.upper(),
        "red_flag_count": len(red_flags),
        "flags": red_flags,
        "overall_risk_score": summary.get("overall_score", 0)
    }


@router.get("/{ticker}/category/{category}")
async def get_category_risks(ticker: str, category: str):
    """Get risks for a specific category."""
    analyzer = get_risk_analyzer()
    summary = analyzer.get_company_risk_summary(ticker.upper())

    category_upper = category.upper()
    breakdown = summary.get("risk_breakdown", {})

    if category_upper not in breakdown:
        raise HTTPException(
            status_code=404,
            detail=f"No {category} risks found for {ticker}"
        )

    category_data = breakdown[category_upper]

    return {
        "ticker": ticker.upper(),
        "category": category_upper,
        "average_score": category_data.get("average_score"),
        "assessment_count": category_data.get("count"),
        "latest_assessment": category_data.get("latest"),
        "related_flags": [
            f for f in summary.get("recent_flags", [])
            if f.get("category") == category_upper
        ]
    }
