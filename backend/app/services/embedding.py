"""
Embedding service with text preprocessing pipeline for document chunking and normalization.

This service handles the complete pipeline from raw text to optimized embeddings,
including intelligent chunking, deduplication, and batch processing.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logger import get_logger, LoggerMixin
from app.core.config import settings
from app.schemas.vector import DocumentType

logger = get_logger(__name__)


class ChunkingStrategy(str, Enum):
    """Strategies for text chunking"""
    PARAGRAPH = "paragraph"      # Split by paragraphs
    SENTENCE = "sentence"        # Split by sentences
    FIXED_SIZE = "fixed_size"    # Fixed size chunks with overlap
    SEMANTIC = "semantic"        # Semantic boundary detection (future)


class TextNormalization(str, Enum):
    """Text normalization levels"""
    MINIMAL = "minimal"          # Basic cleaning only
    STANDARD = "standard"        # Standard normalization
    AGGRESSIVE = "aggressive"    # Aggressive normalization for embeddings


@dataclass
class TextChunk:
    """A chunk of text with metadata"""
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
    hash: str
    confidence_score: float = 1.0


@dataclass
class EmbeddingResult:
    """Result of embedding computation"""
    chunks: List[TextChunk]
    embeddings: List[List[float]]
    model_used: str
    processing_time_ms: float
    total_tokens: int
    deduplication_stats: Dict[str, int]


class EmbeddingService(LoggerMixin):
    """
    Service for computing document embeddings with preprocessing pipeline.
    """

    def __init__(self):
        super().__init__()
        self.embedding_model = settings.EMBEDDING_MODEL
        self.max_chunk_size = settings.EMBEDDING_MAX_CHUNK_SIZE
        self.chunk_overlap = settings.EMBEDDING_CHUNK_OVERLAP
        self.batch_size = settings.EMBEDDING_BATCH_SIZE

        # Initialize embedding client
        self._embedding_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the embedding API client"""
        try:
            # Import here to avoid circular dependencies
            from openai import AsyncOpenAI

            self._embedding_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )

            logger.info("Embedding client initialized", model=self.embedding_model)

        except Exception as e:
            logger.error("Failed to initialize embedding client", error=str(e))
            raise

    async def process_document(
        self,
        text: str,
        doc_type: DocumentType = DocumentType.KNOWLEDGE,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH,
        normalization: TextNormalization = TextNormalization.STANDARD,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingResult:
        """
        Process a complete document through the embedding pipeline.

        Args:
            text: Raw document text
            doc_type: Type of document
            chunking_strategy: Strategy for chunking the text
            normalization: Level of text normalization
            metadata: Additional document metadata

        Returns:
            Complete embedding result
        """
        start_time = asyncio.get_event_loop().time()

        # Bind correlation/request and tenancy context for structured logs
        _log_meta = metadata or {}
        log = self.logger.bind(
            correlation_id=_log_meta.get("correlation_id"),
            tenant_id=_log_meta.get("tenant_id"),
            project_id=_log_meta.get("project_id"),
            doc_type=str(doc_type.value) if hasattr(doc_type, "value") else str(doc_type),
        )

        try:
            # Step 1: Normalize text
            normalized_text = self._normalize_text(text, normalization)

            # Step 2: Chunk text
            chunks = self._chunk_text(
                normalized_text,
                chunking_strategy,
                metadata or {}
            )

            # Step 3: Deduplicate chunks
            unique_chunks, dedup_stats = self._deduplicate_chunks(chunks)

            # Step 4: Compute embeddings
            embeddings = await self._compute_embeddings(unique_chunks)

            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            # Calculate total tokens
            total_tokens = sum(len(chunk.text.split()) for chunk in unique_chunks)

            result = EmbeddingResult(
                chunks=unique_chunks,
                embeddings=embeddings,
                model_used=self.embedding_model,
                processing_time_ms=processing_time,
                total_tokens=total_tokens,
                deduplication_stats=dedup_stats
            )

            log.info(
                "Document processed successfully",
                doc_type=doc_type,
                chunks_count=len(unique_chunks),
                processing_time_ms=processing_time,
                total_tokens=total_tokens
            )

            return result

        except Exception as e:
            log.exception("Document processing failed", error=str(e))
            raise

    def _normalize_text(self, text: str, normalization: TextNormalization) -> str:
        """
        Normalize text according to specified level.

        Args:
            text: Input text
            normalization: Normalization level

        Returns:
            Normalized text
        """
        if normalization == TextNormalization.MINIMAL:
            return self._minimal_normalization(text)
        elif normalization == TextNormalization.STANDARD:
            return self._standard_normalization(text)
        elif normalization == TextNormalization.AGGRESSIVE:
            return self._aggressive_normalization(text)
        else:
            return text

    def _minimal_normalization(self, text: str) -> str:
        """Basic text cleaning"""
        # Normalize line endings first
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Collapse spaces/tabs but preserve newlines
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Normalize multiple blank lines to a single blank line
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Trim outer whitespace
        text = text.strip()
        return text

    def _standard_normalization(self, text: str) -> str:
        """Standard text normalization for embeddings"""
        # Apply minimal normalization first
        text = self._minimal_normalization(text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Normalize common Unicode characters
        text = text.replace('–', '-').replace('—', '--')
        text = text.replace('…', '...')

        # Remove special characters that might interfere with embeddings
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\{\}\"\'\/\@\#\$\%\^\&\*\+\=\~\`]', ' ', text)

        # Clean up again after character replacement
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _aggressive_normalization(self, text: str) -> str:
        """Aggressive normalization for optimal embedding quality"""
        # Apply standard normalization first
        text = self._standard_normalization(text)

        # Convert to lowercase (optional - depends on use case)
        # text = text.lower()

        # Normalize numbers (replace with special token)
        text = re.sub(r'\b\d+\b', '<NUM>', text)

        # Normalize email addresses and URLs
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', text)
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '<URL>', text)

        # Remove remaining special characters except basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?]', ' ', text)

        # Final cleanup
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _chunk_text(
        self,
        text: str,
        strategy: ChunkingStrategy,
        metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """
        Chunk text according to specified strategy.

        Args:
            text: Input text
            strategy: Chunking strategy
            metadata: Base metadata

        Returns:
            List of text chunks
        """
        if strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraphs(text, metadata)
        elif strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentences(text, metadata)
        elif strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_by_fixed_size(text, metadata)
        else:
            # Default to paragraph chunking
            return self._chunk_by_paragraphs(text, metadata)

    def _chunk_by_paragraphs(self, text: str, metadata: Dict[str, Any]) -> List[TextChunk]:
        """Chunk text by paragraphs"""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_pos = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Skip very short paragraphs (likely formatting artifacts)
            if len(paragraph) < 10:
                continue

            # Calculate position
            start_pos = text.find(paragraph, current_pos)
            end_pos = start_pos + len(paragraph)

            chunk_metadata = {
                **metadata,
                "chunk_type": "paragraph",
                "paragraph_index": i
            }

            chunk = TextChunk(
                text=paragraph,
                chunk_index=i,
                start_char=start_pos,
                end_char=end_pos,
                metadata=chunk_metadata,
                hash=self._compute_hash(paragraph)
            )

            chunks.append(chunk)
            current_pos = end_pos

        return chunks

    def _chunk_by_sentences(self, text: str, metadata: Dict[str, Any]) -> List[TextChunk]:
        """Chunk text by sentences"""
        # Simple sentence splitting (in production, use NLP library)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_pos = 0
        sentence_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            start_pos = text.find(sentence, current_pos)
            end_pos = start_pos + len(sentence)

            chunk_metadata = {
                **metadata,
                "chunk_type": "sentence",
                "sentence_index": sentence_index
            }

            chunk = TextChunk(
                text=sentence,
                chunk_index=sentence_index,
                start_char=start_pos,
                end_char=end_pos,
                metadata=chunk_metadata,
                hash=self._compute_hash(sentence)
            )

            chunks.append(chunk)
            current_pos = end_pos
            sentence_index += 1

        return chunks

    def _chunk_by_fixed_size(self, text: str, metadata: Dict[str, Any]) -> List[TextChunk]:
        """Chunk text by fixed size with overlap"""
        chunks = []
        text_length = len(text)
        chunk_size = self.max_chunk_size
        overlap = self.chunk_overlap

        if overlap >= chunk_size:
            # Avoid non-progress / infinite loop due to misconfiguration
            self.logger.warning(
                "Adjusting chunk_overlap to avoid infinite loop",
                chunk_overlap=overlap,
                chunk_size=chunk_size,
            )
            overlap = max(0, chunk_size // 4)

        start_pos = 0
        chunk_index = 0

        while start_pos < text_length:
            end_pos = min(start_pos + chunk_size, text_length)

            # Try to end at word boundary
            if end_pos < text_length:
                last_space = text.rfind(' ', start_pos, end_pos)
                if last_space > start_pos + chunk_size // 2:
                    end_pos = last_space

            chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:
                chunk_metadata = {
                    **metadata,
                    "chunk_type": "fixed_size",
                    "chunk_size": len(chunk_text)
                }

                chunk = TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata=chunk_metadata,
                    hash=self._compute_hash(chunk_text)
                )

                chunks.append(chunk)
                chunk_index += 1

            # Advance start based on actual chunk length to guarantee progress
            produced_len = max(1, end_pos - start_pos)
            next_start = (end_pos - overlap) if overlap < produced_len else (start_pos + 1)
            if next_start <= start_pos:
                next_start = min(end_pos, text_length)
            start_pos = next_start

        return chunks

    def _deduplicate_chunks(self, chunks: List[TextChunk]) -> Tuple[List[TextChunk], Dict[str, int]]:
        """
        Remove duplicate chunks based on content hash.

        Args:
            chunks: List of text chunks

        Returns:
            Tuple of (unique_chunks, deduplication_stats)
        """
        seen_hashes = set()
        unique_chunks = []
        duplicates_count = 0
        near_duplicates = 0

        for chunk in chunks:
            chunk_hash = chunk.hash

            if chunk_hash in seen_hashes:
                duplicates_count += 1
                continue

            # Check for near-duplicates (similar but not identical)
            is_near_duplicate = False
            for existing_hash in seen_hashes:
                if self._are_hashes_similar(chunk_hash, existing_hash):
                    near_duplicates += 1
                    is_near_duplicate = True
                    break

            if not is_near_duplicate:
                unique_chunks.append(chunk)
                seen_hashes.add(chunk_hash)

        stats = {
            "original_chunks": len(chunks),
            "unique_chunks": len(unique_chunks),
            "exact_duplicates": duplicates_count,
            "near_duplicates": near_duplicates
        }

        return unique_chunks, stats

    def _are_hashes_similar(self, hash1: str, hash2: str, threshold: float = 0.9) -> bool:
        """
        Check if two hashes are similar (for near-duplicate detection).

        Args:
            hash1: First hash
            hash2: Second hash
            threshold: Similarity threshold

        Returns:
            True if hashes are similar
        """
        # Simple hash similarity check
        # In production, could use more sophisticated similarity measures
        return hash1[:6] == hash2[:6]  # First 6 characters match

    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _compute_embeddings(self, chunks: List[TextChunk]) -> List[List[float]]:
        """
        Compute embeddings for text chunks with batching and retry logic.

        Args:
            chunks: List of text chunks

        Returns:
            List of embedding vectors
        """
        if not chunks:
            return []

        all_embeddings = []

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch_chunks = chunks[i:i + self.batch_size]
            batch_texts = [chunk.text for chunk in batch_chunks]

            try:
                # Compute embeddings for batch (with timeout)
                client = self._embedding_client
                # Prefer per-call timeout if supported; otherwise configure via client options
                response = await client.with_options(
                    timeout=getattr(settings, "EMBEDDING_REQUEST_TIMEOUT", None),
                ).embeddings.create(
                    model=self.embedding_model,
                    input=batch_texts,
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.debug(
                    "Batch embeddings computed",
                    batch_index=i // self.batch_size,
                    batch_size=len(batch_chunks),
                    embedding_dim=len(batch_embeddings[0]) if batch_embeddings else 0
                )

            except Exception as e:
                self.logger.exception("Batch embedding computation failed", error=str(e))
                raise

        # Sanity check: provider must return one vector per input
        if len(all_embeddings) != len(chunks):
            self.logger.error(
                "Embedding count mismatch",
                expected=len(chunks),
                actual=len(all_embeddings),
            )
            raise RuntimeError("Embedding count mismatch")
        return all_embeddings

    async def process_streaming(
        self,
        text_stream: AsyncGenerator[str, None],
        doc_type: DocumentType = DocumentType.KNOWLEDGE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[EmbeddingResult, None]:
        """
        Process text as a streaming input.

        Args:
            text_stream: Async generator of text chunks
            doc_type: Type of document
            metadata: Additional metadata

        Yields:
            Embedding results for each processed batch
        """
        buffer = ""
        async for text_chunk in text_stream:
            buffer += text_chunk

            # Process when we have enough content or end of stream
            if len(buffer) >= self.max_chunk_size * 2:
                result = await self.process_document(
                    buffer,
                    doc_type=doc_type,
                    metadata=metadata
                )
                yield result
                buffer = ""

        # Process remaining content
        if buffer.strip():
            result = await self.process_document(
                buffer,
                doc_type=doc_type,
                metadata=metadata
            )
            yield result


    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Simple interface to embed a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Create dummy chunks for the existing interface
        chunks = []
        for i, text in enumerate(texts):
            chunk = TextChunk(
                text=text,
                chunk_index=i,
                start_char=0,
                end_char=len(text),
                metadata={},
                hash=self._compute_hash(text)
            )
            chunks.append(chunk)

        return await self._compute_embeddings(chunks)


# Singleton instance for application-wide use
embedding_service = EmbeddingService()