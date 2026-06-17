from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptScore:
    score: int
    signals: dict[str, bool]


def score_transcript(transcript: str) -> TranscriptScore:
    text = transcript.lower()
    signals = {
        "budget": any(word in text for word in ("budget", "бюджет", "price", "цена")),
        "authority": any(word in text for word in ("decision", "approved", "director", "решение", "директор", "owner")),
        "need": any(word in text for word in ("need", "нужно", "problem", "проблем")),
        "timing": any(word in text for word in ("deadline", "срок", "week", "month", "месяц")),
        "next_step": any(word in text for word in ("next step", "следующий шаг", "meeting", "созвон")),
    }
    score = sum(20 for value in signals.values() if value)
    return TranscriptScore(score=score, signals=signals)
