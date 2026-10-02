import os

from fastapi import APIRouter, Depends, HTTPException, status

from app.providers.errors import ProviderConfigurationError, ProviderError
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider
from app.providers.tavily_search import InvalidSearchResponse, TavilyEvidenceSearch
from app.schemas.analysis import EvidenceOrigin, EvidenceRequest, EvidenceResponse
from app.services.evidence import EvidenceService

router = APIRouter(prefix="/api/v1")


def get_evidence_service() -> EvidenceService:
    provider_name = os.getenv("EVIDENCE_PROVIDER", "tavily").strip().lower()
    if provider_name == "fixture":
        return EvidenceService(
            DemoFixtureEvidenceProvider(),
            EvidenceOrigin.DEMO_FIXTURE,
        )
    if provider_name == "tavily":
        return EvidenceService(TavilyEvidenceSearch(), EvidenceOrigin.LIVE_SEARCH)
    raise ProviderConfigurationError("EVIDENCE_PROVIDER must be 'tavily' or 'fixture'.")


@router.post("/evidence", response_model=EvidenceResponse)
async def retrieve_evidence(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceResponse:
    if not request.consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit consent is required before sending claims to web search.",
        )

    try:
        return await service.retrieve(request)
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence search is not configured with a supported provider.",
        ) from error
    except InvalidSearchResponse as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The evidence search provider returned unusable results.",
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The evidence search provider is unavailable.",
        ) from error
