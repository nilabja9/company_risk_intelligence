import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Risk Analysis", page_icon="⚠️", layout="wide")

API_BASE_URL = "http://localhost:8000/api"


def get_risks(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/risks/{ticker}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_red_flags(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/risks/{ticker}/red-flags")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_risk_comparison(ticker: str, section: str = "RISK_FACTORS"):
    try:
        response = requests.get(
            f"{API_BASE_URL}/risks/{ticker}/compare-periods",
            params={"section": section}
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("⚠️ Risk Analysis")

    ticker = st.session_state.get('selected_ticker')

    if not ticker:
        st.warning("Please select a company from the sidebar on the main page.")
        return

    st.header(f"Risk Assessment: {ticker}")

    risks = get_risks(ticker)

    if not risks:
        st.info("No risk assessment data available. Run the batch processor to generate risk analysis.")
        return

    # Overall risk score gauge
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        score = risks.get("overall_score", 0)

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            title={'text': "Overall Risk Score"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkgray"},
                'steps': [
                    {'range': [0, 40], 'color': "lightgreen"},
                    {'range': [40, 70], 'color': "yellow"},
                    {'range': [70, 100], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))

        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Risk breakdown by category
    st.subheader("📊 Risk Breakdown by Category")

    if risks.get("risk_breakdown"):
        breakdown = risks["risk_breakdown"]

        # Radar chart for risk categories
        categories = list(breakdown.keys())
        values = [breakdown[cat].get("average_score", 0) for cat in categories]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Risk Score'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=False,
            height=400
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### Category Details")
            for cat, data in breakdown.items():
                score = data.get("average_score", 0)
                color = "🟢" if score < 40 else "🟡" if score < 70 else "🔴"
                st.write(f"{color} **{cat}**: {score:.0f}/100 ({data.get('count', 0)} assessments)")

    st.markdown("---")

    # Red flags section
    st.subheader("🚩 Red Flags")

    red_flags = get_red_flags(ticker)

    if red_flags and red_flags.get("flags"):
        for flag in red_flags["flags"]:
            with st.expander(f"🔴 {flag['category']} - Score: {flag['score']}/100"):
                st.write(f"**Date:** {flag['date']}")
                st.write(f"**Summary:** {flag['summary']}")
    else:
        st.success("✅ No high-severity risk flags detected")

    st.markdown("---")

    # Period comparison
    st.subheader("📈 Risk Factor Changes Between Periods")

    section = st.selectbox(
        "Select section to compare",
        options=["RISK_FACTORS", "MD&A", "LEGAL_PROCEEDINGS"],
        format_func=lambda x: x.replace('_', ' ').title()
    )

    comparison = get_risk_comparison(ticker, section)

    if comparison and comparison.get("comparison"):
        comp_data = comparison["comparison"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Current Period**")
            if comparison.get("current_period"):
                st.write(f"Filing: {comparison['current_period'].get('filing_type')}")
                st.write(f"Date: {comparison['current_period'].get('filing_date')}")

        with col2:
            st.markdown("**Previous Period**")
            if comparison.get("previous_period"):
                st.write(f"Filing: {comparison['previous_period'].get('filing_type')}")
                st.write(f"Date: {comparison['previous_period'].get('filing_date')}")

        st.markdown("---")

        if isinstance(comp_data, dict):
            if comp_data.get("summary"):
                st.markdown("### Summary")
                st.write(comp_data["summary"])

            if comp_data.get("additions"):
                st.markdown("### 🆕 New Risks/Concerns")
                for item in comp_data["additions"]:
                    st.write(f"- {item}")

            if comp_data.get("removals"):
                st.markdown("### ✅ Removed/Reduced Risks")
                for item in comp_data["removals"]:
                    st.write(f"- {item}")

            if comp_data.get("red_flags"):
                st.markdown("### 🚩 New Red Flags")
                for item in comp_data["red_flags"]:
                    st.error(item)

            significance = comp_data.get("significance", "UNKNOWN")
            sig_color = "🟢" if significance == "LOW" else "🟡" if significance == "MEDIUM" else "🔴"
            st.markdown(f"**Change Significance:** {sig_color} {significance}")
    else:
        st.info("Not enough historical data for period comparison.")


if __name__ == "__main__":
    main()
