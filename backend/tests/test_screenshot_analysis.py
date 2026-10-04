import asyncio
from io import BytesIO

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes.analysis import (
    get_complete_analysis_service,
    get_screenshot_analysis_service,
)
from app.main import app
from app.middleware.request_size import (
    MAX_SCREENSHOT_REQUEST_BYTES,
    ScreenshotRequestSizeLimitMiddleware,
)
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider
from app.providers.fixture_ocr import (
    CANONICAL_DEMO_TEXT,
    FixtureOCRProvider,
)
from app.providers.http_ocr import HTTPJSONOCRProvider, InvalidOCRResponse
from app.providers.ocr import OCRConfigurationError, OCRProviderError
from app.schemas.analysis import (
    AnalysisRequest,
    AssessmentState,
    Claim,
    ClaimAssessment,
    ClaimDraft,
    ClaimKind,
    EvidenceOrigin,
    RankedEvidenceSource,
)
from app.services.complete_analysis import CompleteAnalysisService
from app.services.screenshot_analysis import (
    MAX_SCREENSHOT_BYTES,
    ScreenshotAnalysisService,
)

DEMO_OCR_TEXT = (
    "SEBI approved XYZ investment plan. Contact test.person@example.com."
)
DEMO_CLAIM = "SEBI approved XYZ investment plan."


def png_image(width: int = 2, height: int = 2) -> bytes:
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeClaimExtractor:
    def __init__(self) -> None:
        self.received_text: str | None = None

    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        self.received_text = normalized_text
        return [ClaimDraft(text=DEMO_CLAIM, kind=ClaimKind.FACTUAL)]


class FakeAssessmentProvider:
    def __init__(self) -> None:
        self.evidence_package: list[RankedEvidenceSource] = []
        self.evidence_packages: list[list[RankedEvidenceSource]] = []

    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        self.evidence_package = evidence_package
        self.evidence_packages.append(evidence_package)
        return ClaimAssessment(
            assessment=AssessmentState.UNVERIFIED,
            rationale="The demo evidence is illustrative.",
            evidence_ids=[source.evidence_id for source in evidence_package],
            uncertainty="A live source page has not been reviewed.",
        )


class CanonicalClaimExtractor:
    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        assert normalized_text == " ".join(CANONICAL_DEMO_TEXT.split())
        return [
            ClaimDraft(
                text="SEBI approved XYZ investment plan.",
                kind=ClaimKind.FACTUAL,
            ),
            ClaimDraft(
                text="XYZ investment plan promises a guaranteed 30% return.",
                kind=ClaimKind.FINANCIAL,
            ),
            ClaimDraft(
                text="Only 200 slots remaining for XYZ investment plan.",
                kind=ClaimKind.PROMOTIONAL,
            ),
        ]


class OverconfidentFixtureAssessmentProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        self.calls += 1
        return ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="The supplied source supports the claim.",
            evidence_ids=[source.evidence_id for source in evidence_package],
            uncertainty="The source excerpt is illustrative.",
        )


class FailingOCRProvider:
    async def extract_text(self, image: bytes, media_type: str) -> str:
        raise OCRProviderError("private provider detail")


def make_complete_service() -> tuple[CompleteAnalysisService, FakeClaimExtractor, FakeAssessmentProvider]:
    extractor = FakeClaimExtractor()
    assessor = FakeAssessmentProvider()
    return (
        CompleteAnalysisService(
            claim_extractor=extractor,
            evidence_provider=DemoFixtureEvidenceProvider(),
            assessment_provider=assessor,
            evidence_origin=EvidenceOrigin.DEMO_FIXTURE,
        ),
        extractor,
        assessor,
    )


def configure_service(ocr_provider, complete_service=None):
    if complete_service is None:
        complete_service, _, _ = make_complete_service()
    service = ScreenshotAnalysisService(ocr_provider, complete_service)
    app.dependency_overrides[get_screenshot_analysis_service] = lambda: service
    return service


def test_upload_ocr_and_complete_analysis_flow_redacts_pii() -> None:
    complete_service, extractor, assessor = make_complete_service()
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr, complete_service)
    image = png_image()
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", image, "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["input_type"] == "screenshot"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(image)
    assert image not in response.content
    assert body["ocr_text"] == (
        "SEBI approved XYZ investment plan. Contact [REDACTED EMAIL]."
    )
    assert "test.person@example.com" not in response.text
    assert extractor.received_text == body["ocr_text"]
    assert len(ocr.calls) == 1
    assert body["analysis"]["results"][0]["claim"]["text"] == DEMO_CLAIM
    assert body["analysis"]["results"][0]["assessment"]["assessment"] == "Unverified"
    assert body["analysis"]["results"][0]["evidence"][0]["origin"] == "demo_fixture"
    assert body["analysis"]["results"][0]["manipulation_signals"][0]["signal_type"] == (
        "AUTHORITY_CLAIM"
    )
    assert assessor.evidence_package[0].origin == EvidenceOrigin.DEMO_FIXTURE


def test_missing_consent_blocks_ocr_provider() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert ocr.calls == []


def test_rejects_unsupported_type_before_ocr() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.gif", b"GIF89a", "image/gif")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert ocr.calls == []


def test_rejects_mime_signature_mismatch_before_ocr() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.jpg", png_image(), "image/jpeg")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert ocr.calls == []


def test_rejects_corrupt_image_before_ocr() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", b"not an image", "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert ocr.calls == []


def test_rejects_oversized_image_without_calling_ocr() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={
                "file": (
                    "large.png",
                    b"x" * (MAX_SCREENSHOT_BYTES + 1),
                    "image/png",
                )
            },
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert ocr.calls == []


def test_oversized_request_content_length_is_rejected_before_route() -> None:
    ocr = FixtureOCRProvider(DEMO_OCR_TEXT)
    configure_service(ocr)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            content=b"unused",
            headers={
                "Content-Type": "multipart/form-data; boundary=demo",
                "Content-Length": str(
                    MAX_SCREENSHOT_REQUEST_BYTES + 1
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert ocr.calls == []


def test_oversized_stream_without_content_length_is_rejected() -> None:
    messages = [
        {
            "type": "http.request",
            "body": b"x" * MAX_SCREENSHOT_REQUEST_BYTES,
            "more_body": True,
        },
        {"type": "http.request", "body": b"x", "more_body": False},
    ]
    sent: list[dict] = []

    async def downstream(scope, receive, send) -> None:
        while (message := await receive())["type"] == "http.request":
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive() -> dict:
        return messages.pop(0)

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(
        ScreenshotRequestSizeLimitMiddleware(downstream)(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/analyze/screenshot",
                "headers": [],
            },
            receive,
            send,
        )
    )

    assert sent[0]["status"] == 413


def test_empty_ocr_text_is_rejected_without_analysis() -> None:
    complete_service, extractor, _ = make_complete_service()
    ocr = FixtureOCRProvider(" \n ")
    configure_service(ocr, complete_service)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert extractor.received_text is None


def test_missing_ocr_configuration_returns_safe_503() -> None:
    complete_service, _, _ = make_complete_service()
    configure_service(HTTPJSONOCRProvider(endpoint=None), complete_service)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Screenshot OCR is not configured."


def test_ocr_provider_failure_does_not_expose_provider_detail() -> None:
    configure_service(FailingOCRProvider())
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "private provider detail" not in response.text


def test_explicit_demo_mode_selects_http_ocr_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("NIRNAY_OCR_DEMO_MODE", raising=False)
    monkeypatch.delenv("OCR_API_URL", raising=False)
    complete_service, _, _ = make_complete_service()
    app.dependency_overrides[get_complete_analysis_service] = lambda: complete_service
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Screenshot OCR is not configured."


def test_canonical_demo_screenshot_runs_through_complete_pipeline(
    monkeypatch,
) -> None:
    monkeypatch.setenv("NIRNAY_OCR_DEMO_MODE", "true")
    extractor = CanonicalClaimExtractor()
    assessor = OverconfidentFixtureAssessmentProvider()
    complete_service = CompleteAnalysisService(
        claim_extractor=extractor,
        evidence_provider=DemoFixtureEvidenceProvider(),
        assessment_provider=assessor,
        evidence_origin=EvidenceOrigin.DEMO_FIXTURE,
    )
    app.dependency_overrides[get_complete_analysis_service] = lambda: complete_service
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("whatsapp.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    analysis = result["analysis"]
    assert result["ocr_text"] == " ".join(CANONICAL_DEMO_TEXT.split())
    assert [
        claim["text"] for claim in (item["claim"] for item in analysis["results"])
    ] == [
        "SEBI approved XYZ investment plan.",
        "XYZ investment plan promises a guaranteed 30% return.",
        "Only 200 slots remaining for XYZ investment plan.",
    ]
    assert len(analysis["results"]) == 3
    assert assessor.calls == 3
    assert all(
        item["assessment"]["assessment"] == "Needs more evidence"
        for item in analysis["results"]
    )
    assert all(
        source["origin"] == "demo_fixture"
        and source["evidence"]["excerpt_source"] == "demo_fixture"
        for item in analysis["results"]
        for source in item["evidence"]
    )
    assert {
        signal["signal_type"] for signal in analysis["manipulation_signals"]
    } >= {
        "AUTHORITY_CLAIM",
        "GUARANTEED_RETURN",
        "SCARCITY_FOMO",
        "URGENCY",
        "UNSUPPORTED_STATISTICAL_CLAIM",
    }


def test_rejects_image_over_pixel_limit_before_ocr(monkeypatch) -> None:
    class OversizedImage:
        format = "PNG"
        size = (5_000, 5_000)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def verify(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.screenshot_analysis.Image.open",
        lambda _image: OversizedImage(),
    )
    from app.services.screenshot_analysis import validate_screenshot

    with pytest.raises(ValueError, match="dimensions exceed"):
        validate_screenshot(b"not needed by fake decoder", "image/png")


def test_ocr_text_over_analysis_limit_is_rejected() -> None:
    complete_service, extractor, _ = make_complete_service()
    configure_service(FixtureOCRProvider("x" * 20_001), complete_service)
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/screenshot",
            files={"file": ("message.png", png_image(), "image/png")},
            data={"consent": "true"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert extractor.received_text is None


def test_generic_http_ocr_adapter_uses_configured_multipart_contract() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"text": DEMO_OCR_TEXT})

    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        api_key="unit-test-key",
        transport=httpx.MockTransport(handle),
    )
    output = asyncio.run(provider.extract_text(png_image(), "image/png"))

    assert output == DEMO_OCR_TEXT
    assert requests[0].url == "https://ocr.example/recognize"
    assert requests[0].headers["authorization"] == "Bearer unit-test-key"
    assert "name=\"file\"" in requests[0].content.decode("latin1")


def test_generic_http_ocr_adapter_rejects_malformed_response() -> None:
    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"result": "no text field"})
        ),
    )

    try:
        asyncio.run(provider.extract_text(png_image(), "image/png"))
    except InvalidOCRResponse:
        pass
    else:
        raise AssertionError("Malformed OCR output should be rejected.")


def test_generic_http_ocr_adapter_rejects_malformed_endpoint() -> None:
    provider = HTTPJSONOCRProvider(endpoint="http://[")

    with pytest.raises(OCRConfigurationError):
        asyncio.run(provider.extract_text(png_image(), "image/png"))


@pytest.mark.parametrize("response_body", [b"\xff", b'{"text":'])
def test_generic_http_ocr_adapter_rejects_invalid_utf8_or_json(
    response_body: bytes,
) -> None:
    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=response_body,
                headers={"content-type": "application/json"},
            )
        ),
    )

    with pytest.raises(InvalidOCRResponse):
        asyncio.run(provider.extract_text(png_image(), "image/png"))


@pytest.mark.parametrize("response_body", [{"result": "text only"}, {"text": 42}])
def test_generic_http_ocr_adapter_requires_string_text(
    response_body: dict,
) -> None:
    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response_body)
        ),
    )

    with pytest.raises(InvalidOCRResponse):
        asyncio.run(provider.extract_text(png_image(), "image/png"))


def test_generic_http_ocr_adapter_handles_non_2xx_without_response_body() -> None:
    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                content=b"provider response body must not escape",
            )
        ),
    )

    with pytest.raises(OCRProviderError) as error:
        asyncio.run(provider.extract_text(png_image(), "image/png"))

    assert "provider response body" not in str(error.value)


@pytest.mark.parametrize(
    "failure_type",
    [httpx.ReadTimeout, httpx.ConnectError],
)
def test_generic_http_ocr_adapter_handles_timeout_and_network_errors(
    failure_type,
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise failure_type("provider unavailable", request=request)

    provider = HTTPJSONOCRProvider(
        endpoint="https://ocr.example/recognize",
        transport=httpx.MockTransport(fail),
    )

    with pytest.raises(OCRProviderError) as error:
        asyncio.run(provider.extract_text(png_image(), "image/png"))

    assert "provider unavailable" not in str(error.value)


def test_text_analysis_request_contract_is_not_changed() -> None:
    assert AnalysisRequest.model_fields.keys() == {"content", "consent"}
