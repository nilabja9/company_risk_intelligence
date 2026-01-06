from pydantic import BaseModel
from typing import Any


class Company(BaseModel):
    ticker: str
    company_name: str
    sector: str | None = None


class CompanyList(BaseModel):
    companies: list[Company]
    count: int
