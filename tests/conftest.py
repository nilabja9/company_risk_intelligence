import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_filing_text():
    """Sample SEC filing text for testing."""
    return """
    ITEM 1A. RISK FACTORS

    The following risk factors may adversely affect our business:

    Market Risk: Changes in market conditions could impact our revenue.
    We face significant competition from established players.

    Regulatory Risk: New regulations may increase compliance costs.
    We are subject to various legal proceedings.

    ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

    Revenue increased 15% year-over-year to $50 billion.
    Operating margin improved to 25% from 22% in the prior year.
    Net income was $10 billion, representing a net margin of 20%.

    ITEM 8. FINANCIAL STATEMENTS

    Total Revenue: $50,000,000,000
    Gross Profit: $25,000,000,000
    Operating Income: $12,500,000,000
    Net Income: $10,000,000,000
    Total Assets: $200,000,000,000
    Total Liabilities: $80,000,000,000
    Shareholders' Equity: $120,000,000,000
    """


@pytest.fixture
def sample_company():
    """Sample company data."""
    return {
        "ticker": "TEST",
        "company_name": "Test Corporation",
        "sector": "Technology"
    }
