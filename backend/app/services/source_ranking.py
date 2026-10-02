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
    "about", "also", "been", "being", "can", "could", "has", "have", "into",
    "may", "more", "most", "not", "should", "than", "that", "this", "these",
    "those", "will", "would",
}
_MAX_EXCERPT_CHARS = 2_000
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


def _page_sentences(raw_content: str) -> list[str]:
    text = raw_content.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r"<(script|style|nav|header|footer)\b[^>]*>.*?</\1>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+", "", text)
    fragments = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [
        sentence.strip(" \t\r\n#*_>`")
        for fragment in fragments
        if (sentence := re.sub(r"\s+", " ", fragment)).strip(" \t\r\n#*_>`")
    ]


def _extract_page_excerpt(
    claim_text: str,
    raw_content: str,
) -> tuple[str, EvidenceStatus, int] | None:
    claim_tokens = _tokens(claim_text)
    if not claim_tokens:
        return None

    candidates: list[tuple[tuple[float, float, int, int], str, int]] = []
    for index, sentence in enumerate(_page_sentences(raw_content)):
        sentence_tokens = _tokens(sentence)
        overlap = claim_tokens & sentence_tokens
        if not overlap:
            continue
        claim_coverage = len(overlap) / len(claim_tokens)
        sentence_coverage = len(overlap) / max(len(sentence_tokens), 1)
        score = (claim_coverage, sentence_coverage, len(overlap), -index)
        candidates.append((score, sentence, len(overlap)))

    if not candidates:
        return None

    _, passage, overlap_count = max(candidates, key=lambda candidate: candidate[0])
    required_overlap = (
        1 if len(claim_tokens) == 1 else max(2, (len(claim_tokens) + 3) // 4)
    )
    status = (
        EvidenceStatus.RELEVANT
        if overlap_count >= required_overlap
        else EvidenceStatus.WEAK_PARTIAL
    )
    excerpt = passage[:_MAX_EXCERPT_CHARS].rstrip()
    return excerpt, status, overlap_count


def _snippet_evidence(
    source: EvidenceSource,
    claim_text: str,
    origin: EvidenceOrigin,
) -> tuple[EvidenceExcerpt, int]:
    claim_tokens = _tokens(claim_text)
    content = " ".join((source.title, source.snippet or ""))
    overlap = claim_tokens & _tokens(content)
    excerpt_source = (
        "demo_fixture"
        if origin == EvidenceOrigin.DEMO_FIXTURE
        else "search_provider_snippet"
    )
    if source.snippet is None:
        return EvidenceExcerpt(status=EvidenceStatus.INACCESSIBLE), len(overlap)
    if not overlap:
        return (
            EvidenceExcerpt(
                status=EvidenceStatus.NO_RELEVANT,
                excerpt=source.snippet,
                excerpt_source=excerpt_source,
            ),
            0,
        )
    enough_overlap = len(overlap) >= 2 or (
        len(claim_tokens) == 1 and len(overlap) == 1
    )
    return (
        EvidenceExcerpt(
            status=(
                EvidenceStatus.RELEVANT
                if enough_overlap
                else EvidenceStatus.WEAK_PARTIAL
            ),
            excerpt=source.snippet,
            excerpt_source=excerpt_source,
        ),
        len(overlap),
    )


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

    page_excerpt = (
        _extract_page_excerpt(claim_text, source.raw_content)
        if origin == EvidenceOrigin.LIVE_SEARCH and source.raw_content
        else None
    )
    if page_excerpt is not None:
        excerpt, excerpt_status, relevance = page_excerpt
        evidence = EvidenceExcerpt(
            status=excerpt_status,
            excerpt=excerpt,
            excerpt_source="source_page_excerpt",
        )
    else:
        evidence, relevance = _snippet_evidence(source, claim_text, origin)
        if (
            origin == EvidenceOrigin.LIVE_SEARCH
            and source.raw_content
            and evidence.status == EvidenceStatus.INACCESSIBLE
        ):
            evidence = EvidenceExcerpt(status=EvidenceStatus.NO_RELEVANT)
    ranked = RankedEvidenceSource(
        title=source.title,
        url=source.url,
        domain=domain,
        source_tier=tier,
        evidence=evidence,
        published_date=source.published_date,
        origin=origin,
    )
    available = int(evidence.excerpt is not None)
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
        if existing is None:
            unique_by_url[canonical_url] = source
            continue
        raw_content = max(
            (existing.raw_content, source.raw_content),
            key=lambda content: len(content or ""),
        )
        snippet = max(
            (existing.snippet, source.snippet),
            key=lambda content: len(content or ""),
        )
        published_date = existing.published_date or source.published_date
        unique_by_url[canonical_url] = existing.model_copy(
            update={
                "raw_content": raw_content,
                "snippet": snippet,
                "published_date": published_date,
            }
        )

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
