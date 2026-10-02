import os
from typing import cast

import httpx
from pydantic import AnyHttpUrl, ValidationError

from app.providers.evidence_search import EvidenceSearchProvider
from app.providers.errors import ProviderConfigurationError, ProviderError
from app.schemas.analysis import EvidenceSource


class InvalidSearchResponse(Exception):
    pass


class TavilyEvidenceSearch:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("TAVILY_API_KEY")
        self._transport = transport

    async def search(self, query: str) -> list[EvidenceSource]:
        if not self._api_key:
            raise ProviderConfigurationError("TAVILY_API_KEY is not configured.")

        try:
            async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self._api_key,
                        "query": query,
                        "max_results": 3,
                        "search_depth": "basic",
                        "include_answer": False,
                        "include_raw_content": True,
                    },
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError("The evidence search provider failed.") from error

        try:
            raw_results = body["results"]
            if not isinstance(raw_results, list):
                raise InvalidSearchResponse("The provider results value was not a list.")

            sources: list[EvidenceSource] = []
            for result in raw_results[:3]:
                if not isinstance(result, dict):
                    raise InvalidSearchResponse("A provider result was not an object.")
                url = result.get("url")
                if not isinstance(url, str):
                    raise InvalidSearchResponse("A provider result had no URL.")
                sources.append(
                    EvidenceSource(
                        title=result.get("title"),
                        url=cast(AnyHttpUrl, url),
                        snippet=result.get("content") or None,
                        published_date=result.get("published_date"),
                        raw_content=(
                            result["raw_content"]
                            if isinstance(result.get("raw_content"), str)
                            else None
                        ),
                    )
                )
            return sources
        except (KeyError, TypeError, ValidationError) as error:
            raise InvalidSearchResponse("The evidence search provider returned malformed results.") from error
