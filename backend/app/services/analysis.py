from uuid import uuid4

from app.providers.claim_extractor import ClaimExtractor
from app.schemas.analysis import AnalysisResponse, Claim
from app.services.normalization import normalize_and_redact


class AnalysisService:
    def __init__(self, claim_extractor: ClaimExtractor) -> None:
        self._claim_extractor = claim_extractor

    async def analyze(self, content: str) -> AnalysisResponse:
        normalized_text = normalize_and_redact(content)
        if not normalized_text:
            raise ValueError("Content must contain non-whitespace text.")

        claim_drafts = await self._claim_extractor.extract_claims(normalized_text)
        claims = [
            Claim(id=uuid4(), text=draft.text, kind=draft.kind)
            for draft in claim_drafts
        ]
        return AnalysisResponse(
            analysis_id=uuid4(),
            status="completed",
            claims=claims,
        )
