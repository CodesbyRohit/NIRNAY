import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analysis import get_complete_analysis_service
from app.main import app
from app.providers.hosted_assessor import (
    HostedLLMAssessor,
    InvalidAssessmentResponse,
)
from app.schemas.analysis import (
    AnalysisRequest,
    AssessmentState,
    Claim,
    ClaimAssessment,
    ClaimKind,
    ClaimDraft,
    EvidenceExcerpt,
    EvidenceOrigin,
    EvidenceStatus,
    EvidenceSource,
    RankedEvidenceSource,
    SourceTier,
)
from app.services.assessment import AssessmentService, InvalidEvidenceReference
from app.services.complete_analysis import CompleteAnalysisService
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider


def make_claim(text: str = "The XYZ plan guarantees a 30% return.") -> Claim:
    return Claim(id=uuid4(), text=text, kind=ClaimKind.FINANCIAL)


def make_evidence(
    *,
    source_tier: SourceTier = SourceTier.TIER_1,
    status: EvidenceStatus = EvidenceStatus.RELEVANT,
    origin: EvidenceOrigin = EvidenceOrigin.LIVE_SEARCH,
    excerpt_source: str | None = "source_page_excerpt",
    excerpt: str | None = "The XYZ plan guarantees a 30% return.",
) -> RankedEvidenceSource:
    return RankedEvidenceSource(
        evidence_id=uuid4(),
        title="Evidence source",
        url="https://sebi.gov.in/notice",
        domain="sebi.gov.in",
        source_tier=source_tier,
        evidence=EvidenceExcerpt(
            status=status,
            excerpt=excerpt,
            excerpt_source=excerpt_source,
        ),
        origin=origin,
    )


class FakeAssessmentProvider:
    def __init__(self, assessment: ClaimAssessment) -> None:
        self.assessment = assessment
        self.claim: Claim | None = None
        self.package: list[RankedEvidenceSource] = []

    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        self.claim = claim
        self.package = evidence_package
        return self.assessment


def run_assessment(
    claim: Claim,
    evidence: list[RankedEvidenceSource],
    assessment: ClaimAssessment,
) -> tuple[ClaimAssessment, FakeAssessmentProvider]:
    provider = FakeAssessmentProvider(assessment)
    result = asyncio.run(AssessmentService(provider).assess(claim, evidence))
    return result, provider


def test_directly_supporting_evidence_can_be_supported() -> None:
    claim = make_claim()
    source = make_evidence()
    result, _ = run_assessment(
        claim,
        [source],
        ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="The source excerpt directly states the same return guarantee.",
            evidence_ids=[source.evidence_id],
            uncertainty="The assessment is limited to this retrieved excerpt.",
        ),
    )

    assert result.assessment == AssessmentState.SUPPORTED
    assert result.evidence_ids == [source.evidence_id]


def test_directly_conflicting_evidence_can_be_contradicted() -> None:
    claim = make_claim()
    source = make_evidence(excerpt="The XYZ plan does not guarantee any return.")
    result, _ = run_assessment(
        claim,
        [source],
        ClaimAssessment(
            assessment=AssessmentState.CONTRADICTED,
            rationale="The excerpt explicitly says the plan makes no guarantee.",
            evidence_ids=[source.evidence_id],
            uncertainty="The conclusion is limited to the supplied source excerpt.",
        ),
    )

    assert result.assessment == AssessmentState.CONTRADICTED


def test_no_evidence_is_unverified_without_calling_provider() -> None:
    claim = make_claim()
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.CONTRADICTED,
            rationale="This should not be used.",
            evidence_ids=[],
            uncertainty="This should not be used.",
        )
    )

    result = asyncio.run(AssessmentService(provider).assess(claim, []))

    assert result.assessment == AssessmentState.UNVERIFIED
    assert result.evidence_ids == []
    assert provider.claim is None


def test_weak_evidence_remains_needs_more_evidence() -> None:
    claim = make_claim()
    source = make_evidence(
        status=EvidenceStatus.WEAK_PARTIAL,
        excerpt_source="search_provider_snippet",
    )
    result, _ = run_assessment(
        claim,
        [source],
        ClaimAssessment(
            assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
            rationale="The snippet only partially overlaps the claim.",
            evidence_ids=[source.evidence_id],
            uncertainty="The underlying page has not been retrieved.",
        ),
    )

    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE


def test_conflicting_evidence_is_preserved_as_needs_more_evidence() -> None:
    claim = make_claim()
    supporting = make_evidence()
    conflicting = make_evidence(
        source_tier=SourceTier.TIER_4,
        excerpt="The XYZ plan makes no guaranteed return.",
    )
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
            rationale="The supplied excerpts conflict.",
            evidence_ids=[supporting.evidence_id, conflicting.evidence_id],
            uncertainty="The disagreement needs further review.",
        )
    )

    result = asyncio.run(
        AssessmentService(provider).assess(claim, [supporting, conflicting])
    )

    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE
    assert set(result.evidence_ids) == {supporting.evidence_id, conflicting.evidence_id}
    assert len(provider.package) == 2


def test_irrelevant_tier_one_source_cannot_support_claim() -> None:
    claim = make_claim()
    source = make_evidence(
        status=EvidenceStatus.NO_RELEVANT,
        excerpt="A notice about unrelated investor education.",
    )
    result, _ = run_assessment(
        claim,
        [source],
        ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="The provider guessed based on source tier.",
            evidence_ids=[source.evidence_id],
            uncertainty="No direct excerpt supports the claim.",
        ),
    )

    assert source.source_tier == SourceTier.TIER_1
    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE


def test_lower_tier_conflict_is_not_dropped_from_assessment_package() -> None:
    claim = make_claim()
    high_tier = make_evidence()
    low_tier_conflict = make_evidence(
        source_tier=SourceTier.TIER_4,
        excerpt="The XYZ plan does not guarantee a 30% return.",
    )
    result, provider = run_assessment(
        claim,
        [high_tier, low_tier_conflict],
        ClaimAssessment(
            assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
            rationale="A lower-tier excerpt conflicts with the other excerpt.",
            evidence_ids=[high_tier.evidence_id, low_tier_conflict.evidence_id],
            uncertainty="The conflicting excerpts have different source tiers.",
        ),
    )

    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE
    assert {item.evidence_id for item in provider.package} == {
        high_tier.evidence_id,
        low_tier_conflict.evidence_id,
    }


def test_nonexistent_evidence_id_is_rejected() -> None:
    source = make_evidence()
    claim = make_claim()
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="Unsupported reference.",
            evidence_ids=[uuid4()],
            uncertainty="Reference was not supplied.",
        )
    )

    with pytest.raises(InvalidEvidenceReference):
        asyncio.run(AssessmentService(provider).assess(claim, [source]))


def test_nonexistent_evidence_reference_in_narrative_is_rejected() -> None:
    source = make_evidence()
    claim = make_claim()
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
            rationale=f"See evidence {uuid4()}.",
            evidence_ids=[],
            uncertainty="The reference was not supplied.",
        )
    )

    with pytest.raises(InvalidEvidenceReference):
        asyncio.run(AssessmentService(provider).assess(claim, [source]))


def test_provider_cannot_add_url_to_narrative() -> None:
    source = make_evidence()
    claim = make_claim()
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.NEEDS_MORE_EVIDENCE,
            rationale="See https://invented.example/source.",
            evidence_ids=[],
            uncertainty="Source is unavailable.",
        )
    )

    with pytest.raises(InvalidAssessmentResponse):
        asyncio.run(AssessmentService(provider).assess(claim, [source]))


def test_supported_without_evidence_ids_is_rejected() -> None:
    source = make_evidence()
    claim = make_claim()
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="No citation.",
            evidence_ids=[],
            uncertainty="Evidence ID required.",
        )
    )

    with pytest.raises(InvalidAssessmentResponse):
        asyncio.run(AssessmentService(provider).assess(claim, [source]))


@pytest.mark.parametrize(
    "provider_content",
    [
        '{"assessment":"Probably true","rationale":"x","evidence_ids":[],"uncertainty":"x"}',
        '{"assessment":"Supported","rationale":"x","evidence_ids":[],"uncertainty":"x","confidence":0.95}',
        '{"assessment":"Supported","rationale":"95% confidence","evidence_ids":[],"uncertainty":"x"}',
        '{"assessment":"Supported","rationale":"See https://not-supplied.example.","evidence_ids":[],"uncertainty":"x"}',
    ],
)
def test_invalid_assessment_output_is_rejected(provider_content: str) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": provider_content}}]},
        )
    )
    assessor = HostedLLMAssessor(
        api_key="test-key",
        base_url="https://provider.example/v1",
        transport=transport,
    )

    with pytest.raises(InvalidAssessmentResponse):
        asyncio.run(assessor.assess(make_claim(), [make_evidence()]))


def test_assessment_provider_receives_only_claim_and_evidence_package() -> None:
    claim = make_claim()
    source = make_evidence()
    requests: list[httpx.Request] = []
    response_content = json.dumps(
        {
            "assessment": "Needs more evidence",
            "rationale": "Only a provider snippet was supplied.",
            "evidence_ids": [str(source.evidence_id)],
            "uncertainty": "The source page has not been checked.",
        }
    )

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": response_content}}]},
        )

    assessor = HostedLLMAssessor(
        api_key="test-key",
        transport=httpx.MockTransport(handle),
    )
    result = asyncio.run(assessor.assess(claim, [source]))

    request_body = json.loads(requests[0].content)
    sent = json.loads(request_body["messages"][1]["content"])
    assert set(sent) == {"claim", "evidence_package"}
    assert sent["claim"] == {"text": claim.text, "kind": claim.kind.value}
    assert sent["evidence_package"][0]["evidence_id"] == str(source.evidence_id)
    assert "original input" not in sent["claim"]["text"].lower()
    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE
    assert set(result.model_dump()) == {
        "assessment",
        "rationale",
        "evidence_ids",
        "uncertainty",
    }


def test_snippet_cannot_be_promoted_to_supported() -> None:
    claim = make_claim()
    source = make_evidence(excerpt_source="search_provider_snippet")
    result, _ = run_assessment(
        claim,
        [source],
        ClaimAssessment(
            assessment=AssessmentState.SUPPORTED,
            rationale="The snippet appears to support the claim.",
            evidence_ids=[source.evidence_id],
            uncertainty="Page not fetched.",
        ),
    )

    assert result.assessment == AssessmentState.NEEDS_MORE_EVIDENCE


def test_demo_fixture_runs_through_assessment_using_fixture_evidence() -> None:
    claim = Claim(
        id=uuid4(),
        text="SEBI approved XYZ investment plan.",
        kind=ClaimKind.FACTUAL,
    )
    sources = asyncio.run(DemoFixtureEvidenceProvider().search(claim.text))
    from app.services.source_ranking import rank_sources

    package = rank_sources(sources, claim.text, EvidenceOrigin.DEMO_FIXTURE)
    provider = FakeAssessmentProvider(
        ClaimAssessment(
            assessment=AssessmentState.UNVERIFIED,
            rationale="The illustrative fixture does not establish this claim.",
            evidence_ids=[package[0].evidence_id],
            uncertainty="This is demo material, not a retrieved source page.",
        )
    )
    result = asyncio.run(AssessmentService(provider).assess(claim, package))

    assert package[0].origin == EvidenceOrigin.DEMO_FIXTURE
    assert result.assessment == AssessmentState.UNVERIFIED
    assert provider.package[0].origin == EvidenceOrigin.DEMO_FIXTURE


class FakeClaimExtractor:
    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        return [ClaimDraft(text="SEBI approved XYZ investment plan.", kind="factual")]


class FakeAssessmentFlow:
    async def assess(self, claim, evidence_package):
        return ClaimAssessment(
            assessment=AssessmentState.UNVERIFIED,
            rationale="The available fixture does not confirm approval.",
            evidence_ids=[source.evidence_id for source in evidence_package],
            uncertainty="Fixture evidence is illustrative only.",
        )


def test_complete_analysis_route_returns_claim_evidence_and_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.providers.fixture_evidence import DemoFixtureEvidenceProvider

    service = CompleteAnalysisService(
        claim_extractor=FakeClaimExtractor(),
        evidence_provider=DemoFixtureEvidenceProvider(),
        assessment_provider=FakeAssessmentFlow(),
        evidence_origin=EvidenceOrigin.DEMO_FIXTURE,
    )
    app.dependency_overrides[get_complete_analysis_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/complete",
            json={"content": "SEBI approved XYZ investment plan.", "consent": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["claim"]["text"] == "SEBI approved XYZ investment plan."
    assert result["assessment"]["assessment"] == "Unverified"
    assert result["evidence"][0]["origin"] == "demo_fixture"
    assert result["assessment"]["evidence_ids"] == [result["evidence"][0]["evidence_id"]]
    assert "manipulation_signals" in result
    assert result["manipulation_signals"][0]["signal_type"] == "AUTHORITY_CLAIM"
    assert response.json()["manipulation_signals"][0]["signal_type"] == "AUTHORITY_CLAIM"


def test_complete_analysis_requires_consent_before_provider_calls() -> None:
    class MustNotRunExtractor:
        async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
            raise AssertionError("provider must not run without consent")

    service = CompleteAnalysisService(
        claim_extractor=MustNotRunExtractor(),
        evidence_provider=DemoFixtureEvidenceProvider(),
        assessment_provider=FakeAssessmentFlow(),
        evidence_origin=EvidenceOrigin.DEMO_FIXTURE,
    )
    app.dependency_overrides[get_complete_analysis_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/analyze/complete",
            json={"content": "Financial claim without consent."},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
