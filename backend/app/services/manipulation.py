import re
from uuid import NAMESPACE_URL, uuid5

from app.schemas.analysis import ManipulationSignal, ManipulationSignalType


class _Rule:
    def __init__(
        self,
        signal_type: ManipulationSignalType,
        patterns: tuple[str, ...],
        explanation: str,
    ) -> None:
        self.signal_type = signal_type
        self.patterns = tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
        self.explanation = explanation


_EDUCATIONAL_CONTEXT = re.compile(
    r"\b(?:discuss(?:es|ed|ing)?|explain(?:s|ed|ing)?|warn(?:s|ed|ing)?|"
    r"educat(?:e|es|ed|ing)|describe(?:s|d|ing)?|avoid|beware of)\b",
    re.IGNORECASE,
)
_RULES = (
    _Rule(
        ManipulationSignalType.GUARANTEED_RETURN,
        (
            r"\b(?:guaranteed?|assured?)[\s.!?,;:—–-]+"
            r"(?:\d+(?:\.\d+)?\s*%?[\s.!?,;:—–-]+)?"
            r"(?:returns?|profits?|gains?)\b",
            r"\b(?:fixed|risk[\s-]?free|no[\s-]?loss)[\s.!?,;:—–-]+"
            r"(?:\d+(?:\.\d+)?\s*%?[\s.!?,;:—–-]+)?"
            r"(?:returns?|profits?|investment)\b",
        ),
        "This wording promises a return or profit; the signal does not assess whether it is true.",
    ),
    _Rule(
        ManipulationSignalType.URGENCY,
        (
            r"\bact[\s.!?,;:—–-]+now\b",
            r"\bjoin[\s.!?,;:—–-]+now\b",
            r"\bimmediately\b",
            r"\btoday[\s-]+only\b",
            r"\bdon['’]?t\s+wait\b",
            r"\blimited[\s-]+time\b",
        ),
        "This wording pressures the reader to act quickly.",
    ),
    _Rule(
        ManipulationSignalType.SCARCITY_FOMO,
        (
            r"\blimited\s+(?:slots?|spots?|places?|opportunit(?:y|ies))\b",
            r"\bonly\s+\d[\d,]*(?:\s+\w+){0,3}\s+remaining\b",
            r"\blast\s+chance\b",
            r"\bexclusive\s+opportunit(?:y|ies)\b",
        ),
        "This wording emphasizes scarcity or fear of missing out.",
    ),
    _Rule(
        ManipulationSignalType.AUTHORITY_CLAIM,
        (
            r"\b(?:SEBI|RBI|NSDL|NSE|BSE|government)[\s.!?,;:—–-]+approved\b",
            r"\bapproved\s+by[\s.!?,;:—–-]+(?:the[\s.!?,;:—–-]+)?"
            r"(?:SEBI|RBI|NSDL|NSE|BSE|government)\b",
            r"\b(?:official\s+)?regulator\s+approval\b",
            r"\bgovernment[\s-]+approved\b",
        ),
        "This wording claims regulatory or government approval; the signal does not verify that claim.",
    ),
    _Rule(
        ManipulationSignalType.INSIDER_SECRET_LANGUAGE,
        (
            r"\binsider[\s.!?,;:—–-]+(?:tip|information|secret|knowledge)\b",
            r"\bsecret[\s.!?,;:—–-]+(?:strategy|tip|opportunity|information)\b",
            r"\bbefore[\s.!?,;:—–-]+everyone[\s.!?,;:—–-]+knows\b",
            r"\bconfidential[\s.!?,;:—–-]+opportunit(?:y|ies)\b",
        ),
        "This wording suggests privileged or secret access.",
    ),
    _Rule(
        ManipulationSignalType.EXAGGERATED_CERTAINTY,
        (
            r"\b100\s*%\s+safe\b",
            r"\bcannot\s+lose\b",
            r"\bcan['’]?t\s+lose\b",
            r"\bcertain\s+profit\b",
            r"\bguaranteed\s+success\b",
            r"\bzero[\s-]+risk\b",
        ),
        "This wording presents an absolute safety or success claim.",
    ),
    _Rule(
        ManipulationSignalType.TESTIMONIAL_SOCIAL_PROOF_PRESSURE,
        (
            r"\bi\s+(?:invested|joined|tried)\b.{0,50}\b(?:earned|made|gained)\b",
            r"\bi\s+(?:earned|made|gained)\b.{0,50}\b(?:investing|trading|this\s+plan)\b",
            r"\b\d[\d,]*\s+(?:investors?|members?|people)\s+"
            r"(?:have\s+)?(?:already\s+)?(?:joined|earned|made|profited)\b",
            r"\b(?:everyone|thousands\s+of\s+(?:investors?|people))\s+"
            r"(?:is|are|has|have)\s+(?:joining|earning|profiting)\b",
            r"\bjoin\s+(?:the\s+)?(?:thousands|millions)\b",
        ),
        "This wording uses testimonials or popularity to influence the reader.",
    ),
    _Rule(
        ManipulationSignalType.UNSUPPORTED_STATISTICAL_CLAIM,
        (
            r"\b\d+(?:\.\d+)?\s*%\s+(?:annual(?:ized)?\s+)?"
            r"(?:returns?|profits?|gains?)\b",
            r"\b(?:returns?|profits?|gains?)\s+(?:of\s+)?"
            r"\d+(?:\.\d+)?\s*%(?:\s+(?:annual(?:ized)?|per\s+year))?(?!\w)",
            r"\b(?:earned|made|gained)\s+(?:₹|rs\.?\s*)?\d[\d,]*(?:\.\d+)?\s*"
            r"(?:in|within|per)\s+(?:just\s+)?\d+\s+(?:days?|weeks?|months?)\b",
        ),
        "This wording makes a specific promotional number claim without showing its context.",
    ),
)


def _is_educational_mention(text: str, start: int, end: int) -> bool:
    sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
    sentence_end_candidates = [
        index for marker in ".!?" if (index := text.find(marker, end)) != -1
    ]
    sentence_end = min(sentence_end_candidates, default=len(text))
    sentence = text[sentence_start:sentence_end]
    match_start = start - sentence_start
    prefix = sentence[:match_start]
    return bool(_EDUCATIONAL_CONTEXT.search(prefix)) and bool(
        re.search(r"\b(?:page|article|material|guide|resource|risks?|claims?)\b", sentence, re.I)
    )


def detect_manipulation_signals(text: str) -> list[ManipulationSignal]:
    """Return stable, inspectable phrase matches; this does not evaluate claim truth."""
    matches: dict[tuple[int, int, ManipulationSignalType], ManipulationSignal] = {}
    for rule in _RULES:
        for pattern in rule.patterns:
            for match in pattern.finditer(text):
                if (
                    rule.signal_type
                    in {
                        ManipulationSignalType.GUARANTEED_RETURN,
                        ManipulationSignalType.AUTHORITY_CLAIM,
                    }
                    and _is_educational_mention(text, match.start(), match.end())
                ):
                    continue
                matched_text = match.group(0)
                key = (match.start(), match.end(), rule.signal_type)
                signal_id = uuid5(
                    NAMESPACE_URL,
                    f"nirnay:manipulation:{rule.signal_type.value}:{match.start()}:{match.end()}:{matched_text.casefold()}",
                )
                matches[key] = ManipulationSignal(
                    signal_id=signal_id,
                    signal_type=rule.signal_type,
                    matched_text=matched_text,
                    explanation=rule.explanation,
                )
    return [
        signal
        for _, signal in sorted(
            matches.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2].value),
        )
    ]
