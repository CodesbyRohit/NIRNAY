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
    EvidenceOrigin,
    EvidenceSource,
    EvidenceStatus,
    SourceTier,
)
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
    assert request_body["include_raw_content"] is False
    assert request_body["api_key"] == "test-key"


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
