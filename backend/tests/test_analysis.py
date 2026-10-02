import json
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analysis import get_analysis_service
from app.main import app
from app.providers.hosted_llm import (
    HostedLLMClaimExtractor,
    ProviderError,
)
from app.schemas.analysis import ClaimDraft
from app.services.analysis import AnalysisService

DEMO_CONTENT = (
    "SEBI approved XYZ investment plan. Guaranteed 30% return. "
    "Only 200 slots remaining. Join NOW!"
)
DEMO_CLAIMS = [
    {"text": "SEBI approved XYZ investment plan.", "kind": "factual"},
    {"text": "XYZ investment plan guarantees a 30% return.", "kind": "financial"},
    {"text": "Only 200 slots remain for the plan.", "kind": "promotional"},
]


class FakeExtractor:
    def __init__(
        self,
        claims: list[dict[str, str]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.claims = claims or []
        self.error = error
        self.received_text: str | None = None
        self.calls = 0

    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        self.calls += 1
        self.received_text = normalized_text
        if self.error:
            raise self.error
        return [ClaimDraft.model_validate(claim) for claim in self.claims]


@pytest.fixture
def client_and_extractor() -> Callable[[FakeExtractor], TestClient]:
    client = TestClient(app)

    def configure(extractor: FakeExtractor) -> TestClient:
        app.dependency_overrides[get_analysis_service] = lambda: AnalysisService(extractor)
        return client

    yield configure
    app.dependency_overrides.clear()


def test_extracts_separate_claims_from_multi_claim_input(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(DEMO_CLAIMS)
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": DEMO_CONTENT, "consent": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert [claim["text"] for claim in body["claims"]] == [
        claim["text"] for claim in DEMO_CLAIMS
    ]
    assert [claim["kind"] for claim in body["claims"]] == [
        claim["kind"] for claim in DEMO_CLAIMS
    ]
    assert extractor.received_text == DEMO_CONTENT


def test_extracts_a_single_claim(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor([{"text": "The plan offers a 30% return.", "kind": "financial"}])
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": "The plan offers a 30% return.", "consent": True},
    )

    assert response.status_code == 200
    assert len(response.json()["claims"]) == 1


@pytest.mark.parametrize("content", ["", " \n\t "])
def test_rejects_empty_input(
    content: str,
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(DEMO_CLAIMS)
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": content, "consent": True},
    )

    assert response.status_code == 422
    assert extractor.calls == 0


def test_rejects_oversized_input(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(DEMO_CLAIMS)
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": "x" * 20_001, "consent": True},
    )

    assert response.status_code == 422
    assert extractor.calls == 0


def test_rejects_malformed_hosted_llm_response() -> None:
    provider_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "claims": [
                                {
                                    "text": "The investment plan is true.",
                                    "kind": "financial",
                                    "truth_assessment": "true",
                                }
                            ]
                        }
                    )
                }
            }
        ]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=provider_body)
    )
    app.dependency_overrides[get_analysis_service] = lambda: AnalysisService(
        HostedLLMClaimExtractor(
            api_key="test-key",
            base_url="https://provider.example/v1",
            transport=transport,
        )
    )
    try:
        response = TestClient(app).post(
            "/api/v1/analyze",
            json={"content": "The investment plan is true.", "consent": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "The claim extraction provider returned an unusable response."


def test_provider_failure_is_returned_safely(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(error=ProviderError("upstream secret detail"))
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": DEMO_CONTENT, "consent": True},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "The claim extraction provider is unavailable."
    assert "upstream secret detail" not in response.text


def test_missing_provider_configuration_is_returned_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    response = TestClient(app).post(
        "/api/v1/analyze",
        json={"content": DEMO_CONTENT, "consent": True},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Claim extraction is not configured."


def test_missing_consent_does_not_call_provider(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(DEMO_CLAIMS)
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": DEMO_CONTENT},
    )

    assert response.status_code == 403
    assert extractor.calls == 0


def test_redacts_obvious_personal_identifiers_before_provider_call(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor([])
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={
            "content": "Contact test.person@example.com or +91 98765 43210. "
            "PAN ABCDE1234F; Aadhaar 1234 5678 9012.",
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert extractor.received_text is not None
    assert "test.person@example.com" not in extractor.received_text
    assert "98765 43210" not in extractor.received_text
    assert "ABCDE1234F" not in extractor.received_text
    assert "1234 5678 9012" not in extractor.received_text
    assert "[REDACTED EMAIL]" in extractor.received_text
    assert "[REDACTED PHONE]" in extractor.received_text
    assert "[REDACTED PAN]" in extractor.received_text
    assert "[REDACTED AADHAAR]" in extractor.received_text


def test_response_contains_only_extracted_claims_not_assessments(
    client_and_extractor: Callable[[FakeExtractor], TestClient],
) -> None:
    extractor = FakeExtractor(DEMO_CLAIMS[:1])
    response = client_and_extractor(extractor).post(
        "/api/v1/analyze",
        json={"content": DEMO_CONTENT, "consent": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"analysis_id", "status", "claims"}
    assert body["status"] == "completed"
    assert set(body["claims"][0]) == {"id", "text", "kind"}
    assert not any(
        word in response.text.lower()
        for word in ("truth", "confidence", "supported", "contradicted", "scam", "advice")
    )
