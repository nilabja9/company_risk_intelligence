from functools import lru_cache

from app.config import Settings, get_settings
from app.services.snowflake_client import SnowflakeClient, get_snowflake_client
from app.services.claude_client import ClaudeClient, get_claude_client
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.rag_service import RAGService, get_rag_service
from app.services.metrics_engine import MetricsEngine, get_metrics_engine
from app.services.risk_analyzer import RiskAnalyzer, get_risk_analyzer


def get_settings_dependency() -> Settings:
    return get_settings()


def get_snowflake_dependency() -> SnowflakeClient:
    return get_snowflake_client()


def get_claude_dependency() -> ClaudeClient:
    return get_claude_client()


def get_embedding_dependency() -> EmbeddingService:
    return get_embedding_service()


def get_rag_dependency() -> RAGService:
    return get_rag_service()


def get_metrics_dependency() -> MetricsEngine:
    return get_metrics_engine()


def get_risk_dependency() -> RiskAnalyzer:
    return get_risk_analyzer()
