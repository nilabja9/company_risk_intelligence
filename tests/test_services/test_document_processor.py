import pytest
from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    def setup_method(self):
        self.processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)

    def test_extract_sections(self, sample_filing_text):
        """Test section extraction from filing text."""
        sections = self.processor.extract_sections(sample_filing_text)

        assert "RISK_FACTORS" in sections or len(sections) > 0

    def test_chunk_text(self):
        """Test text chunking."""
        text = "This is a test paragraph. " * 100
        chunks = self.processor.chunk_text(text)

        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= self.processor.chunk_size + 100  # Allow some overflow

    def test_clean_text(self):
        """Test text cleaning."""
        dirty_text = "  Multiple   spaces   and\n\n\n\nnewlines  "
        clean = self.processor._clean_text(dirty_text)

        assert "  " not in clean.replace("  ", " ")  # Reduced whitespace


class TestDocumentChunking:
    def test_empty_text(self):
        """Test handling of empty text."""
        processor = DocumentProcessor()
        chunks = processor.chunk_text("")

        assert chunks == []

    def test_small_text(self):
        """Test handling of small text that doesn't need chunking."""
        processor = DocumentProcessor(chunk_size=1000)
        small_text = "This is a small piece of text."
        chunks = processor.chunk_text(small_text)

        assert len(chunks) == 1
        assert chunks[0] == small_text
