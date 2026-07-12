import logging
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from src.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingDimensionError(Exception):
    """Raised when a model produces a vector of unexpected size."""
    pass


class EmbeddingGenerationError(Exception):
    """Raised when embedding fails after all retries are exhausted."""
    pass


class EmbeddingService:
    """
    Turns chunk text into vectors using a self-hosted embedding model.
    Wraps calls with retry logic — if generation fails repeatedly,
    raises a clear error so the ingestion pipeline can mark that
    document as 'failed' and retry later, rather than silently
    inserting wrong/missing vectors.
    """

    def __init__(self, model_name: str | None = None, expected_dim: int | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.expected_dim = expected_dim or settings.EMBEDDING_DIM

        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

      
        actual_dim = self.model.get_sentence_embedding_dimension()
        if actual_dim != self.expected_dim:
            raise EmbeddingDimensionError(
                f"Model '{self.model_name}' outputs {actual_dim}-dim vectors, "
                f"but settings.embedding_dim is {self.expected_dim}. "
                f"Update your .env, SQL column, and schemas to match."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((RuntimeError, OSError)),
        reraise=True,
    ) 
    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,  # important for cosine similarity search
        )
        return embeddings.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            vectors = self._encode_batch(texts)
        except Exception as e:
            logger.error(f"Embedding generation failed after retries: {e}")
            raise EmbeddingGenerationError(
                f"Could not generate embeddings for {len(texts)} texts"
            ) from e

        # validate every vector actually came out the right size
      
        for i, vec in enumerate(vectors):
            if len(vec) != self.expected_dim:
                raise EmbeddingDimensionError(
                    f"Vector at index {i} has {len(vec)} dims, expected {self.expected_dim}"
                )

        return vectors

    def embed_single(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]