from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import PrivacyRedactionOut, TranscriptionOut


EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)",
)
PAYMENT_CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE)


@dataclass(frozen=True)
class RedactedText:
    text: str
    counts: dict[str, int]

    @property
    def redacted(self) -> bool:
        return any(count > 0 for count in self.counts.values())

    def evidence(self) -> PrivacyRedactionOut:
        return PrivacyRedactionOut(
            enabled=True,
            redacted=self.redacted,
            categories=[key for key, value in self.counts.items() if value > 0],
            replacement_counts={key: value for key, value in self.counts.items() if value > 0},
            raw_text_stored=False,
            safe_logging=True,
            notes=(
                "Transcript PII is redacted before RAG ingestion, approval context, "
                "CRM handoff payloads, demo output, and public logs."
            ),
        )


def redact_text(text: str) -> RedactedText:
    redacted = text
    counts: dict[str, int] = {}

    for category, pattern, replacement in (
        ("email", EMAIL_PATTERN, "[redacted-email]"),
        ("iban", IBAN_PATTERN, "[redacted-iban]"),
        ("payment_card", PAYMENT_CARD_PATTERN, "[redacted-payment-card]"),
        ("phone", PHONE_PATTERN, "[redacted-phone]"),
    ):
        redacted, count = pattern.subn(replacement, redacted)
        counts[category] = count

    return RedactedText(text=redacted, counts=counts)


def redact_transcription(transcription: TranscriptionOut) -> TranscriptionOut:
    redacted_transcript = redact_text(transcription.transcript)
    redacted_segments = [
        segment.model_copy(update={"text": redact_text(segment.text).text})
        for segment in transcription.segments
    ]
    request_contract = {
        **transcription.request_contract,
        "privacy": redacted_transcript.evidence().model_dump(mode="json"),
    }
    return transcription.model_copy(
        update={
            "transcript": redacted_transcript.text,
            "segments": redacted_segments,
            "request_contract": request_contract,
        }
    )
