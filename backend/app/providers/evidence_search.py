from typing import Protocol

from app.schemas.analysis import EvidenceSource


class EvidenceSearchProvider(Protocol):
    async def search(self, query: str) -> list[EvidenceSource]:
        """Return web source snippets for a claim query without assessing it."""
