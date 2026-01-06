from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import companies, filings, metrics, risks, chat

settings = get_settings()

app = FastAPI(
    title="Company Risk Intelligence API",
    description="Financial statement analyzer and risk intelligence for investment bankers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(companies.router, prefix="/api")
app.include_router(filings.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(risks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Company Risk Intelligence API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/info")
async def api_info():
    return {
        "endpoints": {
            "companies": "/api/companies",
            "filings": "/api/filings",
            "metrics": "/api/metrics",
            "risks": "/api/risks",
            "chat": "/api/chat"
        },
        "target_companies": settings.target_companies,
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
