import re

import pytest

from app.schemas.analysis import ManipulationSignalType
from app.services.manipulation import detect_manipulation_signals


def _types(text: str) -> set[ManipulationSignalType]:
    return {signal.signal_type for signal in detect_manipulation_signals(text)}


@pytest.mark.parametrize(
    ("text", "signal_type"),
    [
        ("Guaranteed 30% return", ManipulationSignalType.GUARANTEED_RETURN),
        ("Assured profits", ManipulationSignalType.GUARANTEED_RETURN),
        ("Fixed return", ManipulationSignalType.GUARANTEED_RETURN),
        ("Risk-free returns", ManipulationSignalType.GUARANTEED_RETURN),
        ("No-loss investment", ManipulationSignalType.GUARANTEED_RETURN),
        ("Act now", ManipulationSignalType.URGENCY),
        ("Join now!", ManipulationSignalType.URGENCY),
        ("Available immediately", ManipulationSignalType.URGENCY),
        ("Today only", ManipulationSignalType.URGENCY),
        ("Don't wait", ManipulationSignalType.URGENCY),
        ("Limited slots", ManipulationSignalType.SCARCITY_FOMO),
        ("Only 200 slots remaining", ManipulationSignalType.SCARCITY_FOMO),
        ("Last chance", ManipulationSignalType.SCARCITY_FOMO),
        ("Limited opportunity", ManipulationSignalType.SCARCITY_FOMO),
        ("Exclusive opportunity", ManipulationSignalType.SCARCITY_FOMO),
        ("SEBI approved", ManipulationSignalType.AUTHORITY_CLAIM),
        ("RBI approved", ManipulationSignalType.AUTHORITY_CLAIM),
        ("Approved by SEBI", ManipulationSignalType.AUTHORITY_CLAIM),
        ("Government approved", ManipulationSignalType.AUTHORITY_CLAIM),
        ("Official regulator approval", ManipulationSignalType.AUTHORITY_CLAIM),
        ("Insider tip", ManipulationSignalType.INSIDER_SECRET_LANGUAGE),
        ("Secret strategy", ManipulationSignalType.INSIDER_SECRET_LANGUAGE),
        ("Before everyone knows", ManipulationSignalType.INSIDER_SECRET_LANGUAGE),
        ("Confidential opportunity", ManipulationSignalType.INSIDER_SECRET_LANGUAGE),
        ("100% safe", ManipulationSignalType.EXAGGERATED_CERTAINTY),
        ("Cannot lose", ManipulationSignalType.EXAGGERATED_CERTAINTY),
        ("Certain profit", ManipulationSignalType.EXAGGERATED_CERTAINTY),
        ("Guaranteed success", ManipulationSignalType.EXAGGERATED_CERTAINTY),
        ("Zero risk", ManipulationSignalType.EXAGGERATED_CERTAINTY),
        (
            "I invested yesterday and earned ₹50,000",
            ManipulationSignalType.TESTIMONIAL_SOCIAL_PROOF_PRESSURE,
        ),
        (
            "5,000 investors have already joined",
            ManipulationSignalType.TESTIMONIAL_SOCIAL_PROOF_PRESSURE,
        ),
        ("30% annual returns", ManipulationSignalType.UNSUPPORTED_STATISTICAL_CLAIM),
        ("Returns of 12.5%", ManipulationSignalType.UNSUPPORTED_STATISTICAL_CLAIM),
        (
            "Earned ₹50,000 in just 7 days",
            ManipulationSignalType.UNSUPPORTED_STATISTICAL_CLAIM,
        ),
    ],
)
def test_detects_each_initial_signal_category(
    text: str,
    signal_type: ManipulationSignalType,
) -> None:
    assert signal_type in _types(text)


def test_is_case_insensitive_and_tolerates_punctuation_variations() -> None:
    signals = detect_manipulation_signals(
        "GUARANTEED—30% RETURN!!! Join... NOW! Only 200 slots remaining."
    )

    assert ManipulationSignalType.GUARANTEED_RETURN in {
        signal.signal_type for signal in signals
    }
    assert ManipulationSignalType.URGENCY in {signal.signal_type for signal in signals}
    assert ManipulationSignalType.SCARCITY_FOMO in {
        signal.signal_type for signal in signals
    }
    assert all(signal.matched_text for signal in signals)


def test_detects_multiple_distinct_signals_in_one_message() -> None:
    signals = detect_manipulation_signals(
        "SEBI approved! Guaranteed 30% return. Only 200 slots remaining. Join NOW!"
    )
    types = {signal.signal_type for signal in signals}

    assert {
        ManipulationSignalType.AUTHORITY_CLAIM,
        ManipulationSignalType.GUARANTEED_RETURN,
        ManipulationSignalType.UNSUPPORTED_STATISTICAL_CLAIM,
        ManipulationSignalType.SCARCITY_FOMO,
        ManipulationSignalType.URGENCY,
    }.issubset(types)
    assert len({signal.signal_id for signal in signals}) == len(signals)


def test_educational_discussion_does_not_trigger_claim_like_signals() -> None:
    signals = detect_manipulation_signals(
        "SEBI's investor education page discusses guaranteed returns."
    )

    assert ManipulationSignalType.GUARANTEED_RETURN not in {
        signal.signal_type for signal in signals
    }
    assert ManipulationSignalType.AUTHORITY_CLAIM not in {
        signal.signal_type for signal in signals
    }


def test_signal_explanation_is_neutral_and_has_no_numeric_risk_score() -> None:
    signals = detect_manipulation_signals("Guaranteed 30% return — join now.")

    assert signals
    assert all("scam" not in signal.explanation.lower() for signal in signals)
    assert all(
        not re.search(r"\b(?:risk|scam)\s+score\b|\b\d+\s*%\s*(?:risk|scam)\b", signal.explanation, re.I)
        for signal in signals
    )
    assert all(set(signal.model_dump()) == {
        "signal_id",
        "signal_type",
        "matched_text",
        "explanation",
    } for signal in signals)


def test_signal_detection_is_deterministic() -> None:
    text = "Approved by SEBI—last chance, don't wait."

    assert detect_manipulation_signals(text) == detect_manipulation_signals(text)
