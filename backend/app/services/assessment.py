import re
from uuid import UUID

from pydantic import ValidationError

from app.providers.assessment import ClaimAssessmentProvider
from app.schemas.analysis import (
    AssessmentState,
    Claim,
    ClaimAssessment,
    EvidenceStatus,
    RankedEvidenceSource,
)
from app.providers.hosted_assessor import InvalidAssessmentResponse

_UUID_REFERENCE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_UNSUPPORTED_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_NUMERIC_CONFIDENCE = re.compile(
    r"\bconfidence\b[^.\n]{0,30}\b\d+(?:\.\d+)?\s*%?|\b\d+(?:\.\d+)?\s*%\s*confidence\b",
    re.IGNORECASE,
)


class InvalidEvidenceReference(Exception):
    pass


class AssessmentService:
    def __init__(self, provider: ClaimAssessmentProvider) -> None:
        self._provider = provider

    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        if not evidence_package:
            return ClaimAssessment(
                assessment=AssessmentState.UNVERIFIED,
                rationale="No retrieved evidence was available for this claim.",
                evidence_ids=[],
                uncertainty="No relevant source material was found to assess the claim.",
            )

        try:
            assessment = ClaimAssessment.model_validate(
                await self._provider.assess(claim, evidence_package)
            )
        except ValidationError as error:
            raise InvalidAssessmentResponse(
                "The assessment provider returned malformed assessment data."
            ) from error
        supplied_ids = {source.evidence_id for source in evidence_package}
        referenced_ids = set(assessment.evidence_ids)
        if not referenced_ids.issubset(supplied_ids):
            raise InvalidEvidenceReference("Assessment referenced evidence not in the package.")
        narrative = f"{assessment.rationale}\n{assessment.uncertainty}"
        narrative_ids = {UUID(value) for value in _UUID_REFERENCE.findall(narrative)}
        if not narrative_ids.issubset(supplied_ids):
            raise InvalidEvidenceReference("Assessment narrative referenced evidence not in the package.")
        if _UNSUPPORTED_URL.search(narrative) or _NUMERIC_CONFIDENCE.search(narrative):
            raise InvalidAssessmentResponse(
                "Assessment narrative contains a URL or numeric confidence score."
            )

        if assessment.assessment in {
            AssessmentState.SUPPORTED,
            AssessmentState.CONTRADICTED,
        }:
            if not assessment.evidence_ids:
                raise InvalidAssessmentResponse(
                    "Supported and Contradicted assessments require evidence IDs."
                )
            cited_sources = [
                source for source in evidence_package if source.evidence_id in referenced_ids
            ]
            if not any(
                source.evidence.status == EvidenceStatus.RELEVANT
                and source.evidence.excerpt_source == "source_page_excerpt"
                and source.evidence.excerpt
                for source in cited_sources
            ):
                return ClaimAssessment(
                    assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
                    rationale=(
                        "The supplied material contains snippets or illustrative text, "
                        "not directly retrieved page evidence."
                    ),
                    evidence_ids=assessment.evidence_ids,
                    uncertainty=(
                        "Search snippets and demo fixtures cannot establish support or "
                        "contradiction without reviewing the source page."
                    ),
                )

        if assessment.assessment == AssessmentState.UNVERIFIED and not assessment.evidence_ids:
            return assessment

        if assessment.assessment == AssessmentState.NEEDS_MORE_EVIDENCE and not assessment.evidence_ids:
            return assessment

        return assessment
