import os

from fastapi import APIRouter, Depends, HTTPException, status

from app.providers.hosted_llm import (
    HostedLLMClaimExtractor,
    InvalidProviderResponse,
)
from app.providers.tavily_search import InvalidSearchResponse
from app.providers.errors import ProviderConfigurationError, ProviderError
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider
from app.providers.hosted_assessor import HostedLLMAssessor, InvalidAssessmentResponse
from app.providers.tavily_search import TavilyEvidenceSearch
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    CompleteAnalysisResponse,
    EvidenceOrigin,
)
from app.services.analysis import AnalysisService
from app.services.assessment import InvalidEvidenceReference
from app.services.complete_analysis import CompleteAnalysisService

router = APIRouter(prefix="/api/v1")


def get_analysis_service() -> AnalysisService:
    return AnalysisService(HostedLLMClaimExtractor())


def get_complete_analysis_service() -> CompleteAnalysisService:
    provider_name = os.getenv("EVIDENCE_PROVIDER", "tavily").strip().lower()
    if provider_name == "fixture":
        evidence_provider = DemoFixtureEvidenceProvider()
        evidence_origin = EvidenceOrigin.DEMO_FIXTURE
    elif provider_name == "tavily":
        evidence_provider = TavilyEvidenceSearch()
        evidence_origin = EvidenceOrigin.LIVE_SEARCH
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence search is not configured with a supported provider.",
        )
    return CompleteAnalysisService(
        claim_extractor=HostedLLMClaimExtractor(),
        evidence_provider=evidence_provider,
        assessment_provider=HostedLLMAssessor(),
        evidence_origin=evidence_origin,
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_content(
    request: AnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    if not request.consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit consent is required before sending content for external processing.",
        )

    try:
        return await service.analyze(request.content)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim extraction is not configured.",
        ) from error
    except InvalidProviderResponse as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The claim extraction provider returned an unusable response.",
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The claim extraction provider is unavailable.",
        ) from error


@router.post("/analyze/complete", response_model=CompleteAnalysisResponse)
async def analyze_content_with_evidence(
    request: AnalysisRequest,
    service: CompleteAnalysisService = Depends(get_complete_analysis_service),
) -> CompleteAnalysisResponse:
    if not request.consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit consent is required before external processing.",
        )

    try:
        return await service.analyze(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A required analysis provider is not configured.",
        ) from error
    except (
        InvalidAssessmentResponse,
        InvalidEvidenceReference,
        InvalidProviderResponse,
        InvalidSearchResponse,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assessment provider returned an unusable or ungrounded response.",
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An analysis provider is unavailable.",
        ) from error
