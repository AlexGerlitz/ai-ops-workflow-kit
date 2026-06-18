DEMO_SALES_PLAYBOOK = """
# Sales Playbook

Discovery calls should confirm budget, decision authority, business need, timeline, and a dated next step.
AI-generated follow-ups must be reviewed by a human before CRM updates are sent.
High-confidence leads can move to the qualified stage after approval.
Risky calls should create a manager task with the missing qualification signals.
"""

DEMO_TRANSCRIPT = {
    "call_id": "CALL-LIVE-DEMO-1",
    "customer_id": "LEAD-SALEOPS-42",
    "transcript": (
        "The client said the price may be expensive, but the operations director approved the budget. "
        "They need the workflow this month because managers lose follow-up context after calls. "
        "The next step is a short implementation call tomorrow with the decision maker."
    ),
    "metadata": {"source": "public-live-demo", "manager": "sales-demo"},
}
