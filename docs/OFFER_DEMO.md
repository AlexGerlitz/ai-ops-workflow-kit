# Offer Demo

This is the fast reviewer path for the project.

The demo proves an end-to-end AI workflow automation scenario:

1. ingest a sales playbook into the RAG store;
2. query the knowledge base with source context;
3. accept a call transcript through the n8n-facing webhook;
4. score the lead and build a structured call analysis;
5. create a human approval item for the follow-up draft;
6. build a dry-run Telegram approval payload;
7. approve the item;
8. queue a mock Bitrix24 CRM handoff event;
9. build a dry-run Bitrix24 dispatch payload with outbox event state.

The point is not to show a prompt wrapper. The point is to show the production
boundary: n8n routes events, while the backend owns retrieval, scoring, state,
approval transitions, and integration contracts.

## One-Command Local Run

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_offer_demo.py
```

The script uses in-memory storage so a reviewer can run it without Docker or API keys.
Docker/PostgreSQL mode is still available through `docker compose up --build`.

The same workflow is available through the browser demo:

```text
http://127.0.0.1:8080/
```

The deployed browser demo is available at:

```text
https://saleops.duckdns.org/
```

The full public gate also runs tests and validates the demo output:

```bash
bash scripts/verify_public.sh
```

The live deployment smoke validates the public route and HTTPS callback base URL:

```bash
bash scripts/smoke_live_demo.sh
```

## Expected Shape

The output contains these sections:

| Section | What it proves |
| --- | --- |
| `runtime` | API booted and reported the active storage mode. |
| `integrations` | Telegram and Bitrix24 adapter readiness and public callback base URL. |
| `ingestion` | Sales playbook was chunked and stored. |
| `rag_context_sources` | Retrieval returned explicit source context. |
| `call_analysis` | Transcript was scored and converted into structured business action. |
| `approval` | Human-in-the-loop state transition happened before CRM handoff. |
| `telegram_approval` | Telegram approval payload and approve/reject callback contract were built in dry-run mode. |
| `crm_handoff` | A mock Bitrix24 adapter event was queued after approval, with attempt count and last error state. |
| `bitrix24_dispatch` | Bitrix24 dispatch payload was built in dry-run mode for the queued event and reports event state. |

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
  "telegram_approval": {
    "adapter_key": "telegram.approval",
    "status": "dry_run"
  },
  "crm_handoff": {
    "adapter_key": "bitrix24.mock",
    "operation": "upsert_lead_follow_up",
    "status": "queued",
    "attempt_count": 0
  },
  "bitrix24_dispatch": {
    "adapter_key": "bitrix24",
    "status": "dry_run",
    "event_status": "queued",
    "attempt_count": 0,
    "method": "crm.lead.update"
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
- retry/dead-letter integration state;
- dry-run integration contracts before credentials are connected;
- browser-visible control tower for a one-click review path;
- audit-friendly state transitions;
- repeatable local verification.

## Extension Points

- Disable dry-run after adding Telegram Bot API and Bitrix24 webhook credentials.
- Replace deterministic local embeddings with OpenAI or another embedding API.
- Add Deepgram/Whisper before the transcript webhook.
- Add a scheduler or worker loop to drain queued integration events automatically.
