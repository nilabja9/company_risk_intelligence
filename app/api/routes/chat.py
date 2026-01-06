from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    ticker: str | None = None
    top_k: int = 5


class ChatResponse(BaseModel):
    answer: str
    confidence: str
    sources: list[dict]
    caveats: list[str]


class SectionSummaryRequest(BaseModel):
    ticker: str
    section: str


@router.post("", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """Ask a question about SEC filings using RAG."""
    rag = get_rag_service()

    response = rag.answer_question(
        question=request.question,
        ticker=request.ticker.upper() if request.ticker else None,
        top_k=request.top_k
    )

    return ChatResponse(
        answer=response.answer,
        confidence=response.confidence,
        sources=response.sources,
        caveats=response.caveats
    )


@router.post("/search")
async def search_documents(
    query: str,
    ticker: str | None = None,
    section: str | None = None,
    limit: int = 10
):
    """Search for relevant document chunks."""
    rag = get_rag_service()

    results = rag.search_context(
        query=query,
        ticker=ticker.upper() if ticker else None,
        section_filter=section,
        top_k=limit
    )

    return {
        "query": query,
        "ticker": ticker,
        "section_filter": section,
        "results": results,
        "count": len(results)
    }


@router.post("/summarize-section")
async def summarize_section(request: SectionSummaryRequest):
    """Get a summary of a specific filing section."""
    rag = get_rag_service()

    summary = rag.get_section_summary(
        ticker=request.ticker.upper(),
        section_name=request.section.upper()
    )

    return summary


@router.get("/suggested-questions")
async def get_suggested_questions(ticker: str | None = None):
    """Get suggested questions for the chat interface."""
    questions = [
        "What are the main risk factors mentioned in the latest filing?",
        "How has revenue changed year-over-year?",
        "What are the key litigation concerns?",
        "Summarize the Management Discussion and Analysis section",
        "What are the main competitive risks?",
        "Are there any going concern issues mentioned?",
        "What regulatory challenges does the company face?",
        "How has the company's debt position changed?"
    ]

    if ticker:
        questions = [
            f"{q} for {ticker.upper()}" if "for" not in q.lower() else q
            for q in questions
        ]

    return {"questions": questions}
