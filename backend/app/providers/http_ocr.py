import json
from urllib.parse import urlsplit

import httpx

from app.providers.ocr import OCRConfigurationError, OCRProviderError


class InvalidOCRResponse(OCRProviderError):
    """Raised when the configured OCR endpoint returns an invalid response."""


class HTTPJSONOCRProvider:
    """Vendor-neutral adapter for an HTTP OCR endpoint accepting multipart image data."""

    def __init__(
        self,
        endpoint: str | None,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._transport = transport

    async def extract_text(self, image: bytes, media_type: str) -> str:
        if not self._endpoint:
            raise OCRConfigurationError("OCR_API_URL is not configured.")
        try:
            parsed_endpoint = urlsplit(self._endpoint)
        except ValueError as error:
            raise OCRConfigurationError(
                "OCR_API_URL must be a valid HTTP(S) endpoint."
            ) from error
        if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
            raise OCRConfigurationError("OCR_API_URL must be an HTTP(S) endpoint.")

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers=headers,
                    files={"file": ("screenshot", image, media_type)},
                )
                response.raise_for_status()
        except httpx.InvalidURL as error:
            raise OCRConfigurationError(
                "OCR_API_URL must be a valid HTTP(S) endpoint."
            ) from error
        except httpx.HTTPError as error:
            raise OCRProviderError("The OCR provider request failed.") from error

        try:
            body = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise InvalidOCRResponse(
                "The OCR provider returned malformed output."
            ) from error

        if not isinstance(body, dict) or not isinstance(body.get("text"), str):
            raise InvalidOCRResponse("The OCR provider returned malformed output.")
        return body["text"]
