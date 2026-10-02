import re
from datetime import date
from urllib.parse import urlsplit, urlunsplit

from app.schemas.analysis import (
    EvidenceExcerpt,
    EvidenceOrigin,
    EvidenceSource,
    EvidenceStatus,
    RankedEvidenceSource,
    SourceTier,
)

_TIER_ONE_DOMAINS = (
    "sebi.gov.in",
    "rbi.org.in",
    "nsdl.co.in",
    "nseindia.com",
    "bseindia.com",
)
_GOVERNMENT_DOMAINS = ("gov.in", "nic.in")
_TIER_TWO_DOMAINS = (
    "nism.ac.in",
    "amfiindia.com",
    "imf.org",
    "worldbank.org",
    "bis.org",
)
_TIER_THREE_DOMAINS = (
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "financialexpress.com",
)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "to", "was", "were", "with",
}
_TIER_RANK = {
    SourceTier.TIER_1: 0,
    SourceTier.TIER_2: 1,
    SourceTier.TIER_3: 2,
    SourceTier.TIER_4: 3,
    SourceTier.UNKNOWN: 4,
}


def _matches_domain(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def classify_domain(hostname: str) -> SourceTier:
    normalized_host = hostname.rstrip(".").lower()
    if any(_matches_domain(normalized_host, domain) for domain in _TIER_ONE_DOMAINS):
        return SourceTier.TIER_1
    if any(_matches_domain(normalized_host, domain) for domain in _GOVERNMENT_DOMAINS):
        return SourceTier.TIER_1
    if any(_matches_domain(normalized_host, domain) for domain in _TIER_TWO_DOMAINS):
        return SourceTier.TIER_2
    if any(_matches_domain(normalized_host, domain) for domain in _TIER_THREE_DOMAINS):
        return SourceTier.TIER_3
    return SourceTier.TIER_4


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(value.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _published_day(published_date: str | None) -> date | None:
    if not published_date:
        return None
    try:
        return date.fromisoformat(published_date[:10])
    except ValueError:
        return None


def _build_ranked_source(
    source: EvidenceSource,
    claim_text: str,
    origin: EvidenceOrigin,
) -> tuple[RankedEvidenceSource, int]:
    hostname = urlsplit(str(source.url)).hostname
    if not hostname:
        raise ValueError("Evidence source URL has no valid hostname.")
    domain = hostname.rstrip(".").lower()
    tier = classify_domain(domain)

    claim_tokens = _tokens(claim_text)
    content = " ".join((source.title, source.snippet or ""))
    overlap = claim_tokens & _tokens(content)
    if source.snippet is None:
        evidence = EvidenceExcerpt(status=EvidenceStatus.INACCESSIBLE)
    elif not overlap:
        evidence = EvidenceExcerpt(
            status=EvidenceStatus.NO_RELEVANT,
            excerpt=source.snippet,
            excerpt_source=(
                "demo_fixture" if origin == EvidenceOrigin.DEMO_FIXTURE else "search_provider_snippet"
            ),
        )
    else:
        enough_overlap = len(overlap) >= 2 or (len(claim_tokens) == 1 and len(overlap) == 1)
        evidence = EvidenceExcerpt(
            status=EvidenceStatus.RELEVANT if enough_overlap else EvidenceStatus.WEAK_PARTIAL,
            excerpt=source.snippet,
            excerpt_source=(
                "demo_fixture" if origin == EvidenceOrigin.DEMO_FIXTURE else "search_provider_snippet"
            ),
        )
    ranked = RankedEvidenceSource(
        title=source.title,
        url=source.url,
        domain=domain,
        source_tier=tier,
        evidence=evidence,
        published_date=source.published_date,
        origin=origin,
    )
    relevance = len(overlap)
    available = int(source.snippet is not None)
    published = _published_day(source.published_date)
    recency = published.toordinal() if published else 0
    return ranked, relevance * 1_000_000 + available * 10_000 + recency


def rank_sources(
    sources: list[EvidenceSource],
    claim_text: str,
    origin: EvidenceOrigin = EvidenceOrigin.LIVE_SEARCH,
) -> list[RankedEvidenceSource]:
    """Rank by domain tier first, then token overlap, availability, date, and stable URL."""
    unique_by_url: dict[str, EvidenceSource] = {}
    for source in sources:
        canonical_url = _canonical_url(str(source.url))
        existing = unique_by_url.get(canonical_url)
        if existing is None or (
            source.snippet is not None
            and (existing.snippet is None or len(source.snippet) > len(existing.snippet))
        ):
            unique_by_url[canonical_url] = source

    ranked: list[tuple[RankedEvidenceSource, int]] = [
        _build_ranked_source(source, claim_text, origin)
        for source in unique_by_url.values()
    ]
    ranked.sort(
        key=lambda item: (
            _TIER_RANK[item[0].source_tier],
            -item[1],
            str(item[0].url).lower(),
        )
    )
    return [item[0] for item in ranked]
