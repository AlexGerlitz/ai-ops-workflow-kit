from app.schemas import CallAnalysisOut, RetrievedContext
from app.scoring import TranscriptScore


SIGNAL_LABELS = {
    "budget": "budget",
    "authority": "decision authority",
    "need": "business need",
    "timing": "timeline",
    "next_step": "dated next step",
}


def build_call_analysis(
    *,
    call_id: str,
    customer_id: str,
    transcript: str,
    transcript_score: TranscriptScore,
    knowledge_context: list[RetrievedContext],
) -> CallAnalysisOut:
    missing_signals = [
        label for key, label in SIGNAL_LABELS.items() if not transcript_score.signals.get(key)
    ]
    objections = detect_objections(transcript)
    risk_level = classify_risk(transcript_score.score, objections, missing_signals)
    next_action = build_next_action(missing_signals, risk_level)
    summary = summarize_transcript(transcript)
    follow_up_draft = build_follow_up_draft(
        summary=summary,
        score=transcript_score.score,
        missing_signals=missing_signals,
        objections=objections,
        next_action=next_action,
        knowledge_context=knowledge_context,
    )
    crm_update = build_crm_update(
        call_id=call_id,
        customer_id=customer_id,
        score=transcript_score.score,
        risk_level=risk_level,
        summary=summary,
        objections=objections,
        next_action=next_action,
        missing_signals=missing_signals,
    )
    return CallAnalysisOut(
        summary=summary,
        risk_level=risk_level,
        missing_signals=missing_signals,
        objections=objections,
        next_action=next_action,
        follow_up_draft=follow_up_draft,
        crm_update=crm_update,
        knowledge_context=knowledge_context,
    )


def summarize_transcript(transcript: str) -> str:
    normalized = " ".join(transcript.strip().split())
    if len(normalized) <= 260:
        return normalized
    sentence_end = normalized.find(". ")
    if 80 <= sentence_end <= 260:
        return normalized[: sentence_end + 1]
    return normalized[:257] + "..."


def detect_objections(transcript: str) -> list[str]:
    text = transcript.lower()
    objections: list[str] = []
    if any(word in text for word in ("expensive", "price", "дорого", "цена", "стоимость")):
        objections.append("price sensitivity")
    if any(word in text for word in ("later", "not now", "позже", "не сейчас", "подумаю")):
        objections.append("delayed decision")
    if any(word in text for word in ("compare", "competitor", "конкурент", "сравнить")):
        objections.append("competitor comparison")
    if any(word in text for word in ("unclear", "непонятно", "сомнева", "doubt")):
        objections.append("unclear value")
    return objections or ["no explicit objection detected"]


def classify_risk(score: int, objections: list[str], missing_signals: list[str]) -> str:
    explicit_objections = [item for item in objections if item != "no explicit objection detected"]
    if score >= 80 and not explicit_objections:
        return "low"
    if score >= 60 and len(missing_signals) <= 2:
        return "medium"
    return "high"


def build_next_action(missing_signals: list[str], risk_level: str) -> str:
    if missing_signals:
        missing = ", ".join(missing_signals[:3])
        return f"Confirm {missing}, then agree on a dated next step."
    if risk_level == "low":
        return "Send recap, confirm terms, and move the lead to the next CRM stage."
    return "Send a concise recap and ask one direct qualification question."


def build_follow_up_draft(
    *,
    summary: str,
    score: int,
    missing_signals: list[str],
    objections: list[str],
    next_action: str,
    knowledge_context: list[RetrievedContext],
) -> str:
    context_line = ""
    if knowledge_context:
        top = knowledge_context[0]
        context_line = f"\nRelevant playbook context: {top.text[:220]}"
    missing_line = ", ".join(missing_signals) if missing_signals else "none"
    objection_line = ", ".join(objections)
    return (
        f"Lead score: {score}/100.\n"
        f"Call summary: {summary}\n"
        f"Objections: {objection_line}.\n"
        f"Missing qualification: {missing_line}.\n"
        f"Recommended next action: {next_action.rstrip('.')}.{context_line}"
    )


def build_crm_update(
    *,
    call_id: str,
    customer_id: str,
    score: int,
    risk_level: str,
    summary: str,
    objections: list[str],
    next_action: str,
    missing_signals: list[str],
) -> dict[str, object]:
    stage = "qualified" if score >= 80 else "needs_manager_review" if risk_level == "high" else "in_progress"
    return {
        "adapter": "bitrix24.mock",
        "operation": "upsert_lead_follow_up",
        "customer_id": customer_id,
        "call_id": call_id,
        "lead_score": score,
        "risk_level": risk_level,
        "target_stage": stage,
        "fields": {
            "AI Lead Score": score,
            "AI Risk Level": risk_level,
            "AI Missing Signals": missing_signals,
        },
        "comment": summary,
        "task": {
            "title": f"Follow up after call {call_id}",
            "description": next_action,
            "priority": "high" if risk_level == "high" else "normal",
        },
        "objections": objections,
    }
