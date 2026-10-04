from typing import Protocol


class OCRProviderError(Exception):
    """Raised when an OCR provider fails or returns unusable output."""


class OCRConfigurationError(OCRProviderError):
    """Raised when no production OCR endpoint is configured."""


class OCRProvider(Protocol):
    async def extract_text(self, image: bytes, media_type: str) -> str:
        """Extract text from an image without storing it."""
