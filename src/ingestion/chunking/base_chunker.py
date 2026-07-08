from abc import ABC, abstractmethod
from uuid import UUID
from src.schemas.chunk_schema import ChunkCreate


class BaseChunker(ABC):
    """
    Abstract contract that every chunking strategy must follow.
    This class cannot be instantiated directly — it only exists to
    
    """

    @abstractmethod
    def chunk(
        self,
        text: str,
        document_id: UUID,
        tenant_id: UUID,
    ) -> list[ChunkCreate]:
        """
        Split `text` into a list of validated ChunkCreate objects.
        Every subclass MUST implement this method, or Python will
        refuse to let you create an instance of it.
        """
        raise NotImplementedError