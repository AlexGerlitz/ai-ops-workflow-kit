DEMO_SALES_PLAYBOOK = """
# Sales Playbook

Discovery calls should confirm budget, decision authority, business need, timeline, and a dated next step.
AI-assisted follow-ups must be reviewed by a human before CRM updates are sent.
High-confidence leads can move to the qualified stage after approval.
Risky calls should create a manager task with the missing qualification signals.
"""

DEMO_TRANSCRIPT = {
    "call_id": "CALL-LIVE-DEMO-1",
    "customer_id": "LEAD-SALEOPS-42",
    "transcript": (
        "The client said the price may be expensive, but the operations director approved the budget. "
        "They need the workflow this month because managers lose follow-up context after calls. "
        "The next step is a short implementation call tomorrow with the decision maker. "
        "Send the recap to maria.petrov@example.com and confirm by phone at +41 44 555 12 34."
    ),
    "metadata": {"source": "public-live-demo", "manager": "sales-demo"},
}

DEMO_CALL_AUDIO = {
    "call_id": "CALL-LIVE-DEMO-1",
    "customer_id": "LEAD-SALEOPS-42",
    "audio_uri": "gdrive://demo-call-audio.mp3",
    "audio_mime_type": "audio/mpeg",
    "duration_seconds": 186,
    "language": "en",
    "provider": "local_stub",
    "transcript_hint": (
        "Manager: The client said the price may be expensive, but the operations director "
        "approved the budget.\n"
        "Client: We need the workflow this month because managers lose follow-up context "
        "after calls.\n"
        "Manager: The next step is a short implementation call tomorrow with the decision maker.\n"
        "Client: Send the recap to maria.petrov@example.com and confirm by phone at +41 44 555 12 34."
    ),
    "metadata": {
        "source": "public-live-demo",
        "manager": "sales-demo",
        "telephony_provider": "demo-recorder",
    },
}

DEMO_RAG_EVAL_QUESTIONS = [
    {
        "question": "What should discovery calls confirm?",
        "expected_source": "gdrive://demo-sales-playbook",
        "required_terms": ["budget", "decision authority", "timeline", "dated next step"],
        "top_k": 5,
        "score_floor": 0.05,
    },
    {
        "question": "What must happen before CRM updates are sent?",
        "expected_source": "gdrive://demo-sales-playbook",
        "required_terms": ["reviewed by a human", "CRM updates"],
        "top_k": 5,
        "score_floor": 0.05,
    },
]
