import re
import uuid
from dataclasses import dataclass
from typing import Iterator

from app.services.snowflake_client import get_snowflake_client


@dataclass
class DocumentChunk:
    chunk_id: str
    cik: str
    company_ticker: str
    company_name: str
    filing_type: str
    adsh: str
    period_end_date: str
    section_name: str
    chunk_text: str
    chunk_index: int
    metadata: dict | None = None


class DocumentProcessor:
    # SEC filing section patterns
    SECTION_PATTERNS = {
        "RISK_FACTORS": r"(?i)(item\s*1a\.?\s*risk\s*factors)",
        "MD&A": r"(?i)(item\s*7\.?\s*management['']?s?\s*discussion)",
        "BUSINESS": r"(?i)(item\s*1\.?\s*business)",
        "FINANCIAL_STATEMENTS": r"(?i)(item\s*8\.?\s*financial\s*statements)",
        "LEGAL_PROCEEDINGS": r"(?i)(item\s*3\.?\s*legal\s*proceedings)",
        "CONTROLS": r"(?i)(item\s*9a\.?\s*controls)",
    }

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.snowflake = get_snowflake_client()

    def extract_sections(self, filing_text: str) -> dict[str, str]:
        sections = {}

        # Find all section positions
        section_positions = []
        for section_name, pattern in self.SECTION_PATTERNS.items():
            matches = list(re.finditer(pattern, filing_text))
            for match in matches:
                section_positions.append((match.start(), section_name))

        # Sort by position
        section_positions.sort(key=lambda x: x[0])

        # Extract text between sections
        for i, (start_pos, section_name) in enumerate(section_positions):
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]
            else:
                end_pos = len(filing_text)

            section_text = filing_text[start_pos:end_pos].strip()

            # Only keep if there's meaningful content
            if len(section_text) > 100:
                sections[section_name] = section_text

        return sections

    def chunk_text(self, text: str) -> list[str]:
        chunks = []

        # Clean the text
        text = self._clean_text(text)

        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, save current and start new
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If single paragraph is too long, split by sentences
                if len(para) > self.chunk_size:
                    sentence_chunks = self._split_by_sentences(para)
                    chunks.extend(sentence_chunks[:-1])
                    current_chunk = sentence_chunks[-1] if sentence_chunks else ""
                else:
                    # Start new chunk with overlap from previous
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = overlap_text + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _clean_text(self, text: str) -> str:
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove HTML tags if any remain
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _split_by_sentences(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap(self, text: str) -> str:
        if len(text) <= self.chunk_overlap:
            return text + " "
        return text[-self.chunk_overlap:] + " "

    def process_filing(
        self,
        sec_document_id: str,
        cik: str,
        adsh: str,
        company_ticker: str,
        company_name: str,
        filing_type: str,
        period_end_date: str,
        filing_text: str
    ) -> Iterator[DocumentChunk]:
        """
        Process a SEC filing into chunks.

        Args:
            sec_document_id: Cybersyn's unique document ID
            cik: SEC Central Index Key
            adsh: SEC Accession Number
            company_ticker: Stock ticker
            company_name: Company name
            filing_type: Document type (10-K, 10-Q, 8-K)
            period_end_date: Filing period end date
            filing_text: Full text of the filing
        """
        # Extract sections from filing
        sections = self.extract_sections(filing_text)

        chunk_index = 0
        for section_name, section_text in sections.items():
            # Chunk each section
            text_chunks = self.chunk_text(section_text)

            for chunk_text in text_chunks:
                yield DocumentChunk(
                    chunk_id=f"{sec_document_id}_{section_name}_{chunk_index}",
                    cik=cik,
                    company_ticker=company_ticker,
                    company_name=company_name,
                    filing_type=filing_type,
                    adsh=adsh,
                    period_end_date=period_end_date,
                    section_name=section_name,
                    chunk_text=chunk_text,
                    chunk_index=chunk_index,
                    metadata={
                        "sec_document_id": sec_document_id,
                        "char_count": len(chunk_text),
                    }
                )
                chunk_index += 1

    def process_and_store_filing(
        self,
        sec_document_id: str,
        cik: str,
        adsh: str,
        company_ticker: str,
        company_name: str,
        filing_type: str,
        period_end_date: str,
        filing_text: str
    ) -> int:
        """Process a filing and store chunks in Snowflake."""
        chunks_stored = 0
        for chunk in self.process_filing(
            sec_document_id=sec_document_id,
            cik=cik,
            adsh=adsh,
            company_ticker=company_ticker,
            company_name=company_name,
            filing_type=filing_type,
            period_end_date=period_end_date,
            filing_text=filing_text
        ):
            self.snowflake.insert_document_chunk(
                chunk_id=chunk.chunk_id,
                cik=chunk.cik,
                company_ticker=chunk.company_ticker,
                company_name=chunk.company_name,
                filing_type=chunk.filing_type,
                adsh=chunk.adsh,
                period_end_date=chunk.period_end_date,
                section_name=chunk.section_name,
                chunk_text=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata
            )
            chunks_stored += 1

        return chunks_stored


def get_document_processor() -> DocumentProcessor:
    return DocumentProcessor()
