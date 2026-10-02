import json
import os
import re
from typing import cast

import httpx
from pydantic import ValidationError

from app.providers.errors import ProviderConfigurationError, ProviderError
from app.schemas.analysis import Claim, ClaimAssessment, RankedEvidenceSource

_SYSTEM_PROMPT = """You assess only the relationship between one supplied claim and its supplied evidence package.
Use no outside knowledge, browsing, or the original input. The package includes source tier, excerpt, and excerpt provenance.
A source's tier is relevant context, not proof; relevance to this claim is required.
Preserve conflicting evidence, including lower-tier conflicts. Search-provider snippets and demo fixtures are not verified page content and cannot establish support or contradiction.
Choose exactly one state: Supported, Contradicted, Unverified, or Needs more evidence.
Supported/Contradicted require direct relevant evidence in a source_page_excerpt and evidence IDs from this package.
No evidence or irrelevant evidence must be Unverified. Weak, inaccessible, conflicting, or incomplete evidence should be Needs more evidence or Unverified as appropriate; never infer Contradicted from missing evidence.
Rationale and uncertainty must be concise and grounded only in supplied excerpts. Do not invent facts, titles, URLs, excerpts, or sources. Refer to sources only by evidence ID; do not repeat their URL or title.
Do not give investment advice or make recommendations. Do not include numeric truth-confidence scores.
Return only JSON with exactly: assessment, rationale, evidence_ids, uncertainty."""

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_NUMERIC_CONFIDENCE = re.compile(
    r"\bconfidence\b[^.\n]{0,30}\b\d+(?:\.\d+)?\s*%?|\b\d+(?:\.\d+)?\s*%\s*confidence\b",
    re.IGNORECASE,
)


class InvalidAssessmentResponse(Exception):
    pass


class HostedLLMAssessor:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY")
        self._base_url = (
            base_url if base_url is not None else os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self._model = model if model is not None else os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._transport = transport

    async def assess(
        self,
        claim: Claim,
        evidence_package: list[RankedEvidenceSource],
    ) -> ClaimAssessment:
        if not self._api_key:
            raise ProviderConfigurationError("LLM_API_KEY is not configured.")

        assessment_input = {
            "claim": {"text": claim.text, "kind": claim.kind.value},
            "evidence_package": [
                source.model_dump(mode="json", exclude={"evidence_id"}, exclude_none=True)
                | {"evidence_id": str(source.evidence_id)}
                for source in evidence_package
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": json.dumps(assessment_input, ensure_ascii=False),
                            },
                        ],
                    },
                )
                response.raise_for_status()
                provider_body = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            raise ProviderError("The hosted assessment provider failed.") from error

        try:
            content = provider_body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise InvalidAssessmentResponse("The provider response did not contain text.")
            raw_assessment = json.loads(content)
            if not isinstance(raw_assessment, dict) or set(raw_assessment) != {
                "assessment",
                "rationale",
                "evidence_ids",
                "uncertainty",
            }:
                raise InvalidAssessmentResponse("The provider returned unexpected assessment fields.")
            assessment = ClaimAssessment.model_validate(raw_assessment)
            if any(
                pattern.search(text)
                for pattern in (_URL, _NUMERIC_CONFIDENCE)
                for text in (assessment.rationale, assessment.uncertainty)
            ):
                raise InvalidAssessmentResponse(
                    "The provider returned a URL or numeric confidence score."
                )
            return assessment
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise InvalidAssessmentResponse("The provider returned malformed assessment data.") from error
