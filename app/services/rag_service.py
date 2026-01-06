from dataclasses import dataclass
from typing import Any

from app.services.snowflake_client import get_snowflake_client
from app.services.embedding_service import get_embedding_service
from app.services.claude_client import get_claude_client


@dataclass
class RAGResponse:
    answer: str
    confidence: str
    sources: list[dict]
    caveats: list[str]


class RAGService:
    def __init__(self):
        self.snowflake = get_snowflake_client()
        self.embedding_service = get_embedding_service()
        self.claude = get_claude_client()

    def search_context(
        self,
        query: str,
        ticker: str | None = None,
        section_filter: str | None = None,
        top_k: int = 5
    ) -> list[dict]:
        # Get relevant chunks using vector search
        results = self.embedding_service.search_similar(
            query_text=query,
            ticker=ticker,
            limit=top_k
        )

        # Filter by section if specified
        if section_filter:
            results = [r for r in results if r.get("SECTION_NAME") == section_filter]

        # Format results
        formatted = []
        for r in results:
            formatted.append({
                "chunk_id": r.get("CHUNK_ID"),
                "company_ticker": r.get("COMPANY_TICKER"),
                "filing_type": r.get("FILING_TYPE"),
                "filing_date": str(r.get("FILING_DATE")) if r.get("FILING_DATE") else None,
                "section_name": r.get("SECTION_NAME"),
                "chunk_text": r.get("CHUNK_TEXT"),
                "similarity": r.get("SIMILARITY")
            })

        return formatted

    def answer_question(
        self,
        question: str,
        ticker: str | None = None,
        top_k: int = 5
    ) -> RAGResponse:
        # Search for relevant context
        context_chunks = self.search_context(
            query=question,
            ticker=ticker,
            top_k=top_k
        )

        if not context_chunks:
            return RAGResponse(
                answer="I couldn't find relevant information in the SEC filings to answer your question.",
                confidence="LOW",
                sources=[],
                caveats=["No relevant documents found"]
            )

        # Get company name from ticker
        company_name = ticker or "the company"
        if ticker:
            companies = self.snowflake.get_companies()
            for c in companies:
                if c.get("TICKER") == ticker:
                    company_name = c.get("COMPANY_NAME", ticker)
                    break

        # Generate answer using Claude
        response = self.claude.answer_question(
            question=question,
            context_chunks=context_chunks,
            company_name=company_name
        )

        # Format sources
        sources = []
        for chunk in context_chunks:
            sources.append({
                "filing_type": chunk.get("filing_type"),
                "filing_date": chunk.get("filing_date"),
                "section": chunk.get("section_name"),
                "relevance": chunk.get("similarity")
            })

        return RAGResponse(
            answer=response.get("answer", "Unable to generate answer"),
            confidence=response.get("confidence", "LOW"),
            sources=sources,
            caveats=response.get("caveats", [])
        )

    def compare_filings(
        self,
        ticker: str,
        section_name: str = "RISK_FACTORS"
    ) -> dict:
        # Get chunks from different periods
        query = f"""
        SELECT
            chunk_text,
            filing_date,
            filing_type
        FROM document_chunks
        WHERE company_ticker = '{ticker}'
        AND section_name = '{section_name}'
        ORDER BY filing_date DESC
        LIMIT 2
        """

        results = self.snowflake.execute_query(query)

        if len(results) < 2:
            return {
                "comparison": "Not enough historical data for comparison",
                "current_period": None,
                "previous_period": None
            }

        current = results[0]
        previous = results[1]

        # Get company name
        company_name = ticker
        companies = self.snowflake.get_companies()
        for c in companies:
            if c.get("TICKER") == ticker:
                company_name = c.get("COMPANY_NAME", ticker)
                break

        # Compare using Claude
        comparison = self.claude.summarize_changes(
            current_text=current["CHUNK_TEXT"],
            previous_text=previous["CHUNK_TEXT"],
            section_name=section_name,
            company_name=company_name
        )

        return {
            "comparison": comparison,
            "current_period": {
                "filing_type": current["FILING_TYPE"],
                "filing_date": str(current["FILING_DATE"])
            },
            "previous_period": {
                "filing_type": previous["FILING_TYPE"],
                "filing_date": str(previous["FILING_DATE"])
            }
        }

    def get_section_summary(
        self,
        ticker: str,
        section_name: str
    ) -> dict:
        # Get latest chunks for section
        chunks = self.snowflake.get_document_chunks(
            ticker=ticker,
            section_name=section_name,
            limit=10
        )

        if not chunks:
            return {
                "summary": "No data available for this section",
                "section": section_name,
                "ticker": ticker
            }

        # Combine chunk texts
        combined_text = "\n\n".join([c["CHUNK_TEXT"] for c in chunks])

        # Get company name
        company_name = ticker
        companies = self.snowflake.get_companies()
        for c in companies:
            if c.get("TICKER") == ticker:
                company_name = c.get("COMPANY_NAME", ticker)
                break

        # Generate summary using Claude
        summary = self.claude.generate(
            prompt=f"""Summarize the key points from the {section_name} section
            of {company_name}'s SEC filing. Focus on the most important information
            for an investment banker.

            Text:
            {combined_text[:10000]}

            Provide a concise summary in 3-5 bullet points.""",
            system="You are a financial analyst summarizing SEC filings.",
            temperature=0.3
        )

        return {
            "summary": summary,
            "section": section_name,
            "ticker": ticker,
            "filing_date": str(chunks[0]["FILING_DATE"]) if chunks else None
        }


def get_rag_service() -> RAGService:
    return RAGService()
