from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError

from app.providers.ocr import OCRProvider
from app.schemas.analysis import (
    AnalysisRequest,
    CompleteAnalysisResponse,
    ScreenshotAnalysisResponse,
)
from app.services.complete_analysis import CompleteAnalysisService
from app.services.normalization import normalize_and_redact

MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024
MAX_SCREENSHOT_PIXELS = 20_000_000
MAX_OCR_TEXT_CHARS = 20_000
_MEDIA_TYPE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class InvalidScreenshot(ValueError):
    """Raised for invalid, unsupported, or oversized screenshot uploads."""


class UnsupportedScreenshotType(InvalidScreenshot):
    """Raised when the declared image type is not supported."""


class ScreenshotTooLarge(InvalidScreenshot):
    """Raised when an uploaded image exceeds the configured byte limit."""


def validate_screenshot(image: bytes, media_type: str) -> str:
    if len(image) > MAX_SCREENSHOT_BYTES:
        raise ScreenshotTooLarge("Screenshot exceeds the 10 MiB size limit.")
    expected_format = _MEDIA_TYPE_FORMATS.get(media_type.lower())
    if expected_format is None:
        raise UnsupportedScreenshotType("Upload a PNG, JPEG, or WebP image.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image)) as decoded:
                actual_format = decoded.format
                width, height = decoded.size
                decoded.verify()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        raise InvalidScreenshot("The uploaded file is not a valid supported image.") from error

    if actual_format != expected_format:
        raise UnsupportedScreenshotType(
            "Image content does not match its declared media type."
        )
    if width <= 0 or height <= 0 or width * height > MAX_SCREENSHOT_PIXELS:
        raise InvalidScreenshot("Image dimensions exceed the supported limit.")
    return media_type.lower()


class ScreenshotAnalysisService:
    def __init__(
        self,
        ocr_provider: OCRProvider,
        complete_analysis_service: CompleteAnalysisService,
    ) -> None:
        self._ocr_provider = ocr_provider
        self._complete_analysis_service = complete_analysis_service

    async def analyze(
        self,
        image: bytes,
        media_type: str,
        consent: bool,
    ) -> ScreenshotAnalysisResponse:
        if not consent:
            raise PermissionError("Explicit consent is required before image processing.")
        validated_media_type = validate_screenshot(image, media_type)
        extracted_text = await self._ocr_provider.extract_text(
            image,
            validated_media_type,
        )
        if not isinstance(extracted_text, str):
            raise InvalidScreenshot("The OCR provider returned unusable text.")
        if len(extracted_text) > MAX_OCR_TEXT_CHARS:
            raise InvalidScreenshot("OCR text exceeds the 20,000-character analysis limit.")
        redacted_text = normalize_and_redact(extracted_text)
        if not redacted_text:
            raise InvalidScreenshot("No readable text was detected in the screenshot.")

        analysis: CompleteAnalysisResponse = await self._complete_analysis_service.analyze(
            AnalysisRequest(content=redacted_text, consent=True)
        )
        return ScreenshotAnalysisResponse(
            input_type="screenshot",
            ocr_text=redacted_text,
            content_type=validated_media_type,
            size_bytes=len(image),
            analysis=analysis,
        )
