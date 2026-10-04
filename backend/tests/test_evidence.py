import asyncio
import json
from collections.abc import Callable
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.evidence import get_evidence_service
from app.main import app
from app.providers.errors import ProviderError
from app.providers.fixture_evidence import DemoFixtureEvidenceProvider
from app.providers.tavily_search import TavilyEvidenceSearch
from app.schemas.analysis import (
    AssessmentState,
    Claim,
    ClaimAssessment,
    ClaimKind,
    EvidenceRequest,
    EvidenceOrigin,
    RankedEvidenceSource,
    EvidenceSource,
    EvidenceStatus,
    SourceTier,
)
from app.services.assessment import AssessmentService
from app.services.evidence import EvidenceService
from app.services.source_ranking import classify_domain, rank_sources

CLAIMS = [
    {
        "id": "f6c8dfac-6e72-4ceb-a8c7-cf42f52ea8f0",
        "text": "SEBI approved XYZ investment plan.",
        "kind": "factual",
    },
    {
        "id": "2f53d2e0-3db7-4134-9556-ccab027d20fd",
        "text": "The plan guarantees a 30% return.",
        "kind": "financial",
    },
]
SOURCE = {
    "title": "Official notice",
    "url": "https://example.org/notice",
    "snippet": "A source excerpt about the queried claim.",
    "published_date": "2026-09-01",
}


class FakeSearchProvider:
    def __init__(
        self,
        sources: list[dict[str, str]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.sources = sources or []
        self.error = error
        self.queries: list[str] = []

    async def search(self, query: str) -> list[EvidenceSource]:
        self.queries.append(query)
        if self.error:
            raise self.error
        return [EvidenceSource.model_validate(source) for source in self.sources]


@pytest.fixture
def client_and_search() -> Callable[[FakeSearchProvider], TestClient]:
    client = TestClient(app)

    def configure(provider: FakeSearchProvider) -> TestClient:
        app.dependency_overrides[get_evidence_service] = lambda: EvidenceService(provider)
        return client

    yield configure
    app.dependency_overrides.clear()


def test_searches_each_claim_and_returns_cited_source_snippets(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    provider = FakeSearchProvider([SOURCE])
    response = client_and_search(provider).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS, "consent": True},
    )

    assert response.status_code == 200
    assert provider.queries == [claim["text"] for claim in CLAIMS]
    body = response.json()
    assert [result["claim_id"] for result in body["results"]] == [
        claim["id"] for claim in CLAIMS
    ]
    result_source = body["results"][0]["sources"][0]
    assert result_source["title"] == SOURCE["title"]
    assert result_source["url"] == SOURCE["url"]
    assert result_source["domain"] == "example.org"
    assert result_source["source_tier"] == "tier_4"
    assert result_source["evidence"] == {
        "status": "no_relevant_evidence_found",
        "excerpt": SOURCE["snippet"],
        "excerpt_source": "search_provider_snippet",
    }
    assert result_source["origin"] == "live_search"
    assert set(body) == {"results"}
    assert set(body["results"][0]) == {"claim_id", "sources"}
    assert set(body["results"][0]["sources"][0]) == {
        "title",
        "url",
        "evidence_id",
        "domain",
        "source_tier",
        "evidence",
        "published_date",
        "origin",
    }


def test_missing_consent_does_not_search(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    provider = FakeSearchProvider([SOURCE])
    response = client_and_search(provider).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS},
    )

    assert response.status_code == 403
    assert provider.queries == []


def test_limits_claim_batch_to_ten(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    provider = FakeSearchProvider()
    eleven_claims = [
        {
            **CLAIMS[0],
            "id": str(UUID("f6c8dfac-6e72-4ceb-a8c7-cf42f52ea8f0").int + index),
        }
        for index in range(11)
    ]
    response = client_and_search(provider).post(
        "/api/v1/evidence",
        json={"claims": eleven_claims, "consent": True},
    )

    assert response.status_code == 422
    assert provider.queries == []


def test_provider_failure_returns_safe_error(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    provider = FakeSearchProvider(error=ProviderError("private upstream detail"))
    response = client_and_search(provider).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS[:1], "consent": True},
    )

    assert response.status_code == 502
    assert "private upstream detail" not in response.text


def test_missing_search_configuration_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    response = TestClient(app).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS[:1], "consent": True},
    )

    assert response.status_code == 503


def test_rejects_malformed_search_results() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"results": [{"title": "Missing URL"}]})
    )
    app.dependency_overrides[get_evidence_service] = lambda: EvidenceService(
        TavilyEvidenceSearch(api_key="test-key", transport=transport)
    )
    try:
        response = TestClient(app).post(
            "/api/v1/evidence",
            json={"claims": CLAIMS[:1], "consent": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "The evidence search provider returned unusable results."


def test_search_provider_sends_only_claim_query_and_no_answer_generation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": SOURCE["title"],
                        "url": SOURCE["url"],
                        "content": SOURCE["snippet"],
                        "published_date": SOURCE["published_date"],
                        "raw_content": (
                            "The actual source page discusses related details."
                        ),
                    }
                ]
            },
        )

    provider = TavilyEvidenceSearch(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    results = asyncio.run(provider.search("A claim to find sources for"))

    assert len(results) == 1
    request_body = json.loads(requests[0].content)
    assert request_body["query"] == "A claim to find sources for"
    assert request_body["max_results"] == 3
    assert request_body["include_answer"] is False
    assert request_body["include_raw_content"] is True
    assert request_body["api_key"] == "test-key"
    assert results[0].raw_content == "The actual source page discusses related details."


def test_extracts_relevant_excerpt_from_actual_source_page() -> None:
    source = EvidenceSource(
        title="Investor information",
        url="https://www.sebi.gov.in/investor",
        snippet="Search snippet that is not the page excerpt.",
        raw_content=(
            "Home | About | Contact\n"
            "SEBI provides investor education resources for investors. "
            "These materials explain risks before financial decisions.\n"
            "Unrelated contact information follows."
        ),
    )

    ranked = rank_sources(
        [source],
        "SEBI provides investor education resources.",
        EvidenceOrigin.LIVE_SEARCH,
    )

    assert len(ranked) == 1
    assert ranked[0].evidence.status == EvidenceStatus.RELEVANT
    assert ranked[0].evidence.excerpt_source == "source_page_excerpt"
    assert ranked[0].evidence.excerpt == (
        "SEBI provides investor education resources for investors."
    )
    assert "Search snippet" not in (ranked[0].evidence.excerpt or "")


def test_unrelated_raw_page_does_not_produce_random_page_excerpt() -> None:
    source = EvidenceSource(
        title="Mumbai weather",
        url="https://weather.example/mumbai",
        snippet=None,
        raw_content="Today's weather forecast covers rainfall in Mumbai.",
    )

    ranked = rank_sources(
        [source],
        "SEBI provides investor education resources.",
        EvidenceOrigin.LIVE_SEARCH,
    )

    assert ranked[0].evidence.status == EvidenceStatus.NO_RELEVANT
    assert ranked[0].evidence.excerpt is None
    assert ranked[0].evidence.excerpt_source is None


def test_weak_raw_page_match_is_labeled_as_weak_page_evidence() -> None:
    source = EvidenceSource(
        title="Investor information",
        url="https://www.sebi.gov.in/investor",
        snippet="A search snippet with extra claim terms.",
        raw_content="SEBI maintains several public information pages.",
    )

    ranked = rank_sources(
        [source],
        "SEBI provides investor education resources.",
        EvidenceOrigin.LIVE_SEARCH,
    )

    assert ranked[0].evidence.status == EvidenceStatus.WEAK_PARTIAL
    assert ranked[0].evidence.excerpt_source == "source_page_excerpt"
    assert ranked[0].evidence.excerpt == "SEBI maintains several public information pages."


def test_raw_page_content_is_excluded_from_model_serialization_and_repr() -> None:
    private_page_text = "SECRET PAGE CONTENT must remain provider-only."
    source = EvidenceSource(
        title="Source",
        url="https://example.org/page",
        snippet="Snippet",
        raw_content=private_page_text,
    )

    assert "raw_content" not in source.model_dump()
    assert private_page_text not in repr(source)
    ranked = rank_sources(
        [source],
        "An unrelated claim about an investment.",
        EvidenceOrigin.LIVE_SEARCH,
    )
    assert "raw_content" not in ranked[0].model_dump()
    assert private_page_text not in str(ranked[0].model_dump())


def test_fixture_origin_never_promotes_raw_content_to_page_excerpt() -> None:
    source = EvidenceSource(
        title="Illustrative source",
        url="https://www.sebi.gov.in/investor",
        snippet="Illustrative fixture text.",
        raw_content="SEBI provides investor education resources for investors.",
    )

    ranked = rank_sources(
        [source],
        "SEBI provides investor education resources.",
        EvidenceOrigin.DEMO_FIXTURE,
    )

    assert ranked[0].origin == EvidenceOrigin.DEMO_FIXTURE
    assert ranked[0].evidence.excerpt_source == "demo_fixture"
    assert ranked[0].evidence.excerpt != source.raw_content


def test_deduplication_preserves_raw_page_content() -> None:
    sources = [
        EvidenceSource(
            title="Page",
            url="https://news.example/page",
            snippet="A search snippet.",
        ),
        EvidenceSource(
            title="Page",
            url="https://news.example/page/",
            snippet="The longer provider snippet with more background.",
            raw_content="The actual claim details appear on this source page.",
        ),
    ]

    ranked = rank_sources(sources, "actual claim details source page")

    assert len(ranked) == 1
    assert ranked[0].evidence.excerpt_source == "source_page_excerpt"
    assert ranked[0].evidence.status == EvidenceStatus.RELEVANT


def test_tavily_raw_and_snippet_paths_remain_guarded_end_to_end() -> None:
    claim = Claim(
        id=UUID("f6c8dfac-6e72-4ceb-a8c7-cf42f52ea8f0"),
        text="SEBI provides investor education resources.",
        kind=ClaimKind.FACTUAL,
    )
    page_passage = "SEBI does not provide investor education resources."
    full_page = (
        "Navigation and unrelated page content. "
        f"{page_passage} Contact: private-page-detail."
    )

    for raw_content, expected_excerpt_source, expected_assessment in (
        (
            full_page,
            "source_page_excerpt",
            AssessmentState.CONTRADICTED,
        ),
        (
            None,
            "search_provider_snippet",
            AssessmentState.NEEDS_MORE_EVIDENCE,
        ),
    ):
        requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Independent report",
                            "url": "https://www.sebi.gov.in/investor-resources",
                            "content": page_passage,
                            "raw_content": raw_content,
                        }
                    ]
                },
            )

        tavily = TavilyEvidenceSearch(
            api_key="test-key",
            transport=httpx.MockTransport(handle),
        )
        evidence_response = asyncio.run(
            EvidenceService(tavily).retrieve(
                EvidenceRequest(claims=[claim], consent=True)
            )
        )
        source = evidence_response.results[0].sources[0]
        serialized_response = evidence_response.model_dump_json()

        assert json.loads(requests[0].content)["include_raw_content"] is True
        assert source.origin == EvidenceOrigin.LIVE_SEARCH
        assert source.domain == "www.sebi.gov.in"
        assert source.source_tier == SourceTier.TIER_1
        assert source.evidence.excerpt_source == expected_excerpt_source
        assert source.evidence.excerpt
        assert source.evidence.status in {
            EvidenceStatus.RELEVANT,
            EvidenceStatus.WEAK_PARTIAL,
        }
        assert source.evidence.excerpt == page_passage
        assert raw_content is None or raw_content not in serialized_response
        assert "raw_content" not in serialized_response
        UUID(str(source.evidence_id))

        class AssessmentProbe:
            package: list[RankedEvidenceSource] = []

            async def assess(
                self,
                assessment_claim: Claim,
                evidence_package: list[RankedEvidenceSource],
            ) -> ClaimAssessment:
                self.package = evidence_package
                return ClaimAssessment(
                    assessment=AssessmentState.CONTRADICTED,
                    rationale="The supplied evidence was considered.",
                    evidence_ids=[evidence_package[0].evidence_id],
                    uncertainty="Limited to the supplied evidence package.",
                )

        assessor = AssessmentProbe()
        assessed = asyncio.run(
            AssessmentService(assessor).assess(claim, evidence_response.results[0].sources)
        )

        assert assessed.assessment == expected_assessment
        assert assessor.package == evidence_response.results[0].sources
        assert not hasattr(assessor.package[0], "raw_content")
        assert raw_content is None or raw_content not in str(
            assessor.package[0].model_dump()
        )


@pytest.mark.parametrize(
    ("hostname", "expected_tier"),
    [
        ("sebi.gov.in", SourceTier.TIER_1),
        ("www.sebi.gov.in", SourceTier.TIER_1),
        ("rbi.org.in", SourceTier.TIER_1),
        ("nsdl.co.in", SourceTier.TIER_1),
        ("nseindia.com", SourceTier.TIER_1),
        ("bseindia.com", SourceTier.TIER_1),
        ("investor.gov.in", SourceTier.TIER_1),
        ("unknown-finance.example", SourceTier.TIER_4),
    ],
)
def test_classifies_source_tiers_deterministically(
    hostname: str,
    expected_tier: SourceTier,
) -> None:
    assert classify_domain(hostname) == expected_tier


def test_ranking_prefers_higher_tier_relevant_source() -> None:
    sources = [
        EvidenceSource(
            title="Investment plan registration details",
            url="https://random-finance.example/plan",
            snippet="XYZ investment plan and registration details",
        ),
        EvidenceSource(
            title="SEBI notice",
            url="https://www.sebi.gov.in/notice",
            snippet="XYZ investment plan notice",
        ),
    ]

    ranked = rank_sources(sources, "XYZ investment plan")

    assert ranked[0].domain == "www.sebi.gov.in"
    assert ranked[0].source_tier == SourceTier.TIER_1


def test_relevance_affects_order_within_same_tier() -> None:
    sources = [
        EvidenceSource(
            title="Plan background",
            url="https://news.example/plan",
            snippet="General market update with little overlap",
        ),
        EvidenceSource(
            title="XYZ investment plan details",
            url="https://news.example/xyz-plan",
            snippet="XYZ investment plan return details",
        ),
    ]

    ranked = rank_sources(sources, "XYZ investment plan return")

    assert ranked[0].url.host == "news.example"
    assert str(ranked[0].url).endswith("/xyz-plan")


def test_duplicate_sources_are_removed_and_best_copy_is_kept() -> None:
    sources = [
        EvidenceSource(
            title="Plan",
            url="https://news.example/plan",
            snippet="short",
        ),
        EvidenceSource(
            title="Plan",
            url="https://news.example/plan/",
            snippet="The XYZ investment plan details and returns.",
        ),
    ]

    ranked = rank_sources(sources, "XYZ investment plan returns")

    assert len(ranked) == 1
    assert ranked[0].evidence.excerpt == "The XYZ investment plan details and returns."


def test_unavailable_source_is_marked_inaccessible() -> None:
    ranked = rank_sources(
        [
            EvidenceSource(
                title="Plan page",
                url="https://news.example/plan",
                snippet=None,
            )
        ],
        "plan details",
    )

    assert ranked[0].evidence.status == EvidenceStatus.INACCESSIBLE
    assert ranked[0].evidence.excerpt is None


def test_empty_evidence_remains_empty() -> None:
    assert rank_sources([], "A claim without search results") == []


def test_fixture_provider_returns_explicitly_illustrative_results() -> None:
    provider = DemoFixtureEvidenceProvider()
    sources = asyncio.run(
        provider.search("SEBI approved XYZ investment plan.")
    )

    assert len(sources) == 1
    assert "DEMO FIXTURE" in sources[0].title
    assert "does not represent a retrieved SEBI page" in (sources[0].snippet or "")


def test_fixture_provider_api_marks_evidence_as_demo_and_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVIDENCE_PROVIDER", "fixture")
    response = TestClient(app).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS[:1], "consent": True},
    )

    assert response.status_code == 200
    source = response.json()["results"][0]["sources"][0]
    assert source["origin"] == "demo_fixture"
    assert source["source_tier"] == "tier_1"
    assert source["evidence"]["excerpt_source"] == "demo_fixture"
    assert "Illustrative demo snippet only" in source["evidence"]["excerpt"]


def test_live_search_api_marks_search_snippet_as_live_not_page_evidence(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    response = client_and_search(FakeSearchProvider([SOURCE])).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS[:1], "consent": True},
    )

    source = response.json()["results"][0]["sources"][0]
    assert source["origin"] == "live_search"
    assert source["evidence"]["excerpt_source"] == "search_provider_snippet"
    assert source["evidence"]["excerpt"] == SOURCE["snippet"]


def test_raw_page_content_is_not_serialized_in_evidence_api(
    client_and_search: Callable[[FakeSearchProvider], TestClient],
) -> None:
    private_text = "PRIVATE RAW PAGE CONTENT."
    provider = FakeSearchProvider([{**SOURCE, "raw_content": private_text}])

    response = client_and_search(provider).post(
        "/api/v1/evidence",
        json={"claims": CLAIMS[:1], "consent": True},
    )

    assert response.status_code == 200
    assert private_text not in response.text
    assert "raw_content" not in response.text


def test_source_tier_does_not_use_title_or_snippet() -> None:
    source = EvidenceSource(
        title="SEBI RBI NSDL NSE BSE Government of India",
        url="https://unknown-finance.example/article",
        snippet="Official Government of India source",
    )

    ranked = rank_sources([source], "Official Government of India source")

    assert ranked[0].source_tier == SourceTier.TIER_4


def test_low_relevance_result_does_not_claim_relevant_evidence() -> None:
    source = EvidenceSource(
        title="Markets today",
        url="https://news.example/markets",
        snippet="Broad market summary and indices.",
    )

    ranked = rank_sources([source], "XYZ investment plan guarantees returns")

    assert ranked[0].evidence.status == EvidenceStatus.NO_RELEVANT
    assert ranked[0].evidence.excerpt_source == "search_provider_snippet"
    assert ranked[0].evidence.excerpt == source.snippet
