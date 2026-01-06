from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Snowflake Configuration
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_role: str = "ACCOUNTADMIN"

    # Database for reading SEC filings (shared/read-only)
    sec_database: str = "SEC_FILINGS_DEMO_DATA"
    sec_schema: str = "CYBERSYN"

    # Database for app data (writable)
    app_database: str = "COMPANY_INTELLIGENCE"
    app_schema: str = "APP_DATA"

    # Anthropic API (optional - only needed for metrics extraction and risk analysis)
    anthropic_api_key: str = ""

    # Application Settings
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Target Companies
    target_companies: list[str] = [
        "AAPL", "MSFT", "GOOGL",  # Technology
        "JPM", "BAC",              # Financials
        "JNJ", "UNH",              # Healthcare
        "XOM", "CVX",              # Energy
        "WMT", "PG",               # Consumer Staples
        "CAT", "UPS",              # Industrials
        "AMT",                     # Real Estate
        "NEE",                     # Utilities
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
