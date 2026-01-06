import streamlit as st
import requests

st.set_page_config(page_title="Q&A Chat", page_icon="💬", layout="wide")

API_BASE_URL = "http://localhost:8000/api"


def ask_question(question: str, ticker: str | None = None):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"question": question, "ticker": ticker, "top_k": 5}
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error: {e}")
    return None


def get_suggested_questions(ticker: str | None = None):
    try:
        params = {"ticker": ticker} if ticker else {}
        response = requests.get(f"{API_BASE_URL}/chat/suggested-questions", params=params)
        if response.status_code == 200:
            return response.json().get("questions", [])
    except:
        pass
    return []


def summarize_section(ticker: str, section: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/summarize-section",
            json={"ticker": ticker, "section": section}
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("💬 Q&A Chat")

    ticker = st.session_state.get('selected_ticker')

    st.markdown("Ask questions about SEC filings and get AI-powered answers with source citations.")

    if ticker:
        st.info(f"Currently analyzing: **{ticker}**")
    else:
        st.warning("Select a company from the main page for company-specific questions.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Suggested questions
    st.markdown("### 💡 Suggested Questions")
    suggestions = get_suggested_questions(ticker)

    cols = st.columns(2)
    for i, question in enumerate(suggestions[:6]):
        with cols[i % 2]:
            if st.button(question, key=f"suggestion_{i}", use_container_width=True):
                st.session_state.pending_question = question

    st.markdown("---")

    # Quick section summary
    st.markdown("### 📄 Quick Section Summary")
    col1, col2 = st.columns([3, 1])

    with col1:
        section = st.selectbox(
            "Select section",
            options=["RISK_FACTORS", "MD&A", "BUSINESS", "FINANCIAL_STATEMENTS"],
            format_func=lambda x: x.replace('_', ' ').title()
        )

    with col2:
        summarize_btn = st.button("Summarize", disabled=not ticker)

    if summarize_btn and ticker:
        with st.spinner("Generating summary..."):
            summary = summarize_section(ticker, section)
            if summary:
                st.markdown(f"### {section.replace('_', ' ').title()} Summary")
                st.write(summary.get("summary", "No summary available"))
                if summary.get("filing_date"):
                    st.caption(f"Source: Filing from {summary['filing_date']}")

    st.markdown("---")

    # Chat interface
    st.markdown("### 💬 Ask a Question")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and message.get("sources"):
                with st.expander("📚 Sources"):
                    for source in message["sources"]:
                        st.write(f"- {source.get('filing_type', 'N/A')} ({source.get('filing_date', 'N/A')}) - {source.get('section', 'N/A')}")

                if message.get("confidence"):
                    st.caption(f"Confidence: {message['confidence']}")

    # Check for pending question from suggestion button
    if hasattr(st.session_state, 'pending_question') and st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None

        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Searching SEC filings..."):
                response = ask_question(question, ticker)

                if response:
                    st.markdown(response.get("answer", "I couldn't find an answer."))

                    if response.get("sources"):
                        with st.expander("📚 Sources"):
                            for source in response["sources"]:
                                st.write(f"- {source.get('filing_type', 'N/A')} ({source.get('filing_date', 'N/A')}) - {source.get('section', 'N/A')}")

                    if response.get("caveats"):
                        st.caption("⚠️ " + ", ".join(response["caveats"]))

                    st.caption(f"Confidence: {response.get('confidence', 'N/A')}")

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("answer", ""),
                        "sources": response.get("sources", []),
                        "confidence": response.get("confidence")
                    })
                else:
                    st.error("Failed to get a response. Please try again.")

    # Chat input
    if prompt := st.chat_input("Ask about SEC filings..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Searching SEC filings..."):
                response = ask_question(prompt, ticker)

                if response:
                    st.markdown(response.get("answer", "I couldn't find an answer."))

                    if response.get("sources"):
                        with st.expander("📚 Sources"):
                            for source in response["sources"]:
                                st.write(f"- {source.get('filing_type', 'N/A')} ({source.get('filing_date', 'N/A')}) - {source.get('section', 'N/A')}")

                    if response.get("caveats"):
                        st.caption("⚠️ " + ", ".join(response["caveats"]))

                    st.caption(f"Confidence: {response.get('confidence', 'N/A')}")

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("answer", ""),
                        "sources": response.get("sources", []),
                        "confidence": response.get("confidence")
                    })
                else:
                    st.error("Failed to get a response. Please try again.")

    # Clear chat button
    if st.session_state.messages:
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
