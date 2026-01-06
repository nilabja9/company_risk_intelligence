# Objective

The objective of this setup file is to create a financial statement analyzer and risk intelligence app. This app is for investment bankers to quickly prompt questions about companies and their earnings to get key insights on business decisions

# Different layers

## Scope + Data

Pick 10–20 S&P 500 companies
Pull 10-K, 10-Q, 8-k from SEC Data already present in database SEC_FILINGS_DEMO_DATA in Snowflake account, details of which can be found in the export_variables file

## Document Intelligence

Chunk filings intelligently (by section and attributes)
Generate embeddings
Implement RAG Q&A:
“What changed in revenue drivers?”
“Summarize key risks”

## Financial Metrics Engine

Extract structured numbers (LLM-assisted parsing)
Compute:
    -Margins
    -Leverage ratios
    -YoY deltas
    -Flag anomalies

## Risk & Red Flag Layer

LLM prompts for:

    Risk factor changes
    Litigation mentions
    Accounting language shifts
    Store explainability metadata

## API + UI

FastAPI endpoints
Streamlit dashboard:

    Company selector
    Charts
    Narrative output

## Polish

README with architecture diagram
Sample screenshots
Performance metrics

