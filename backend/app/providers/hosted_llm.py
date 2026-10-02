import json
import os
from typing import cast

import httpx
from pydantic import ValidationError

from app.providers.claim_extractor import ClaimExtractor
from app.providers.errors import ProviderConfigurationError, ProviderError
from app.schemas.analysis import ClaimDraft

_SYSTEM_PROMPT = """Extract only distinct atomic factual, financial, or promotional claims explicitly present in the supplied text.
Split compound statements into logically distinct claims without adding information.
Do not assess truth, support, contradiction, risk, or scam status. Do not give investment advice or predictions.
Do not invent claims. Return only a JSON object with a "claims" array; each item has "text" and "kind", where kind is factual, financial, or promotional.
If there are no extractable claims, return {"claims": []}."""


class InvalidProviderResponse(Exception):
    pass


class HostedLLMClaimExtractor:
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

    async def extract_claims(self, normalized_text: str) -> list[ClaimDraft]:
        if not self._api_key:
            raise ProviderConfigurationError("LLM_API_KEY is not configured.")

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
                            {"role": "user", "content": normalized_text},
                        ],
                    },
                )
                response.raise_for_status()
                provider_body = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            raise ProviderError("The hosted claim extraction provider failed.") from error

        try:
            message_content = provider_body["choices"][0]["message"]["content"]
            if not isinstance(message_content, str):
                raise InvalidProviderResponse("The provider response did not contain text.")
            extraction = json.loads(message_content)
            raw_claims = extraction["claims"]
            if not isinstance(raw_claims, list):
                raise InvalidProviderResponse("The provider claims value was not a list.")
            if set(extraction) != {"claims"}:
                raise InvalidProviderResponse("The provider returned unexpected fields.")
            return [ClaimDraft.model_validate(claim) for claim in cast(list[object], raw_claims)]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise InvalidProviderResponse("The provider returned malformed claim data.") from error
