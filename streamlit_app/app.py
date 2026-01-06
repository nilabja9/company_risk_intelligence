import streamlit as st
import requests

# Page configuration
st.set_page_config(
    page_title="Company Risk Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:8000/api"


def get_companies():
    """Fetch list of companies from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/companies")
        if response.status_code == 200:
            return response.json().get("companies", [])
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure the backend is running.")
    return []


def main():
    # Sidebar
    st.sidebar.title("Company Risk Intelligence")
    st.sidebar.markdown("---")

    # Company selector
    companies = get_companies()
    if companies:
        company_options = {f"{c['ticker']} - {c['company_name']}": c['ticker'] for c in companies}
        selected = st.sidebar.selectbox(
            "Select Company",
            options=list(company_options.keys()),
            key="company_selector"
        )
        selected_ticker = company_options.get(selected)
        st.session_state['selected_ticker'] = selected_ticker
    else:
        st.sidebar.warning("No companies loaded")
        selected_ticker = None

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Links")
    st.sidebar.page_link("pages/1_Company_Overview.py", label="Company Overview")
    st.sidebar.page_link("pages/2_Financial_Metrics.py", label="Financial Metrics")
    st.sidebar.page_link("pages/3_Risk_Analysis.py", label="Risk Analysis")
    st.sidebar.page_link("pages/4_QA_Chat.py", label="Q&A Chat")

    # Main content
    st.title("Company Risk Intelligence Dashboard")
    st.markdown("### AI-Powered SEC Filing Analysis for Investment Bankers")

    st.markdown("---")

    # Overview cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Companies Tracked",
            value=len(companies) if companies else 0
        )

    with col2:
        st.metric(
            label="Filing Types",
            value="10-K, 10-Q, 8-K"
        )

    with col3:
        st.metric(
            label="Analysis Types",
            value="3",
            help="Financial Metrics, Risk Assessment, RAG Q&A"
        )

    with col4:
        st.metric(
            label="AI Model",
            value="Claude"
        )

    st.markdown("---")

    # Feature overview
    st.markdown("## Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Financial Metrics Engine")
        st.markdown("""
        - Profitability ratios (margins, ROE, ROA)
        - Leverage ratios (debt-to-equity, interest coverage)
        - Growth metrics (YoY revenue, EPS growth)
        - Anomaly detection for unusual changes
        """)

        st.markdown("### 🔍 Document Intelligence (RAG)")
        st.markdown("""
        - Ask questions about SEC filings
        - Get answers with source citations
        - Compare filing sections across periods
        - Section summaries on demand
        """)

    with col2:
        st.markdown("### ⚠️ Risk & Red Flag Analysis")
        st.markdown("""
        - Regulatory risk detection
        - Litigation monitoring
        - Accounting language analysis
        - Risk scoring by category
        """)

        st.markdown("### 📄 Filing Analysis")
        st.markdown("""
        - 10-K Annual Reports
        - 10-Q Quarterly Reports
        - 8-K Material Events
        - Section-level chunking and search
        """)

    st.markdown("---")

    # Quick start
    st.markdown("## Quick Start")

    if selected_ticker:
        st.success(f"Selected company: **{selected_ticker}**")
        st.markdown("Navigate using the sidebar to explore:")
        st.markdown("1. **Company Overview** - Key stats and recent filings")
        st.markdown("2. **Financial Metrics** - Ratios and trend analysis")
        st.markdown("3. **Risk Analysis** - Risk scores and red flags")
        st.markdown("4. **Q&A Chat** - Ask questions about filings")
    else:
        st.info("Select a company from the sidebar to get started")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Company Risk Intelligence | Powered by Claude AI & Snowflake"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
