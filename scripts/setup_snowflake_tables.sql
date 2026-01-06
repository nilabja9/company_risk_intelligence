-- Company Risk Intelligence - Snowflake Schema Setup
-- Run this script to create the required tables for the application
--
-- NOTE: SEC_FILINGS_DEMO_DATA is a SHARED database (read-only)
--       We create COMPANY_INTELLIGENCE for our writable tables
--
-- Data source: SEC_FILINGS_DEMO_DATA.CYBERSYN
-- Key views:
--   - COMPANY_INDEX: Has PRIMARY_TICKER, CIK, COMPANY_NAME
--   - SEC_CIK_INDEX: Has CIK, SIC codes
--   - SEC_REPORT_TEXT_ATTRIBUTES: Has filing text (VALUE column)

-- ============================================================
-- STEP 1: Create our own database for writable tables
-- ============================================================
CREATE DATABASE IF NOT EXISTS COMPANY_INTELLIGENCE;
USE DATABASE COMPANY_INTELLIGENCE;

CREATE SCHEMA IF NOT EXISTS APP_DATA;
USE SCHEMA APP_DATA;

-- ============================================================
-- STEP 2: Create tables for processed data
-- ============================================================

-- Document chunks for RAG (processed from SEC filings)
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id VARCHAR(100) PRIMARY KEY,
    cik VARCHAR(20) NOT NULL,
    company_ticker VARCHAR(10),
    company_name VARCHAR(500),
    filing_type VARCHAR(20) NOT NULL,
    adsh VARCHAR(30),
    period_end_date DATE NOT NULL,
    section_name VARCHAR(100) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INT NOT NULL,
    metadata VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Vector embeddings table
CREATE TABLE IF NOT EXISTS document_embeddings (
    chunk_id VARCHAR(100) PRIMARY KEY,
    embedding VECTOR(FLOAT, 768),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Extracted financial metrics
CREATE TABLE IF NOT EXISTS financial_metrics (
    metric_id VARCHAR(100) PRIMARY KEY,
    cik VARCHAR(20) NOT NULL,
    company_ticker VARCHAR(10),
    company_name VARCHAR(500),
    filing_type VARCHAR(20) NOT NULL,
    period_end_date DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT,
    metric_unit VARCHAR(50),
    yoy_change FLOAT,
    is_anomaly BOOLEAN DEFAULT FALSE,
    metadata VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Risk assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id VARCHAR(100) PRIMARY KEY,
    cik VARCHAR(20) NOT NULL,
    company_ticker VARCHAR(10),
    company_name VARCHAR(500),
    period_end_date DATE NOT NULL,
    risk_category VARCHAR(50) NOT NULL,
    risk_score FLOAT NOT NULL,
    summary TEXT,
    evidence VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Target companies reference table
CREATE TABLE IF NOT EXISTS target_companies (
    cik VARCHAR(20) PRIMARY KEY,
    ticker VARCHAR(10),
    company_name VARCHAR(500),
    sector VARCHAR(50),
    sic_code VARCHAR(10),
    sic_description VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================
-- STEP 3: Populate target companies
-- ============================================================
-- Join COMPANY_INDEX (has tickers) with SEC_CIK_INDEX (has SIC codes)

MERGE INTO target_companies AS target
USING (
    SELECT
        ci.CIK,
        ci.PRIMARY_TICKER AS TICKER,
        ci.COMPANY_NAME,
        cik.SIC AS SIC_CODE,
        cik.SIC_CODE_DESCRIPTION,
        CASE
            WHEN cik.SIC BETWEEN '3570' AND '3579' THEN 'Technology'
            WHEN cik.SIC BETWEEN '7370' AND '7379' THEN 'Technology'
            WHEN cik.SIC BETWEEN '3571' AND '3571' THEN 'Technology'
            WHEN cik.SIC BETWEEN '6000' AND '6799' THEN 'Financials'
            WHEN cik.SIC BETWEEN '2830' AND '2839' THEN 'Healthcare'
            WHEN cik.SIC BETWEEN '8000' AND '8099' THEN 'Healthcare'
            WHEN cik.SIC BETWEEN '1300' AND '1399' THEN 'Energy'
            WHEN cik.SIC BETWEEN '2900' AND '2999' THEN 'Energy'
            WHEN cik.SIC BETWEEN '5200' AND '5999' THEN 'Consumer Staples'
            WHEN cik.SIC BETWEEN '3500' AND '3599' THEN 'Industrials'
            WHEN cik.SIC BETWEEN '6500' AND '6599' THEN 'Real Estate'
            WHEN cik.SIC BETWEEN '4900' AND '4999' THEN 'Utilities'
            ELSE 'Other'
        END AS sector
    FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.COMPANY_INDEX ci
    LEFT JOIN SEC_FILINGS_DEMO_DATA.CYBERSYN.SEC_CIK_INDEX cik ON ci.CIK = cik.CIK
    WHERE ci.PRIMARY_TICKER IN ('AAPL', 'MSFT', 'GOOGL', 'GOOG', 'JPM', 'BAC', 'JNJ', 'UNH',
                                 'XOM', 'CVX', 'WMT', 'PG', 'CAT', 'UPS', 'AMT', 'NEE')
    AND ci.CIK IS NOT NULL
) AS source
ON target.cik = source.cik
WHEN MATCHED THEN
    UPDATE SET
        ticker = source.ticker,
        company_name = source.company_name,
        sic_code = source.sic_code,
        sic_description = source.sic_code_description,
        sector = source.sector
WHEN NOT MATCHED THEN
    INSERT (cik, ticker, company_name, sic_code, sic_description, sector)
    VALUES (source.cik, source.ticker, source.company_name, source.sic_code,
            source.sic_code_description, source.sector);

-- ============================================================
-- STEP 4: Create views for querying SEC filings
-- ============================================================

-- View to access 10-K, 10-Q, 8-K filing text for target companies
CREATE OR REPLACE VIEW v_sec_filing_text AS
SELECT
    txt.SEC_DOCUMENT_ID,
    txt.CIK,
    txt.ADSH,
    ci.PRIMARY_TICKER AS TICKER,
    ci.COMPANY_NAME,
    txt.VARIABLE_NAME AS DOCUMENT_TYPE,
    txt.PERIOD_END_DATE,
    txt.VALUE AS FILING_TEXT,
    tc.SECTOR
FROM SEC_FILINGS_DEMO_DATA.CYBERSYN.SEC_REPORT_TEXT_ATTRIBUTES txt
JOIN SEC_FILINGS_DEMO_DATA.CYBERSYN.COMPANY_INDEX ci ON txt.CIK = ci.CIK
JOIN target_companies tc ON ci.CIK = tc.CIK
WHERE txt.VARIABLE_NAME IN ('10-K Filing Text', '10-Q Filing Text', '8-K Filing Text');

-- View for latest 10-K per company
CREATE OR REPLACE VIEW v_latest_10k AS
SELECT *
FROM v_sec_filing_text
WHERE DOCUMENT_TYPE = '10-K Filing Text'
QUALIFY ROW_NUMBER() OVER (PARTITION BY CIK ORDER BY PERIOD_END_DATE DESC) = 1;

-- View for latest 10-Q per company
CREATE OR REPLACE VIEW v_latest_10q AS
SELECT *
FROM v_sec_filing_text
WHERE DOCUMENT_TYPE = '10-Q Filing Text'
QUALIFY ROW_NUMBER() OVER (PARTITION BY CIK ORDER BY PERIOD_END_DATE DESC) = 1;

-- ============================================================
-- STEP 5: Verify setup
-- ============================================================
SHOW TABLES IN SCHEMA COMPANY_INTELLIGENCE.APP_DATA;
SHOW VIEWS IN SCHEMA COMPANY_INTELLIGENCE.APP_DATA;

-- Verify target companies were loaded
SELECT ticker, company_name, sector, sic_code FROM target_companies ORDER BY ticker;

-- Check SEC filing availability
SELECT
    TICKER,
    COMPANY_NAME,
    DOCUMENT_TYPE,
    PERIOD_END_DATE,
    LENGTH(FILING_TEXT) AS TEXT_LENGTH
FROM v_sec_filing_text
ORDER BY TICKER, PERIOD_END_DATE DESC
LIMIT 20;
