"""
pipeline/chunking/strategy.py — Overlapping window chunking. ADR-005.

512 tokens per chunk, 10% overlap (~51 tokens).
Every chunk carries full metadata for citation panel.

Context engineering starts at ingest — chunk boundaries determine
what the model can reason about. ADR-005 was written after diagnosing
Meridian's 59% refusal rate on technical queries back to coarse chunking.
"""

import hashlib
import uuid
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    content: str
    chunk_index: int
    source_doc_id: str
    document_title: str
    site_id: str
    pull_id: str
    token_count: int
    char_count: int


class OverlappingWindowChunker:
    """
    Overlapping window chunker. ADR-005.

    Constraints:
    - Target: 512 tokens per chunk
    - Overlap: 10% (~51 tokens)
    - Minimum chunk length: 100 tokens
    - Maximum chunk length: 600 tokens
    - Chunks shorter than min are merged with the previous chunk
    """

    TARGET_TOKENS = 512
    OVERLAP_RATIO = 0.10
    MIN_TOKENS = 100
    MAX_TOKENS = 600

    # Rough chars-per-token approximation (English text)
    CHARS_PER_TOKEN = 4

    def chunk_document(
        self,
        content: str,
        source_doc_id: str,
        document_title: str,
        site_id: str,
        pull_id: str,
    ) -> list[Chunk]:
        """
        Chunk a document into overlapping windows.
        Returns list of Chunk objects with full metadata.

        Use Tip 9 inspection after running:
          "What is the average chunk length across all indexed documents?"
          "Are there any chunks shorter than 100 tokens?"
        """
        if not content or not content.strip():
            return []

        target_chars   = self.TARGET_TOKENS   * self.CHARS_PER_TOKEN
        overlap_chars  = int(target_chars * self.OVERLAP_RATIO)
        min_chars      = self.MIN_TOKENS      * self.CHARS_PER_TOKEN
        max_chars      = self.MAX_TOKENS      * self.CHARS_PER_TOKEN

        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(content):
            end = min(start + target_chars, len(content))

            # Extend to sentence boundary if possible
            if end < len(content):
                boundary = content.rfind(". ", start, end)
                if boundary > start + min_chars:
                    end = boundary + 1

            chunk_text = content[start:end].strip()

            if len(chunk_text) < min_chars and chunks:
                # Too short — merge into previous chunk
                prev = chunks[-1]
                merged_content = prev.content + " " + chunk_text
                chunks[-1] = Chunk(
                    chunk_id=prev.chunk_id,
                    content=merged_content,
                    chunk_index=prev.chunk_index,
                    source_doc_id=source_doc_id,
                    document_title=document_title,
                    site_id=site_id,
                    pull_id=pull_id,
                    token_count=len(merged_content) // self.CHARS_PER_TOKEN,
                    char_count=len(merged_content),
                )
            elif chunk_text:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_text,
                    chunk_index=index,
                    source_doc_id=source_doc_id,
                    document_title=document_title,
                    site_id=site_id,
                    pull_id=pull_id,
                    token_count=len(chunk_text) // self.CHARS_PER_TOKEN,
                    char_count=len(chunk_text),
                ))
                index += 1

            # Advance with overlap — stop if we've processed to end of document
            if end >= len(content):
                break
            start = end - overlap_chars

        return chunks
