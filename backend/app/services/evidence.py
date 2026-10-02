from app.providers.evidence_search import EvidenceSearchProvider
from app.schemas.analysis import (
    ClaimEvidence,
    EvidenceOrigin,
    EvidenceRequest,
    EvidenceResponse,
)
from app.services.source_ranking import rank_sources


class EvidenceService:
    def __init__(
        self,
        search_provider: EvidenceSearchProvider,
        origin: EvidenceOrigin = EvidenceOrigin.LIVE_SEARCH,
    ) -> None:
        self._search_provider = search_provider
        self._origin = origin

    async def retrieve(self, request: EvidenceRequest) -> EvidenceResponse:
        results: list[ClaimEvidence] = []
        for claim in request.claims:
            sources = await self._search_provider.search(claim.text)
            results.append(
                ClaimEvidence(
                    claim_id=claim.id,
                    sources=rank_sources(sources, claim.text, self._origin),
                )
            )
        return EvidenceResponse(results=results)
