from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StrictBool


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=20_000)
    consent: StrictBool = False


class ClaimKind(str, Enum):
    FACTUAL = "factual"
    FINANCIAL = "financial"
    PROMOTIONAL = "promotional"


class ClaimDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2_000)
    kind: ClaimKind


class Claim(ClaimDraft):
    id: UUID


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    status: Literal["completed"]
    claims: list[Claim]


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[Claim] = Field(min_length=1, max_length=10)
    consent: StrictBool = False


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    url: AnyHttpUrl
    snippet: str | None = Field(default=None, max_length=5_000)
    published_date: str | None = Field(default=None, max_length=100)
    raw_content: str | None = Field(default=None, exclude=True, repr=False)


class SourceTier(str, Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    RELEVANT = "relevant_evidence_found"
    WEAK_PARTIAL = "weak_or_partial_evidence"
    INACCESSIBLE = "source_inaccessible"
    NO_RELEVANT = "no_relevant_evidence_found"


class EvidenceOrigin(str, Enum):
    LIVE_SEARCH = "live_search"
    DEMO_FIXTURE = "demo_fixture"


class EvidenceExcerpt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EvidenceStatus
    excerpt: str | None = Field(default=None, max_length=5_000)
    excerpt_source: Literal[
        "search_provider_snippet",
        "demo_fixture",
        "source_page_excerpt",
    ] | None = None


class RankedEvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1, max_length=500)
    url: AnyHttpUrl
    domain: str = Field(min_length=1, max_length=253)
    source_tier: SourceTier
    evidence: EvidenceExcerpt
    published_date: str | None = Field(default=None, max_length=100)
    origin: EvidenceOrigin


class ClaimEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: UUID
    sources: list[RankedEvidenceSource]


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ClaimEvidence]


class AssessmentState(str, Enum):
    SUPPORTED = "Supported"
    CONTRADICTED = "Contradicted"
    UNVERIFIED = "Unverified"
    NEEDS_MORE_EVIDENCE = "Needs more evidence"


class ManipulationSignalType(str, Enum):
    GUARANTEED_RETURN = "GUARANTEED_RETURN"
    URGENCY = "URGENCY"
    SCARCITY_FOMO = "SCARCITY_FOMO"
    AUTHORITY_CLAIM = "AUTHORITY_CLAIM"
    INSIDER_SECRET_LANGUAGE = "INSIDER_SECRET_LANGUAGE"
    EXAGGERATED_CERTAINTY = "EXAGGERATED_CERTAINTY"
    TESTIMONIAL_SOCIAL_PROOF_PRESSURE = "TESTIMONIAL_SOCIAL_PROOF_PRESSURE"
    UNSUPPORTED_STATISTICAL_CLAIM = "UNSUPPORTED_STATISTICAL_CLAIM"


class ManipulationSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: UUID
    signal_type: ManipulationSignalType
    matched_text: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=500)


class ClaimAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: AssessmentState
    rationale: str = Field(min_length=1, max_length=2_000)
    evidence_ids: list[UUID] = Field(max_length=10)
    uncertainty: str = Field(min_length=1, max_length=2_000)


class AssessedClaimResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: Claim
    assessment: ClaimAssessment
    evidence: list[RankedEvidenceSource]
    manipulation_signals: list[ManipulationSignal]


class CompleteAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    status: Literal["completed"]
    manipulation_signals: list[ManipulationSignal]
    results: list[AssessedClaimResult]


class ScreenshotAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_type: Literal["screenshot"]
    ocr_text: str = Field(min_length=1, max_length=20_000)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(ge=1, le=10 * 1024 * 1024)
    analysis: CompleteAnalysisResponse
