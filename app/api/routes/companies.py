from fastapi import APIRouter, HTTPException

from app.services.snowflake_client import get_snowflake_client
from app.models.company import Company, CompanyList

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompanyList)
async def list_companies():
    """Get list of all target companies."""
    client = get_snowflake_client()
    companies = client.get_companies()

    return CompanyList(
        companies=[
            Company(
                ticker=c["TICKER"],
                company_name=c["COMPANY_NAME"],
                sector=c.get("SECTOR")
            )
            for c in companies
        ],
        count=len(companies)
    )


@router.get("/{ticker}")
async def get_company(ticker: str):
    """Get details for a specific company."""
    client = get_snowflake_client()
    companies = client.get_companies()

    for c in companies:
        if c["TICKER"].upper() == ticker.upper():
            return Company(
                ticker=c["TICKER"],
                company_name=c["COMPANY_NAME"],
                sector=c.get("SECTOR")
            )

    raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
