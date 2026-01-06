import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Metrics", page_icon="📈", layout="wide")

API_BASE_URL = "http://localhost:8000/api"


def get_metrics(ticker: str):
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/{ticker}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_metric_history(ticker: str, metric_name: str):
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/{ticker}/history/{metric_name}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("📈 Financial Metrics")

    ticker = st.session_state.get('selected_ticker')

    if not ticker:
        st.warning("Please select a company from the sidebar on the main page.")
        return

    st.header(f"Financial Analysis: {ticker}")

    metrics = get_metrics(ticker)

    if not metrics or not metrics.get("metrics"):
        st.info("No financial metrics available for this company. Run the batch processor to generate metrics.")
        return

    # Organize metrics by category
    profitability = ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa']
    leverage = ['debt_to_equity', 'current_ratio', 'quick_ratio', 'interest_coverage', 'debt_to_ebitda']
    growth = ['revenue', 'net_income', 'eps']

    st.markdown("---")

    # Profitability Metrics
    st.subheader("📊 Profitability Metrics")
    cols = st.columns(5)

    for i, metric in enumerate(profitability):
        if metric in metrics["metrics"]:
            data = metrics["metrics"][metric]
            with cols[i]:
                delta = data.get('yoy_change')
                st.metric(
                    metric.replace('_', ' ').title(),
                    f"{data['value']:.1f}%" if 'margin' in metric or metric in ['roe', 'roa'] else f"{data['value']:.2f}",
                    delta=f"{delta:.1f}%" if delta else None
                )

    st.markdown("---")

    # Leverage Metrics
    st.subheader("💰 Leverage & Solvency")
    cols = st.columns(5)

    for i, metric in enumerate(leverage):
        if metric in metrics["metrics"]:
            data = metrics["metrics"][metric]
            with cols[i]:
                delta = data.get('yoy_change')
                # For leverage metrics, higher is often worse
                is_inverse = metric in ['debt_to_equity', 'debt_to_ebitda']
                st.metric(
                    metric.replace('_', ' ').title(),
                    f"{data['value']:.2f}",
                    delta=f"{delta:.1f}%" if delta else None,
                    delta_color="inverse" if is_inverse else "normal"
                )

    st.markdown("---")

    # Historical trend chart
    st.subheader("📉 Metric Trends")

    available_metrics = list(metrics["metrics"].keys())
    selected_metric = st.selectbox(
        "Select metric to view history",
        options=available_metrics,
        format_func=lambda x: x.replace('_', ' ').title()
    )

    if selected_metric:
        history = get_metric_history(ticker, selected_metric)

        if history and history.get("history"):
            df = pd.DataFrame(history["history"])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

            fig = px.line(
                df,
                x='date',
                y='value',
                title=f"{selected_metric.replace('_', ' ').title()} Over Time",
                markers=True
            )

            # Color anomalies differently
            if 'is_anomaly' in df.columns:
                anomaly_df = df[df['is_anomaly'] == True]
                if not anomaly_df.empty:
                    fig.add_trace(go.Scatter(
                        x=anomaly_df['date'],
                        y=anomaly_df['value'],
                        mode='markers',
                        marker=dict(color='red', size=12, symbol='x'),
                        name='Anomaly'
                    ))

            fig.update_layout(
                xaxis_title="Filing Date",
                yaxis_title=selected_metric.replace('_', ' ').title(),
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for this metric.")

    st.markdown("---")

    # All metrics table
    st.subheader("📋 All Metrics Summary")

    metrics_data = []
    for name, data in metrics["metrics"].items():
        metrics_data.append({
            "Metric": name.replace('_', ' ').title(),
            "Value": data['value'],
            "Unit": data['unit'],
            "Date": data['date'],
            "YoY Change": f"{data['yoy_change']:.1f}%" if data.get('yoy_change') else "N/A"
        })

    df = pd.DataFrame(metrics_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Anomalies highlight
    if metrics.get("anomalies"):
        st.warning(f"⚠️ {len(metrics['anomalies'])} anomalies detected in metrics")
        for anomaly in metrics["anomalies"]:
            st.write(f"- **{anomaly['metric']}**: {anomaly['value']} (on {anomaly['date']})")


if __name__ == "__main__":
    main()
