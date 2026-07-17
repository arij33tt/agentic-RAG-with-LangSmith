import logging
from src.ingestion.embedder import EmbeddingService

logger = logging.getLogger(__name__)


class QueryTransformer:
    """
    Improves a raw user query before it hits retrieval, via:
    - rewrite_with_history: resolve vague follow-ups using chat context
    - expand_multi_query: generate paraphrases to widen recall
    - hyde: embed a hypothetical answer instead of the raw question
    """

    def __init__(self, llm_client, embedding_service: EmbeddingService):
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    def rewrite_with_history(self, question: str, chat_history: list[dict]) -> str:
        """
        chat_history: list of {"role": "user"/"assistant", "content": str},
        most recent last. Returns a standalone version of `question`.
        """
        if not chat_history:
            return question  # nothing to resolve against, return as-is

        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in chat_history[-6:])
        prompt = (
            "Given this conversation history and a follow-up question, "
            "rewrite the follow-up as a standalone question that makes "
            "sense with NO prior context. If it's already standalone, "
            "return it unchanged. Output ONLY the rewritten question.\n\n"
            f"History:\n{history_text}\n\n"
            f"Follow-up question: {question}\n\n"
            "Standalone question:"
        )
        try:
            rewritten = self.llm_client.generate(prompt).strip()
            return rewritten if rewritten else question
        except Exception as e:
            logger.warning(f"Query rewrite failed, using original question: {e}")
            return question

    def expand_multi_query(self, question: str, n: int = 3) -> list[str]:
        """Returns n paraphrases of `question` (does NOT include the original — caller merges)."""
        prompt = (
            f"Generate {n} different phrasings of this question, each capturing "
            "the same underlying intent but using different words or angles. "
            "Output ONLY the paraphrases, one per line, no numbering.\n\n"
            f"Question: {question}"
        )
        try:
            response = self.llm_client.generate(prompt).strip()
            paraphrases = [line.strip() for line in response.split("\n") if line.strip()]
            return paraphrases[:n]
        except Exception as e:
            logger.warning(f"Multi-query expansion failed, using original question only: {e}")
            return []

    def hyde(self, question: str) -> list[float]:
        """
        Generates a hypothetical answer and embeds THAT instead of the
        raw question. Returns the embedding vector, ready to pass to
        vector_store.similarity_search() or hybrid_search().
        """
        prompt = (
            "Write a short, plausible-sounding paragraph that would answer "
            "the following question, as if it came from a real document. "
            "It doesn't need to be factually correct — it just needs to "
            "read like real content on this topic.\n\n"
            f"Question: {question}\n\nHypothetical answer:"
        )
        try:
            hypothetical_doc = self.llm_client.generate(prompt).strip()
            if not hypothetical_doc:
                raise ValueError("LLM returned empty hypothetical document")
            return self.embedding_service.embed_single(hypothetical_doc)
        except Exception as e:
            logger.warning(f"HyDE generation failed, falling back to embedding raw question: {e}")
            return self.embedding_service.embed_single(question)