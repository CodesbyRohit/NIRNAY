from typing import Protocol

from app.schemas.analysis import EvidenceSource


class EvidenceSearchProvider(Protocol):
    async def search(self, query: str) -> list[EvidenceSource]:
        """Return source metadata and provider-only page text for a claim query."""
