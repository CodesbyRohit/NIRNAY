from uuid import UUID, uuid4

from app.providers.assessment import ClaimAssessmentProvider
from app.providers.evidence_search import EvidenceSearchProvider
from app.providers.hosted_llm import ClaimExtractor
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AssessedClaimResult,
    ClaimEvidence,
    CompleteAnalysisResponse,
    EvidenceOrigin,
    EvidenceRequest,
)
from app.services.analysis import AnalysisService
from app.services.assessment import AssessmentService
from app.services.evidence import EvidenceService
from app.services.manipulation import detect_manipulation_signals


class CompleteAnalysisService:
    def __init__(
        self,
        claim_extractor: ClaimExtractor,
        evidence_provider: EvidenceSearchProvider,
        assessment_provider: ClaimAssessmentProvider,
        evidence_origin: EvidenceOrigin,
    ) -> None:
        self._claim_service = AnalysisService(claim_extractor)
        self._evidence_service = EvidenceService(evidence_provider, evidence_origin)
        self._assessment_service = AssessmentService(assessment_provider)

    async def analyze(self, request: AnalysisRequest) -> CompleteAnalysisResponse:
        claim_response: AnalysisResponse = await self._claim_service.analyze(request.content)
        claims = claim_response.claims
        evidence_by_claim: dict[UUID, ClaimEvidence] = {}
        for index in range(0, len(claims), 10):
            evidence_response = await self._evidence_service.retrieve(
                EvidenceRequest(claims=claims[index : index + 10], consent=True)
            )
            evidence_by_claim.update(
                {item.claim_id: item for item in evidence_response.results}
            )

        results: list[AssessedClaimResult] = []
        for claim in claims:
            package: ClaimEvidence = evidence_by_claim[claim.id]
            assessment = await self._assessment_service.assess(claim, package.sources)
            manipulation_signals = detect_manipulation_signals(claim.text)
            results.append(
                AssessedClaimResult(
                    claim=claim,
                    assessment=assessment,
                    evidence=package.sources,
                    manipulation_signals=manipulation_signals,
                )
            )
        return CompleteAnalysisResponse(
            analysis_id=uuid4(),
            status="completed",
            manipulation_signals=detect_manipulation_signals(request.content),
            results=results,
        )
