from typing import Any
import json

from app.services.snowflake_client import get_snowflake_client


class EmbeddingService:
    def __init__(self):
        self.snowflake = get_snowflake_client()
        self.model = "snowflake-arctic-embed-m"  # 768-dimensional embeddings

    def generate_embedding(self, text: str) -> list[float]:
        query = f"""
        SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{self.model}', %s) as embedding
        """
        with self.snowflake.get_cursor() as cursor:
            cursor.execute(query, (text,))
            result = cursor.fetchone()
            if result and result.get("EMBEDDING"):
                return result["EMBEDDING"]
            return []

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def store_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        # Convert embedding list to string format for Snowflake VECTOR type
        embedding_str = str(embedding)
        query = f"""
        INSERT INTO {self.snowflake.app_db}.document_embeddings (chunk_id, embedding)
        SELECT %s, {embedding_str}::VECTOR(FLOAT, 768)
        """
        with self.snowflake.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, (chunk_id,))

    def generate_and_store_for_chunk(self, chunk_id: str, chunk_text: str) -> bool:
        try:
            embedding = self.generate_embedding(chunk_text)
            if embedding:
                self.store_embedding(chunk_id, embedding)
                return True
            return False
        except Exception as e:
            print(f"Error generating embedding for {chunk_id}: {e}")
            return False

    def process_all_chunks(self, batch_size: int = 100) -> dict[str, int]:
        query = f"""
        SELECT dc.chunk_id, dc.chunk_text
        FROM {self.snowflake.app_db}.document_chunks dc
        LEFT JOIN {self.snowflake.app_db}.document_embeddings de ON dc.chunk_id = de.chunk_id
        WHERE de.chunk_id IS NULL
        LIMIT %s
        """

        processed = 0
        failed = 0

        while True:
            chunks = self.snowflake.execute_query(query % batch_size)
            if not chunks:
                break

            for chunk in chunks:
                success = self.generate_and_store_for_chunk(
                    chunk["CHUNK_ID"],
                    chunk["CHUNK_TEXT"]
                )
                if success:
                    processed += 1
                else:
                    failed += 1

        return {"processed": processed, "failed": failed}

    def search_similar(
        self,
        query_text: str,
        ticker: str | None = None,
        limit: int = 5
    ) -> list[dict]:
        # Generate embedding for query
        query_embedding = self.generate_embedding(query_text)
        if not query_embedding:
            return []

        # Perform vector search
        return self.snowflake.vector_search(
            query_embedding=query_embedding,
            ticker=ticker,
            limit=limit
        )


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
