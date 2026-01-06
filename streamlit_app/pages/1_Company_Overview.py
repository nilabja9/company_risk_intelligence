import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Company Overview", page_icon="🏢", layout="wide")

API_BASE_URL = "http://localhost:8000/api"


def get_company_info(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/companies/{ticker}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_filings(ticker: str, limit: int = 10):
    try:
        response = requests.get(f"{API_BASE_URL}/filings", params={"ticker": ticker, "limit": limit})
        if response.status_code == 200:
            return response.json().get("filings", [])
    except:
        pass
    return []


def get_metrics_summary(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/{ticker}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_risk_summary(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/risks/{ticker}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("🏢 Company Overview")

    # Get selected ticker from session state
    ticker = st.session_state.get('selected_ticker')

    if not ticker:
        st.warning("Please select a company from the sidebar on the main page.")
        return

    # Company header
    company = get_company_info(ticker)
    if company:
        st.header(f"{company.get('company_name', ticker)} ({ticker})")
        if company.get('sector'):
            st.markdown(f"**Sector:** {company['sector']}")
    else:
        st.header(ticker)

    st.markdown("---")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    metrics = get_metrics_summary(ticker)
    risks = get_risk_summary(ticker)

    with col1:
        if metrics and metrics.get("metrics", {}).get("net_margin"):
            margin = metrics["metrics"]["net_margin"]
            st.metric(
                "Net Margin",
                f"{margin.get('value', 'N/A')}%",
                delta=f"{margin.get('yoy_change', 0):.1f}%" if margin.get('yoy_change') else None
            )
        else:
            st.metric("Net Margin", "N/A")

    with col2:
        if metrics and metrics.get("metrics", {}).get("roe"):
            roe = metrics["metrics"]["roe"]
            st.metric(
                "ROE",
                f"{roe.get('value', 'N/A')}%",
                delta=f"{roe.get('yoy_change', 0):.1f}%" if roe.get('yoy_change') else None
            )
        else:
            st.metric("ROE", "N/A")

    with col3:
        if metrics and metrics.get("metrics", {}).get("debt_to_equity"):
            d2e = metrics["metrics"]["debt_to_equity"]
            st.metric(
                "Debt/Equity",
                f"{d2e.get('value', 'N/A'):.2f}",
                delta=f"{d2e.get('yoy_change', 0):.1f}%" if d2e.get('yoy_change') else None,
                delta_color="inverse"
            )
        else:
            st.metric("Debt/Equity", "N/A")

    with col4:
        if risks:
            score = risks.get("overall_score", 0)
            color = "🟢" if score < 40 else "🟡" if score < 70 else "🔴"
            st.metric(
                "Risk Score",
                f"{color} {score:.0f}/100"
            )
        else:
            st.metric("Risk Score", "N/A")

    st.markdown("---")

    # Two column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 Recent Filings")
        filings = get_filings(ticker)

        if filings:
            df = pd.DataFrame(filings)
            df['filing_date'] = pd.to_datetime(df['filing_date']).dt.strftime('%Y-%m-%d')
            df = df[['form_type', 'filing_date', 'accession_number']]
            df.columns = ['Type', 'Date', 'Accession #']
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No filings found for this company.")

    with col2:
        st.subheader("⚠️ Risk Flags")

        if risks and risks.get("recent_flags"):
            for flag in risks["recent_flags"][:5]:
                severity_color = "🔴" if flag['score'] >= 70 else "🟡" if flag['score'] >= 50 else "🟢"
                with st.expander(f"{severity_color} {flag['category']}"):
                    st.write(f"**Score:** {flag['score']}/100")
                    st.write(f"**Date:** {flag['date']}")
                    st.write(flag['summary'])
        else:
            st.success("No significant risk flags detected.")

    st.markdown("---")

    # Anomalies section
    st.subheader("📊 Metric Anomalies")

    if metrics and metrics.get("anomalies"):
        anomaly_df = pd.DataFrame(metrics["anomalies"])
        st.dataframe(anomaly_df, use_container_width=True, hide_index=True)
    else:
        st.success("No metric anomalies detected.")


if __name__ == "__main__":
    main()
