from pydantic import BaseModel
from datetime import date
from typing import Any


class Filing(BaseModel):
    accession_number: str
    company_name: str
    ticker: str
    form_type: str
    filing_date: date
    document_url: str | None = None


class FilingContent(BaseModel):
    accession_number: str
    company_name: str
    ticker: str
    form_type: str
    filing_date: date
    filing_text: str | None = None


class FilingList(BaseModel):
    filings: list[Filing]
    count: int


class DocumentChunk(BaseModel):
    chunk_id: str
    company_ticker: str
    filing_type: str
    filing_date: date
    section_name: str
    chunk_text: str
    chunk_index: int
