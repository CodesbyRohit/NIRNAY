import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.providers.hosted_llm import (
    HostedLLMClaimExtractor,
    InvalidProviderResponse,
)
from app.providers.tavily_search import InvalidSearchResponse
from app.providers.errors import ProviderConfigurationError, ProviderError
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider
from app.providers.fixture_ocr import CanonicalDemoOCRProvider
from app.providers.http_ocr import HTTPJSONOCRProvider, InvalidOCRResponse
from app.providers.hosted_assessor import HostedLLMAssessor, InvalidAssessmentResponse
from app.providers.ocr import OCRConfigurationError, OCRProviderError
from app.providers.tavily_search import TavilyEvidenceSearch
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    CompleteAnalysisResponse,
    EvidenceOrigin,
    ScreenshotAnalysisResponse,
)
from app.services.analysis import AnalysisService
from app.services.assessment import InvalidEvidenceReference
from app.services.complete_analysis import CompleteAnalysisService
from app.services.screenshot_analysis import (
    MAX_SCREENSHOT_BYTES,
    InvalidScreenshot,
    ScreenshotAnalysisService,
    ScreenshotTooLarge,
    UnsupportedScreenshotType,
)

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


def get_screenshot_analysis_service(
    complete_service: CompleteAnalysisService = Depends(get_complete_analysis_service),
) -> ScreenshotAnalysisService:
    demo_mode = os.getenv("NIRNAY_OCR_DEMO_MODE", "").strip().lower() in {
        "1",
        "true",
    }
    ocr_provider = (
        CanonicalDemoOCRProvider()
        if demo_mode
        else HTTPJSONOCRProvider(
            endpoint=os.getenv("OCR_API_URL"),
            api_key=os.getenv("OCR_API_KEY"),
        )
    )
    return ScreenshotAnalysisService(
        ocr_provider=ocr_provider,
        complete_analysis_service=complete_service,
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


@router.post("/analyze/screenshot", response_model=ScreenshotAnalysisResponse)
async def analyze_screenshot(
    file: UploadFile = File(...),
    consent: bool = Form(False),
    service: ScreenshotAnalysisService = Depends(get_screenshot_analysis_service),
) -> ScreenshotAnalysisResponse:
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit consent is required before image processing.",
        )

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a PNG, JPEG, or WebP image.",
        )

    try:
        image = await file.read(MAX_SCREENSHOT_BYTES + 1)
    finally:
        await file.close()

    try:
        return await service.analyze(image, file.content_type, consent)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit consent is required before image processing.",
        ) from error
    except ScreenshotTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(error),
        ) from error
    except UnsupportedScreenshotType as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from error
    except InvalidScreenshot as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except OCRConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Screenshot OCR is not configured.",
        ) from error
    except InvalidOCRResponse as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The OCR provider returned unusable output.",
        ) from error
    except OCRProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The OCR provider is unavailable.",
        ) from error
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
            detail="An analysis provider returned an unusable or ungrounded response.",
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An analysis provider is unavailable.",
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
