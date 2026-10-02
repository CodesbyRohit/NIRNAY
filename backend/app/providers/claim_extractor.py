from typing import Protocol

from app.schemas.analysis import ClaimDraft


class ClaimExtractor(Protocol):
    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        """Extract only atomic claims from already-normalized, redacted text."""
