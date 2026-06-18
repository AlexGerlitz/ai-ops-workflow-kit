# Offer Demo

This is the fast reviewer path for the project.

The demo proves an end-to-end AI workflow automation scenario:

1. ingest a sales playbook into the RAG store;
2. query the knowledge base with source context;
3. accept a call transcript through the n8n-facing webhook;
4. score the lead and build a structured call analysis;
5. create a human approval item for the follow-up draft;
6. approve the item;
7. queue a mock Bitrix24 CRM handoff event.

The point is not to show a prompt wrapper. The point is to show the production
boundary: n8n routes events, while the backend owns retrieval, scoring, state,
approval transitions, and integration contracts.

## One-Command Local Run

```bash
python -m pip install -r requirements.txt
python scripts/run_offer_demo.py
```

The script uses in-memory storage so a reviewer can run it without Docker or API keys.
Docker/PostgreSQL mode is still available through `docker compose up --build`.

## Expected Shape

The output contains these sections:

| Section | What it proves |
| --- | --- |
| `runtime` | API booted and reported the active storage mode. |
| `ingestion` | Sales playbook was chunked and stored. |
| `rag_context_sources` | Retrieval returned explicit source context. |
| `call_analysis` | Transcript was scored and converted into structured business action. |
| `approval` | Human-in-the-loop state transition happened before CRM handoff. |
| `crm_handoff` | A mock Bitrix24 adapter event was queued after approval. |

Example high-level result:

```json
{
  "call_analysis": {
    "score": 100,
    "risk_level": "medium",
    "objections": ["price sensitivity"],
    "next_action": "Send a concise recap and ask one direct qualification question."
  },
  "approval": {
    "status": "approved",
    "reviewer": "sales-lead"
  },
  "crm_handoff": {
    "adapter_key": "bitrix24.mock",
    "operation": "upsert_lead_follow_up",
    "status": "queued"
  }
}
```

## Business Scenario

A sales manager finishes a call. The transcript arrives from telephony or n8n.
The backend searches the playbook, extracts qualification signals, identifies
objections, drafts a follow-up, and creates an approval item. Only after a human
reviewer approves the item does the backend queue the CRM handoff.

That maps directly to real AI automation work:

- call analysis;
- RAG-backed generation;
- lead scoring;
- Telegram-style approval;
- Bitrix/CRM integration;
- audit-friendly state transitions;
- repeatable local verification.

## Extension Points

- Replace `bitrix24.mock` with a real Bitrix24 REST adapter.
- Add Telegram Bot API buttons for approve/reject/edit.
- Replace deterministic local embeddings with OpenAI or another embedding API.
- Add Deepgram/Whisper before the transcript webhook.
- Add metrics for approval outcomes and failed integration events.
