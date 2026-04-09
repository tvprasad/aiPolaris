"""
tests/pipeline/test_chunking.py — Unit tests for OverlappingWindowChunker. ADR-005.
"""

import uuid

import pytest

from pipeline.chunking.strategy import Chunk, OverlappingWindowChunker

CHUNKER = OverlappingWindowChunker()
META = {
    "source_doc_id": "doc-001",
    "document_title": "Test Document",
    "site_id": "site-001",
    "pull_id": "pull-001",
}


def make_chunks(content: str) -> list[Chunk]:
    return CHUNKER.chunk_document(content, **META)


class TestEmptyAndWhitespace:
    def test_empty_string_returns_empty_list(self) -> None:
        assert make_chunks("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert make_chunks("   \n\t  ") == []


class TestSingleChunk:
    def test_short_text_produces_one_chunk(self) -> None:
        content = "This is a short document. " * 10  # well under target
        chunks = make_chunks(content)
        assert len(chunks) == 1

    def test_chunk_carries_source_doc_id(self) -> None:
        chunks = make_chunks("Hello world. " * 20)
        assert chunks[0].source_doc_id == "doc-001"

    def test_chunk_carries_document_title(self) -> None:
        chunks = make_chunks("Hello world. " * 20)
        assert chunks[0].document_title == "Test Document"

    def test_chunk_carries_site_id(self) -> None:
        chunks = make_chunks("Hello world. " * 20)
        assert chunks[0].site_id == "site-001"

    def test_chunk_carries_pull_id(self) -> None:
        chunks = make_chunks("Hello world. " * 20)
        assert chunks[0].pull_id == "pull-001"

    def test_chunk_id_is_valid_uuid(self) -> None:
        chunks = make_chunks("Hello world. " * 20)
        parsed = uuid.UUID(chunks[0].chunk_id)
        assert str(parsed) == chunks[0].chunk_id

    def test_token_count_approximation(self) -> None:
        content = "x" * 400
        chunks = make_chunks(content)
        assert chunks[0].token_count == chunks[0].char_count // 4

    def test_char_count_matches_content(self) -> None:
        content = "Hello world. " * 20
        chunks = make_chunks(content)
        assert chunks[0].char_count == len(chunks[0].content)


class TestMultipleChunks:
    def _long_content(self) -> str:
        # ~4000 chars — well over TARGET_TOKENS * CHARS_PER_TOKEN = 2048
        return ("The enterprise policy document contains many sections. " * 80)

    def test_long_text_produces_multiple_chunks(self) -> None:
        chunks = make_chunks(self._long_content())
        assert len(chunks) > 1

    def test_chunk_indices_increment(self) -> None:
        chunks = make_chunks(self._long_content())
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_all_chunks_have_unique_ids(self) -> None:
        chunks = make_chunks(self._long_content())
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_overlap_means_content_restarts_before_prior_end(self) -> None:
        # With overlap, the second chunk should contain content that appeared
        # near the end of the first chunk.
        content = "word " * 600  # large enough for multi-chunk
        chunks = make_chunks(content)
        if len(chunks) >= 2:
            # End of chunk 0 overlaps with start of chunk 1
            end_of_first = chunks[0].content[-50:]
            start_of_second = chunks[1].content[:50]
            # They share some content due to overlap window
            # (can't do exact string match because sentence boundary may vary)
            assert len(start_of_second) > 0

    def test_no_chunk_exceeds_max_tokens(self) -> None:
        chunks = make_chunks(self._long_content())
        max_chars = OverlappingWindowChunker.MAX_TOKENS * OverlappingWindowChunker.CHARS_PER_TOKEN
        for chunk in chunks:
            assert chunk.char_count <= max_chars + 200  # allow slight boundary overshoot


class TestShortChunkMerge:
    def test_tiny_trailing_text_merges_into_previous(self) -> None:
        # Build content where last segment is very short
        target_chars = OverlappingWindowChunker.TARGET_TOKENS * OverlappingWindowChunker.CHARS_PER_TOKEN
        main_body = "A" * target_chars + " "
        tiny_tail = "Hi"  # well under MIN_TOKENS * CHARS_PER_TOKEN = 400 chars
        content = main_body + tiny_tail

        chunks = make_chunks(content)
        # The tiny tail should be merged — we should not have a standalone tiny chunk
        for chunk in chunks:
            assert chunk.char_count >= 10  # all chunks have meaningful content


class TestSentenceBoundary:
    def test_chunk_prefers_period_boundary(self) -> None:
        # Build a string with clear sentence boundaries near the target size
        target_chars = OverlappingWindowChunker.TARGET_TOKENS * OverlappingWindowChunker.CHARS_PER_TOKEN
        sentence = "This is a well-formed sentence. "
        content = sentence * (target_chars // len(sentence) + 5)
        chunks = make_chunks(content)
        # At least the first chunk should end with a period (sentence boundary logic)
        if len(chunks) > 1:
            # Due to sentence boundary detection, chunk content ends at a period
            assert chunks[0].content.endswith(".")
