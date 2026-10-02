from typing import Protocol

from app.schemas.analysis import Claim, ClaimAssessment, RankedEvidenceSource


class ClaimAssessmentProvider(Protocol):
    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        """Assess the claim using only its supplied, ranked evidence package."""
