# Company Risk Intelligence

An AI-powered financial analysis platform for Investment Bankers to analyze SEC filings (10-K, 10-Q, 8-K) and extract actionable risk intelligence from S&P 500 companies.

## Features

- **RAG-Powered Q&A**: Ask natural language questions about company risks, financials, and operations
- **Financial Metrics Extraction**: Automated extraction of key financial ratios and metrics using Claude AI
- **Risk Analysis**: AI-driven identification and scoring of risk factors across multiple categories
- **Interactive Dashboard**: Streamlit-based UI for exploring company data and insights
- **Vector Search**: Semantic search across SEC filing sections using Snowflake Cortex embeddings

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT DASHBOARD                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │ Company  │ │ Financial│ │  Risk    │ │   RAG Q&A Chat       │   │
│  │ Selector │ │  Charts  │ │  Flags   │ │   Interface          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐│
│  │ /api/company │ │ /api/metrics │ │ /api/chat (RAG endpoint)     ││
│  │ /api/risks   │ │ /api/filings │ │                              ││
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Claude API    │     │ Snowflake Cortex  │     │   Snowflake DB    │
│ (Analysis &   │     │ (Embeddings &     │     │ SEC_FILINGS_DATA  │
│  Extraction)  │     │  Vector Search)   │     │ (10-K, 10-Q, 8-K) │
└───────────────┘     └───────────────────┘     └───────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (Python 3.11+) |
| Frontend | Streamlit |
| LLM | Claude API (Anthropic) |
| Embeddings | Snowflake Cortex (EMBED_TEXT_768) |
| Vector Search | Snowflake VECTOR_COSINE_SIMILARITY |
| Database | Snowflake |

## Project Structure

```
company_risk_intelligence/
├── app/
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   ├── api/routes/
│   │   ├── companies.py           # Company listing endpoints
│   │   ├── filings.py             # Filing retrieval endpoints
│   │   ├── metrics.py             # Financial metrics endpoints
│   │   ├── risks.py               # Risk analysis endpoints
│   │   └── chat.py                # RAG Q&A endpoints
│   ├── services/
│   │   ├── snowflake_client.py    # Snowflake connection & queries
│   │   ├── document_processor.py  # Chunking & preprocessing
│   │   ├── embedding_service.py   # Cortex embedding generation
│   │   ├── rag_service.py         # RAG retrieval & generation
│   │   ├── metrics_engine.py      # Financial calculations
│   │   ├── risk_analyzer.py       # Risk/red flag detection
│   │   └── claude_client.py       # Claude API wrapper
│   └── models/                    # Pydantic data models
├── streamlit_app/
│   ├── app.py                     # Main Streamlit application
│   └── pages/                     # Dashboard pages
├── scripts/
│   └── batch_process.py           # Data processing pipeline
├── requirements.txt
└── .env                           # Environment variables (not in repo)
```

## Installation

### Prerequisites

- Python 3.11+
- Snowflake account with access to SEC_FILINGS_DEMO_DATA
- Anthropic API key

### Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:nilabja9/company_risk_intelligence.git
   cd company_risk_intelligence
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   # Snowflake Configuration
   SNOWFLAKE_ACCOUNT=your_account_identifier
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   SNOWFLAKE_DATABASE=COMPANY_INTELLIGENCE
   SNOWFLAKE_SCHEMA=APP_DATA

   # Anthropic API
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

5. **Initialize Snowflake tables**

   Run the batch processor to create tables and process data:
   ```bash
   python scripts/batch_process.py
   ```

## Running the Application

### Start the Backend API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Start the Streamlit Dashboard

```bash
streamlit run streamlit_app/app.py --server.port 8501
```

The dashboard will be available at `http://localhost:8501`

## API Endpoints

### Companies
- `GET /api/companies` - List all tracked companies

### Filings
- `GET /api/filings` - List SEC filings (filterable by ticker, type)
- `GET /api/filings/{accession_number}` - Get filing content
- `GET /api/filings/{ticker}/sections` - Get document chunks for a company

### Metrics
- `GET /api/metrics/{ticker}` - Get financial metrics for a company
- `GET /api/metrics/{ticker}/history/{metric_name}` - Get metric history
- `GET /api/metrics/{ticker}/compare?compare_to={ticker2}` - Compare two companies

### Risk Analysis
- `GET /api/risks/{ticker}` - Get risk assessment summary

### RAG Q&A
- `POST /api/chat` - Ask questions about company filings
  ```json
  {
    "question": "What supply chain risks does Apple face?",
    "ticker": "AAPL"
  }
  ```

## Target Companies

The platform tracks 15 diverse S&P 500 companies across sectors:

| Ticker | Company | Sector |
|--------|---------|--------|
| AAPL | Apple Inc. | Technology |
| MSFT | Microsoft Corp. | Technology |
| GOOGL | Alphabet Inc. | Technology |
| JPM | JPMorgan Chase | Financials |
| BAC | Bank of America | Financials |
| JNJ | Johnson & Johnson | Healthcare |
| UNH | UnitedHealth Group | Healthcare |
| XOM | Exxon Mobil | Energy |
| CVX | Chevron | Energy |
| WMT | Walmart | Consumer Staples |
| PG | Procter & Gamble | Consumer Staples |
| CAT | Caterpillar | Industrials |
| UPS | United Parcel Service | Industrials |
| AMT | American Tower | Real Estate |
| NEE | NextEra Energy | Utilities |

## Financial Metrics

### Profitability
- Gross Margin, Operating Margin, Net Profit Margin
- ROE (Return on Equity), ROA (Return on Assets)

### Leverage & Solvency
- Debt-to-Equity, Interest Coverage
- Current Ratio, Quick Ratio
- Debt-to-EBITDA

### Raw Financials
- Revenue, Gross Profit, Operating Income, Net Income
- Total Assets, Total Liabilities, Shareholders' Equity
- Current Assets, Current Liabilities, Total Debt

## Risk Categories

The platform analyzes risks across six categories:

| Category | Description |
|----------|-------------|
| **FINANCIAL** | Debt obligations, liquidity concerns, credit risks |
| **OPERATIONAL** | Supply chain, workforce, infrastructure risks |
| **MARKET** | Competition, economic conditions, demand fluctuations |
| **REGULATORY** | Compliance requirements, government investigations |
| **LITIGATION** | Lawsuits, legal proceedings, settlements |
| **ACCOUNTING** | Financial reporting, audit concerns, restatements |

## Data Pipeline

```
1. Extract Filings     → Query Snowflake for 10-K, 10-Q, 8-K filings
2. Chunk Documents     → Split by section (Risk Factors, MD&A, etc.)
3. Generate Embeddings → Snowflake Cortex EMBED_TEXT_768
4. Extract Metrics     → Claude parses financial figures
5. Risk Analysis       → Claude identifies and scores risk factors
```

## Example Usage

### RAG Q&A
```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat",
    json={
        "question": "What cybersecurity risks does Microsoft face?",
        "ticker": "MSFT"
    }
)
print(response.json()["answer"])
```

### Get Company Metrics
```python
response = requests.get("http://localhost:8000/api/metrics/AAPL")
metrics = response.json()
print(f"Apple Debt/Equity: {metrics['metrics']['debt_to_equity']['value']}")
```

### Get Risk Summary
```python
response = requests.get("http://localhost:8000/api/risks/JNJ")
risks = response.json()
print(f"Overall Risk Score: {risks['overall_score']}")
```

## License

This project is for educational and demonstration purposes.

## Acknowledgments

- SEC filing data provided via Snowflake Marketplace (Cybersyn)
- AI capabilities powered by Anthropic Claude
- Vector embeddings via Snowflake Cortex
