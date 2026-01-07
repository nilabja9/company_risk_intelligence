#!/usr/bin/env python3
"""
Batch processing script for Company Risk Intelligence.

Pipeline:
1. Read SEC filings from SEC_FILINGS_DEMO_DATA (shared database)
2. Chunk documents by section
3. Generate embeddings using Snowflake Cortex
4. Extract financial metrics using Claude
5. Perform risk analysis using Claude
6. Store all results in COMPANY_INTELLIGENCE (our database)

Data source: https://docs.cybersyn.com/public-domain-sources/sec-filings
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.snowflake_client import get_snowflake_client
from app.services.document_processor import get_document_processor
from app.services.embedding_service import get_embedding_service
from app.services.metrics_engine import get_metrics_engine
from app.services.risk_analyzer import get_risk_analyzer


def log(message: str):
    """Simple logging with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def process_filings():
    """
    Process SEC filings for all target companies.
    Reads from SEC_FILINGS_DEMO_DATA, writes to COMPANY_INTELLIGENCE.
    """
    snowflake = get_snowflake_client()
    doc_processor = get_document_processor()

    log("Starting filing processing...")

    # Get list of target companies
    companies = snowflake.get_companies()
    log(f"Found {len(companies)} target companies")

    total_chunks = 0
    for company in companies:
        ticker = company["TICKER"]
        log(f"Processing filings for {ticker} ({company['COMPANY_NAME']})...")

        # Get filings for this company from the view
        filings = snowflake.get_filings(ticker=ticker, limit=20)
        log(f"  Found {len(filings)} filings")

        for filing in filings:
            sec_doc_id = filing["SEC_DOCUMENT_ID"]

            # Get full filing content
            content = snowflake.get_filing_content(sec_doc_id)
            if not content or not content.get("FILING_TEXT"):
                log(f"  Skipping {sec_doc_id} - no content")
                continue

            # Map document type to simpler filing type
            doc_type = content.get("DOCUMENT_TYPE", "")
            filing_type = doc_type.replace(" Filing Text", "")  # "10-K Filing Text" -> "10-K"

            # Process and store chunks
            try:
                chunks_stored = doc_processor.process_and_store_filing(
                    sec_document_id=sec_doc_id,
                    cik=content["CIK"],
                    adsh=content.get("ADSH", ""),
                    company_ticker=ticker,
                    company_name=content["COMPANY_NAME"],
                    filing_type=filing_type,
                    period_end_date=str(content["PERIOD_END_DATE"]),
                    filing_text=content["FILING_TEXT"]
                )
                total_chunks += chunks_stored
                log(f"  {sec_doc_id}: {chunks_stored} chunks created")
            except Exception as e:
                log(f"  Error processing {sec_doc_id}: {e}")

    log(f"Filing processing complete. Total chunks: {total_chunks}")
    return total_chunks


def generate_embeddings():
    """Generate embeddings for all document chunks using Snowflake Cortex."""
    embedding_service = get_embedding_service()

    log("Starting embedding generation...")

    result = embedding_service.process_all_chunks(batch_size=50)

    log(f"Embedding generation complete. Processed: {result['processed']}, Failed: {result['failed']}")
    return result


def extract_metrics():
    """Extract financial metrics from filings using Claude."""
    from app.services.claude_client import get_claude_client

    # Check if Claude API is configured
    try:
        claude = get_claude_client()
        if not claude.is_configured:
            log("SKIPPED: Anthropic API key not configured")
            log("  Set ANTHROPIC_API_KEY in .env to enable metrics extraction")
            return 0
    except Exception as e:
        log(f"SKIPPED: Claude client error - {e}")
        return 0

    snowflake = get_snowflake_client()
    metrics_engine = get_metrics_engine()

    log("Starting metrics extraction using FINANCIAL_STATEMENTS chunks...")

    # Get target companies
    companies = snowflake.get_companies()

    total_metrics = 0
    for company in companies:
        ticker = company["TICKER"]
        company_name = company["COMPANY_NAME"]
        log(f"Extracting metrics for {ticker}...")

        # Get 10-K filings (best for financial metrics)
        filings = snowflake.get_filings(ticker=ticker, filing_type="10-K", limit=5)

        for filing in filings:
            sec_doc_id = filing["SEC_DOCUMENT_ID"]
            filing_date = str(filing["PERIOD_END_DATE"])

            # Get FINANCIAL_STATEMENTS chunks for this filing from our chunks table
            with snowflake.get_cursor() as cursor:
                cursor.execute(f"""
                    SELECT chunk_text
                    FROM {snowflake.app_db}.document_chunks
                    WHERE company_ticker = %s
                    AND section_name = 'FINANCIAL_STATEMENTS'
                    AND chunk_id LIKE %s
                    ORDER BY chunk_index
                    LIMIT 10
                """, (ticker, f"{sec_doc_id}%"))
                chunks = cursor.fetchall()

            if not chunks:
                log(f"  Skipping {sec_doc_id} - no FINANCIAL_STATEMENTS chunks")
                continue

            # Combine chunks into financial text (up to ~50K chars for Claude)
            financial_text = "\n\n".join([c["CHUNK_TEXT"] for c in chunks])[:50000]

            try:
                # Extract and store metrics using financial statements text
                metrics = metrics_engine.process_filing_metrics(
                    filing_text=financial_text,
                    company_ticker=ticker,
                    company_name=company_name,
                    filing_type="10-K",
                    filing_date=filing_date
                )

                stored = metrics_engine.store_metrics(metrics)
                total_metrics += stored
                log(f"  {sec_doc_id}: {stored} metrics extracted")
            except Exception as e:
                log(f"  Error extracting metrics from {sec_doc_id}: {e}")

    log(f"Metrics extraction complete. Total metrics: {total_metrics}")
    return total_metrics


def analyze_risks():
    """Perform risk analysis on filings using Claude."""
    from app.services.claude_client import get_claude_client

    # Check if Claude API is configured
    try:
        claude = get_claude_client()
        if not claude.is_configured:
            log("SKIPPED: Anthropic API key not configured")
            log("  Set ANTHROPIC_API_KEY in .env to enable risk analysis")
            return 0
    except Exception as e:
        log(f"SKIPPED: Claude client error - {e}")
        return 0

    snowflake = get_snowflake_client()
    risk_analyzer = get_risk_analyzer()

    log("Starting risk analysis...")

    # Get target companies
    companies = snowflake.get_companies()

    total_assessments = 0
    for company in companies:
        ticker = company["TICKER"]
        company_name = company["COMPANY_NAME"]
        log(f"Analyzing risks for {ticker}...")

        # Get filings for this company
        filings = snowflake.get_filings(ticker=ticker, limit=10)

        for filing in filings:
            sec_doc_id = filing["SEC_DOCUMENT_ID"]

            # Get filing content
            content = snowflake.get_filing_content(sec_doc_id)
            if not content or not content.get("FILING_TEXT"):
                continue

            try:
                # Analyze risks
                assessments = risk_analyzer.analyze_risks(
                    filing_text=content["FILING_TEXT"],
                    company_ticker=ticker,
                    company_name=company_name,
                    filing_date=str(content["PERIOD_END_DATE"])
                )

                stored = risk_analyzer.store_assessments(assessments)
                total_assessments += stored
                log(f"  {sec_doc_id}: {stored} risk assessments")
            except Exception as e:
                log(f"  Error analyzing risks in {sec_doc_id}: {e}")

    log(f"Risk analysis complete. Total assessments: {total_assessments}")
    return total_assessments


def main():
    """Run the complete batch processing pipeline."""
    log("=" * 60)
    log("COMPANY RISK INTELLIGENCE - BATCH PROCESSOR")
    log("=" * 60)
    log("")
    log("Data Sources:")
    log("  Read from: SEC_FILINGS_DEMO_DATA.CYBERSYN (shared)")
    log("  Write to:  COMPANY_INTELLIGENCE.APP_DATA (our DB)")
    log("")

    start_time = datetime.now()

    # Step 1: Process filings into chunks
    log("\n--- STEP 1: Processing Filings ---")
    chunks = process_filings()

    # Step 2: Generate embeddings
    log("\n--- STEP 2: Generating Embeddings ---")
    embeddings = generate_embeddings()

    # Step 3: Extract financial metrics
    log("\n--- STEP 3: Extracting Financial Metrics ---")
    metrics = extract_metrics()

    # Step 4: Analyze risks
    log("\n--- STEP 4: Analyzing Risks ---")
    risks = analyze_risks()

    # Summary
    elapsed = datetime.now() - start_time
    log("\n" + "=" * 60)
    log("BATCH PROCESSING COMPLETE")
    log("=" * 60)
    log(f"Total time: {elapsed}")
    log(f"Document chunks created: {chunks}")
    log(f"Embeddings generated: {embeddings.get('processed', 0)}")
    log(f"Financial metrics extracted: {metrics}")
    log(f"Risk assessments created: {risks}")


if __name__ == "__main__":
    main()
