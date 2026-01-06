"""
Snowflake client for Company Risk Intelligence.

Data sources:
- SEC_FILINGS_DEMO_DATA.CYBERSYN: Read-only SEC filings (shared database)
- COMPANY_INTELLIGENCE.APP_DATA: Writable app data (our database)

Reference: https://docs.cybersyn.com/public-domain-sources/sec-filings
"""

import snowflake.connector
from snowflake.connector import DictCursor
from contextlib import contextmanager
from typing import Any
import pandas as pd

from app.config import get_settings


class SnowflakeClient:
    def __init__(self):
        self.settings = get_settings()
        self._connection = None

    def _get_connection_params(self) -> dict:
        return {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password,
            "warehouse": self.settings.snowflake_warehouse,
            "role": self.settings.snowflake_role,
        }

    @property
    def sec_db(self) -> str:
        """Fully qualified SEC database.schema."""
        return f"{self.settings.sec_database}.{self.settings.sec_schema}"

    @property
    def app_db(self) -> str:
        """Fully qualified app database.schema."""
        return f"{self.settings.app_database}.{self.settings.app_schema}"

    @contextmanager
    def get_connection(self):
        conn = snowflake.connector.connect(**self._get_connection_params())
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        with self.get_connection() as conn:
            cursor = conn.cursor(DictCursor) if dict_cursor else conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def execute_query(self, query: str, params: dict | None = None) -> list[dict]:
        with self.get_cursor() as cursor:
            cursor.execute(query, params or {})
            return cursor.fetchall()

    def execute_query_df(self, query: str, params: dict | None = None) -> pd.DataFrame:
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    # =========================================================================
    # Company queries (from app database)
    # =========================================================================

    def get_companies(self) -> list[dict]:
        """Get list of target companies from our app database."""
        query = f"""
        SELECT
            CIK,
            TICKER,
            COMPANY_NAME,
            SECTOR,
            SIC_CODE,
            SIC_DESCRIPTION
        FROM {self.app_db}.target_companies
        WHERE IS_ACTIVE = TRUE
        ORDER BY TICKER
        """
        return self.execute_query(query)

    def get_company_by_ticker(self, ticker: str) -> dict | None:
        """Get company info by ticker."""
        query = f"""
        SELECT
            CIK,
            TICKER,
            COMPANY_NAME,
            SECTOR,
            SIC_CODE,
            SIC_DESCRIPTION
        FROM {self.app_db}.target_companies
        WHERE TICKER = %(ticker)s
        """
        results = self.execute_query(query, {"ticker": ticker.upper()})
        return results[0] if results else None

    # =========================================================================
    # SEC Filing queries (from shared SEC database via views)
    # =========================================================================

    def get_filings(
        self,
        ticker: str | None = None,
        filing_type: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Get SEC filings from the shared database.
        Uses the view created in our app database that joins SEC data.

        Args:
            ticker: Optional ticker to filter by
            filing_type: '10-K', '10-Q', or '8-K'
            limit: Max results to return
        """
        conditions = ["1=1"]
        params = {}

        if ticker:
            conditions.append("TICKER = %(ticker)s")
            params["ticker"] = ticker.upper()

        if filing_type:
            # Map friendly names to Cybersyn VARIABLE_NAME values
            doc_type_map = {
                "10-K": "10-K Filing Text",
                "10-Q": "10-Q Filing Text",
                "8-K": "8-K Filing Text"
            }
            doc_type = doc_type_map.get(filing_type, f"{filing_type} Filing Text")
            conditions.append("DOCUMENT_TYPE = %(doc_type)s")
            params["doc_type"] = doc_type

        query = f"""
        SELECT
            SEC_DOCUMENT_ID,
            CIK,
            ADSH,
            TICKER,
            COMPANY_NAME,
            DOCUMENT_TYPE,
            PERIOD_END_DATE,
            SECTOR,
            LENGTH(FILING_TEXT) AS TEXT_LENGTH
        FROM {self.app_db}.v_sec_filing_text
        WHERE {' AND '.join(conditions)}
        ORDER BY PERIOD_END_DATE DESC
        LIMIT {limit}
        """
        return self.execute_query(query, params)

    def get_filing_content(self, sec_document_id: str) -> dict | None:
        """Get full filing content by SEC document ID."""
        query = f"""
        SELECT
            SEC_DOCUMENT_ID,
            CIK,
            ADSH,
            TICKER,
            COMPANY_NAME,
            DOCUMENT_TYPE,
            PERIOD_END_DATE,
            FILING_TEXT,
            SECTOR
        FROM {self.app_db}.v_sec_filing_text
        WHERE SEC_DOCUMENT_ID = %(doc_id)s
        """
        results = self.execute_query(query, {"doc_id": sec_document_id})
        return results[0] if results else None

    def get_latest_10k(self, ticker: str) -> dict | None:
        """Get the most recent 10-K filing for a company."""
        query = f"""
        SELECT
            SEC_DOCUMENT_ID,
            CIK,
            ADSH,
            TICKER,
            COMPANY_NAME,
            DOCUMENT_TYPE,
            PERIOD_END_DATE,
            FILING_TEXT,
            SECTOR
        FROM {self.app_db}.v_latest_10k
        WHERE TICKER = %(ticker)s
        """
        results = self.execute_query(query, {"ticker": ticker.upper()})
        return results[0] if results else None

    # =========================================================================
    # Document chunk queries (from app database)
    # =========================================================================

    def get_document_chunks(
        self,
        ticker: str | None = None,
        section_name: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """Get document chunks from our processed data."""
        conditions = ["1=1"]
        params = {}

        if ticker:
            conditions.append("COMPANY_TICKER = %(ticker)s")
            params["ticker"] = ticker.upper()

        if section_name:
            conditions.append("SECTION_NAME = %(section)s")
            params["section"] = section_name

        query = f"""
        SELECT
            CHUNK_ID,
            CIK,
            COMPANY_TICKER,
            COMPANY_NAME,
            FILING_TYPE,
            ADSH,
            PERIOD_END_DATE,
            SECTION_NAME,
            CHUNK_TEXT,
            CHUNK_INDEX
        FROM {self.app_db}.document_chunks
        WHERE {' AND '.join(conditions)}
        ORDER BY PERIOD_END_DATE DESC, CHUNK_INDEX
        LIMIT {limit}
        """
        return self.execute_query(query, params)

    def insert_document_chunk(
        self,
        chunk_id: str,
        cik: str,
        company_ticker: str,
        company_name: str,
        filing_type: str,
        adsh: str,
        period_end_date: str,
        section_name: str,
        chunk_text: str,
        chunk_index: int,
        metadata: dict | None = None
    ) -> None:
        """Insert a document chunk into our app database."""
        import json
        # Use TO_VARIANT with PARSE_JSON for proper JSON handling
        metadata_json = json.dumps(metadata or {})
        query = f"""
        INSERT INTO {self.app_db}.document_chunks
        (chunk_id, cik, company_ticker, company_name, filing_type, adsh,
         period_end_date, section_name, chunk_text, chunk_index, metadata)
        SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)
        """
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, (
                chunk_id, cik, company_ticker, company_name, filing_type, adsh,
                period_end_date, section_name, chunk_text, chunk_index,
                metadata_json
            ))

    # =========================================================================
    # Embedding queries
    # =========================================================================

    def vector_search(
        self,
        query_embedding: list[float],
        ticker: str | None = None,
        limit: int = 5
    ) -> list[dict]:
        """Perform vector similarity search on document embeddings."""
        ticker_filter = ""
        if ticker:
            ticker_filter = f"AND dc.COMPANY_TICKER = '{ticker.upper()}'"

        # Convert embedding list to string for query
        embedding_str = str(query_embedding)

        query = f"""
        SELECT
            dc.CHUNK_ID,
            dc.CIK,
            dc.COMPANY_TICKER,
            dc.COMPANY_NAME,
            dc.FILING_TYPE,
            dc.PERIOD_END_DATE,
            dc.SECTION_NAME,
            dc.CHUNK_TEXT,
            VECTOR_COSINE_SIMILARITY(de.EMBEDDING, {embedding_str}::VECTOR(FLOAT, 768)) as SIMILARITY
        FROM {self.app_db}.document_chunks dc
        JOIN {self.app_db}.document_embeddings de ON dc.CHUNK_ID = de.CHUNK_ID
        WHERE 1=1 {ticker_filter}
        ORDER BY SIMILARITY DESC
        LIMIT {limit}
        """
        return self.execute_query(query)

    # =========================================================================
    # Financial metrics queries
    # =========================================================================

    def get_financial_metrics(
        self,
        ticker: str,
        metric_names: list[str] | None = None
    ) -> list[dict]:
        """Get financial metrics for a company."""
        metric_filter = ""
        if metric_names:
            names_str = ','.join(f"'{m}'" for m in metric_names)
            metric_filter = f"AND METRIC_NAME IN ({names_str})"

        query = f"""
        SELECT
            METRIC_ID,
            CIK,
            COMPANY_TICKER,
            COMPANY_NAME,
            FILING_TYPE,
            PERIOD_END_DATE,
            METRIC_NAME,
            METRIC_VALUE,
            METRIC_UNIT,
            YOY_CHANGE,
            IS_ANOMALY
        FROM {self.app_db}.financial_metrics
        WHERE COMPANY_TICKER = %(ticker)s {metric_filter}
        ORDER BY PERIOD_END_DATE DESC, METRIC_NAME
        """
        return self.execute_query(query, {"ticker": ticker.upper()})

    # =========================================================================
    # Risk assessment queries
    # =========================================================================

    def get_risk_assessments(self, ticker: str) -> list[dict]:
        """Get risk assessments for a company."""
        query = f"""
        SELECT
            ASSESSMENT_ID,
            CIK,
            COMPANY_TICKER,
            COMPANY_NAME,
            PERIOD_END_DATE,
            RISK_CATEGORY,
            RISK_SCORE,
            SUMMARY,
            EVIDENCE
        FROM {self.app_db}.risk_assessments
        WHERE COMPANY_TICKER = %(ticker)s
        ORDER BY PERIOD_END_DATE DESC, RISK_SCORE DESC
        """
        return self.execute_query(query, {"ticker": ticker.upper()})


# Singleton instance
_client: SnowflakeClient | None = None


def get_snowflake_client() -> SnowflakeClient:
    global _client
    if _client is None:
        _client = SnowflakeClient()
    return _client
