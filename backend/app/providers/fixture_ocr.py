from app.providers.ocr import OCRProvider

CANONICAL_DEMO_TEXT = (
    "SEBI approved XYZ investment plan.\n"
    "Guaranteed 30% return.\n"
    "Only 200 slots remaining.\n"
    "Join NOW!"
)


class FixtureOCRProvider:
    """Deterministic OCR provider for tests; never selected by production configuration."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[tuple[bytes, str]] = []

    async def extract_text(self, image: bytes, media_type: str) -> str:
        self.calls.append((image, media_type))
        return self._text


class CanonicalDemoOCRProvider(FixtureOCRProvider):
    """Fixed canonical text for an explicitly enabled local demo mode."""

    def __init__(self) -> None:
        super().__init__(CANONICAL_DEMO_TEXT)
