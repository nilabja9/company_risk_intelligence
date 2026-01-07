from fastapi import APIRouter, HTTPException, Query
from typing import Literal

from app.services.snowflake_client import get_snowflake_client
from app.models.filing import Filing, FilingContent, FilingList

router = APIRouter(prefix="/filings", tags=["filings"])


@router.get("", response_model=FilingList)
async def list_filings(
    ticker: str | None = None,
    filing_type: Literal["10-K", "10-Q", "8-K"] | None = None,
    limit: int = Query(default=50, le=200)
):
    """Get list of SEC filings, optionally filtered by company or type."""
    client = get_snowflake_client()
    filings = client.get_filings(
        ticker=ticker,
        filing_type=filing_type,
        limit=limit
    )

    return FilingList(
        filings=[
            Filing(
                accession_number=f["SEC_DOCUMENT_ID"],
                company_name=f["COMPANY_NAME"],
                ticker=f["TICKER"],
                form_type=f["DOCUMENT_TYPE"].replace(" Filing Text", ""),
                filing_date=str(f["PERIOD_END_DATE"]),
                document_url=None
            )
            for f in filings
        ],
        count=len(filings)
    )


@router.get("/{accession_number}")
async def get_filing_content(accession_number: str):
    """Get full content of a specific filing."""
    client = get_snowflake_client()
    filing = client.get_filing_content(accession_number)

    if not filing:
        raise HTTPException(
            status_code=404,
            detail=f"Filing {accession_number} not found"
        )

    return FilingContent(
        accession_number=filing["SEC_DOCUMENT_ID"],
        company_name=filing["COMPANY_NAME"],
        ticker=filing["TICKER"],
        form_type=filing["DOCUMENT_TYPE"].replace(" Filing Text", ""),
        filing_date=str(filing["PERIOD_END_DATE"]),
        filing_text=filing.get("FILING_TEXT")
    )


@router.get("/{ticker}/sections")
async def get_filing_sections(
    ticker: str,
    section: str | None = None,
    limit: int = Query(default=20, le=100)
):
    """Get document chunks/sections for a company."""
    client = get_snowflake_client()
    chunks = client.get_document_chunks(
        ticker=ticker.upper(),
        section_name=section,
        limit=limit
    )

    return {
        "ticker": ticker.upper(),
        "section_filter": section,
        "chunks": [
            {
                "chunk_id": c["CHUNK_ID"],
                "filing_type": c["FILING_TYPE"],
                "filing_date": str(c["PERIOD_END_DATE"]),
                "section_name": c["SECTION_NAME"],
                "chunk_text": c["CHUNK_TEXT"][:500] + "..." if len(c["CHUNK_TEXT"]) > 500 else c["CHUNK_TEXT"],
                "chunk_index": c["CHUNK_INDEX"]
            }
            for c in chunks
        ],
        "count": len(chunks)
    }
